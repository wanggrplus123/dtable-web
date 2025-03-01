# Copyright (c) 2012-2016 Seafile Ltd.
import logging

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.utils.crypto import get_random_string
from seaserv import ccnet_api, seafile_api, ccnet_threaded_rpc

from seahub.constants import ORG_DEFAULT
from seahub.utils.file_size import get_file_size_unit
from seahub.utils.timeutils import timestamp_to_isoformat_timestr
from seahub.utils import is_valid_email
from seahub.base.accounts import User
from seahub.base.templatetags.seahub_tags import email2nickname, \
        email2contact_email
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.throttling import UserRateThrottle
from seahub.api2.utils import api_error
from seahub.api2.permissions import IsProVersion
from seahub.role_permissions.utils import get_available_roles
from seahub.dtable.models import Workspaces
from seahub.profile.models import Profile

try:
    from seahub.settings import ORG_MEMBER_QUOTA_ENABLED
except ImportError:
    ORG_MEMBER_QUOTA_ENABLED= False

if ORG_MEMBER_QUOTA_ENABLED:
    from seahub.organizations.models import OrgMemberQuota

try:
    from seahub.settings import CLOUD_MODE
except ImportError:
    CLOUD_MODE = False

try:
    from seahub.settings import MULTI_TENANCY
    from seahub.organizations.models import OrgSettings
except ImportError:
    MULTI_TENANCY = False

logger = logging.getLogger(__name__)

def get_org_info(org):
    org_id = org.org_id

    org_info = {}
    org_info['org_id'] = org_id
    org_info['org_name'] = org.org_name
    org_info['ctime'] = timestamp_to_isoformat_timestr(org.ctime)
    org_info['org_url_prefix'] = org.url_prefix
    org_info['role'] = OrgSettings.objects.get_role_by_org(org)

    creator = org.creator
    org_info['creator_email'] = creator
    org_info['creator_name'] = email2nickname(creator)
    org_info['creator_contact_email'] = email2contact_email(creator)

    org_info['quota'] = seafile_api.get_org_quota(org_id)
    org_info['storage_usage'] = Workspaces.objects.get_org_total_storage(org_id)

    if ORG_MEMBER_QUOTA_ENABLED:
        org_info['max_user_number'] = OrgMemberQuota.objects.get_quota(org_id)

    return org_info


def get_org_detailed_info(org):
    org_id = org.org_id
    org_info = get_org_info(org)

    # users
    users = ccnet_api.get_org_emailusers(org.url_prefix, -1, -1)
    org_info['users_count'] = len(users)

    # groups
    groups = ccnet_api.get_org_groups(org_id, -1, -1)
    org_info['groups_count'] = len(groups)

    return org_info


def gen_org_url_prefix(max_trial=None, length=20):
    """Generate organization url prefix automatically.
    If ``max_trial`` is large than 0, then re-try that times if failed.
    Arguments:
    - `max_trial`:
    Returns:
        Url prefix if succed, otherwise, ``None``.
    """
    def _gen_prefix():
        url_prefix = 'org_' + get_random_string(
            length, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789')
        if ccnet_api.get_org_by_url_prefix(url_prefix) is not None:
            logger.error("org url prefix, %s is duplicated" % url_prefix)
            return None
        else:
            return url_prefix

    try:
        max_trial = int(max_trial)
    except (TypeError, ValueError):
        max_trial = 0

    while max_trial >= 0:
        ret = _gen_prefix()
        if ret is not None:
            return ret
        else:
            max_trial -= 1

    logger.error("Failed to generate org url prefix, retry: %d" % max_trial)
    return None


class AdminOrganizations(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAdminUser, IsProVersion)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """ Get all organizations

        Permission checking:
        1. only admin can perform this action.
        """

        if not (CLOUD_MODE and MULTI_TENANCY):
            error_msg = 'Feature is not enabled.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            orgs = ccnet_api.get_all_orgs(-1, -1)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        result = []
        for org in orgs:
            org_info = get_org_info(org)
            result.append(org_info)

        return Response({'organizations': result})

    def post(self, request):
        """ Create an organization

        Permission checking:
        1. only admin can perform this action.
        """
        if not (CLOUD_MODE and MULTI_TENANCY):
            error_msg = 'Feature is not enabled.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        org_name = request.data.get('org_name', None)
        if not org_name:
            error_msg = 'org_name invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        admin_email = request.data.get('admin_email', None)
        if not admin_email or not is_valid_email(admin_email):
            error_msg = 'admin_email invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        admin_name = request.data.get('admin_name')

        password = request.data.get('password', None)
        if not password:
            error_msg = 'password invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        url_prefix = gen_org_url_prefix(5, 20)
        if ccnet_api.get_org_by_url_prefix(url_prefix):
            error_msg = 'Failed to create organization, please try again later.'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        try:
            User.objects.get(email=admin_email)
        except User.DoesNotExist:
            pass
        else:
            error_msg = "User %s already exists." % admin_email
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # check profile
        if Profile.objects.filter(contact_email=admin_email).exists():
            error_msg = "User %s already exists." % admin_email
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        try:
            new_user = User.objects.create_user(admin_email, password,
                                                is_staff=False, is_active=True)
        except User.DoesNotExist as e:
            logger.error(e)
            error_msg = 'Failed to add user %s.' % admin_email
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)
        
        # update profile nickname
        if admin_name:
            Profile.objects.add_or_update(new_user.username, nickname=admin_name)

        try:
            org_id = ccnet_api.create_org(org_name, url_prefix, new_user.username)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        org = ccnet_api.get_org_by_id(org_id)
        OrgSettings.objects.add_or_update(org, ORG_DEFAULT)
        try:
            org_info = get_org_info(org)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response(org_info)


class AdminOrganization(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAdminUser, IsProVersion)
    throttle_classes = (UserRateThrottle,)

    def get(self, request, org_id):
        """ Get base info of a organization

        Permission checking:
        1. only admin can perform this action.
        """

        if not (CLOUD_MODE and MULTI_TENANCY):
            error_msg = 'Feature is not enabled.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        org_id = int(org_id)
        if org_id == 0:
            error_msg = 'org_id invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        org = ccnet_api.get_org_by_id(org_id)
        if not org:
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            org_info = get_org_detailed_info(org)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response(org_info)

    def put(self, request, org_id):
        """ Update base info of a organization

        Permission checking:
        1. only admin can perform this action.
        """

        if not (CLOUD_MODE and MULTI_TENANCY):
            error_msg = 'Feature is not enabled.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        org_id = int(org_id)
        if org_id == 0:
            error_msg = 'org_id invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        org = ccnet_api.get_org_by_id(org_id)
        if not org:
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # update org name
        new_name = request.data.get('org_name', None)
        if new_name:
            try:
                ccnet_api.set_org_name(org_id, new_name)
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        # update org max user number
        max_user_number = request.data.get('max_user_number', None)
        if max_user_number and ORG_MEMBER_QUOTA_ENABLED:

            try:
                max_user_number = int(max_user_number)
            except ValueError:
                error_msg = 'max_user_number invalid.'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            if max_user_number <= 0:
                error_msg = 'max_user_number invalid.'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            try:
                OrgMemberQuota.objects.set_quota(org_id, max_user_number)
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        quota_mb = request.data.get('quota', None)
        if quota_mb:

            try:
                quota_mb = int(quota_mb)
            except ValueError:
                error_msg = 'quota invalid.'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            if quota_mb < 0:
                error_msg = 'quota invalid.'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)


            quota = quota_mb * get_file_size_unit('MB')
            try:
                seafile_api.set_org_quota(org_id, quota)
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        role = request.data.get('role', None)
        if role:
            if role not in get_available_roles():
                error_msg = 'Role %s invalid.' % role
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            OrgSettings.objects.add_or_update(org, role)

        org = ccnet_api.get_org_by_id(org_id)
        org_info = get_org_info(org)
        return Response(org_info)

    def delete(self, request, org_id):
        """ Delete an organization

        Permission checking:
        1. only admin can perform this action.
        """

        if not (CLOUD_MODE and MULTI_TENANCY):
            error_msg = 'Feature is not enabled.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        org_id = int(org_id)
        if org_id == 0:
            error_msg = 'org_id invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        org = ccnet_api.get_org_by_id(org_id)
        if not org:
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            # remove org users
            users = ccnet_api.get_org_emailusers(org.url_prefix, -1, -1)
            for u in users:
                ccnet_api.remove_org_user(org_id, u.email)

            # remove org groups
            groups = ccnet_api.get_org_groups(org_id, -1, -1)
            for g in groups:
                ccnet_api.remove_org_group(org_id, g.gid)

            # remove org repos
            seafile_api.remove_org_repo_by_org_id(org_id)

            # remove org workspaces
            Workspaces.objects.filter(org_id=org_id).delete()

            # remove org
            ccnet_api.remove_org(org_id)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response({'success': True})


class AdminSearchOrganization(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAdminUser, IsProVersion)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """ Search organization by name.

        Permission checking:
        1. only admin can perform this action.
        """

        if not MULTI_TENANCY:
            error_msg = 'Feature is not enabled.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        query_str = request.GET.get('query', '').lower().strip()
        if not query_str:
            error_msg = 'query invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        try:
            orgs = ccnet_threaded_rpc.search_orgs(query_str)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        result = []
        for org in orgs:
            org_info = get_org_info(org)
            result.append(org_info)

        return Response({'organization_list': result})

