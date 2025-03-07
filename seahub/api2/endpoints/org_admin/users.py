# Copyright (c) 2012-2016 Seafile Ltd.
import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from django.utils.translation import ugettext as _

from seaserv import ccnet_api, seafile_api

from seahub.api2.permissions import IsProVersion, IsOrgAdminUser
from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.utils import api_error, to_python_boolean
from seahub.api2.endpoints.utils import is_org_user
from seahub.base.accounts import User
from seahub.base.models import UserLastLogin
from seahub.base.templatetags.seahub_tags import email2nickname, email2contact_email
from seahub.profile.models import Profile
from seahub.settings import SEND_EMAIL_ON_ADDING_SYSTEM_MEMBER
from seahub.utils import is_valid_email, IS_EMAIL_CONFIGURED
from seahub.utils.file_size import get_file_size_unit
from seahub.utils.timeutils import timestamp_to_isoformat_timestr, datetime_to_isoformat_timestr
from seahub.utils.licenseparse import user_number_over_limit
from seahub.views.sysadmin import send_user_add_mail
from seahub.avatar.settings import AVATAR_DEFAULT_SIZE
from seahub.avatar.templatetags.avatar_tags import api_avatar_url

from pysearpc import SearpcError

from seahub.organizations.settings import ORG_MEMBER_QUOTA_ENABLED
from seahub.organizations.views import get_org_user_self_usage, get_org_user_quota, \
    is_org_staff, org_user_exists, unset_org_user, set_org_user, set_org_staff, unset_org_staff


logger = logging.getLogger(__name__)


class OrgAdminUsers(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    throttle_classes = (UserRateThrottle,)
    permission_classes = (IsProVersion, IsOrgAdminUser)

    def get(self, request, org_id):
        """List organization user
        """
        # resource check
        org_id = int(org_id)
        if not ccnet_api.get_org_by_id(org_id):
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        org = request.user.org
        is_staff = request.GET.get('is_staff', None)
        if is_staff:
            try:
                is_staff = to_python_boolean(is_staff)
            except ValueError:
                error_msg = 'is_staff invalid.'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            org_users = ccnet_api.get_org_users_by_url_prefix(org.url_prefix, -1, -1)

            users = []
            if is_staff:
                for user in org_users:
                    if is_org_staff(org.org_id, user.email):
                        users.append(user)
        else:
            # Make sure page request is an int. If not, deliver first page.
            try:
                current_page = int(request.GET.get('page', '1'))
                per_page = int(request.GET.get('per_page', '100'))
            except ValueError:
                current_page = 1
                per_page = 100
            users_plus_one = ccnet_api.get_org_users_by_url_prefix(
                org.url_prefix, per_page * (current_page - 1), per_page + 1)

            if len(users_plus_one) == per_page + 1:
                page_next = True
            else:
                page_next = False

            users = users_plus_one[:per_page]

        last_logins = UserLastLogin.objects.filter(username__in=[x.email for x in users])

        user_list = []
        for user in users:
            user_info = get_user_info(user.email, org_id)

            # populate user last login time
            user_info['last_login'] = None
            for last_login in last_logins:
                if last_login.username == user.email:
                    user_info['last_login'] = datetime_to_isoformat_timestr(last_login.last_login)

            user_info['id'] = user.id
            user_info['is_active'] = user.is_active
            user_info['ctime'] = timestamp_to_isoformat_timestr(user.ctime)

            # these two fields are designed to be compatible with the old API
            user_info['self_usage'] = user_info.get('quota_usage')
            user_info['quota'] = user_info.get('quota_total')

            user_list.append(user_info)

        if is_staff:
            return Response({
                'user_list': user_list
            })
        else:
            return Response({
                'user_list': user_list,
                'per_page': per_page,
                'page': current_page,
                'page_next': page_next
            })


    def post(self, request, org_id):
        """Added an organization user, check member quota before adding.
        """
        # resource check
        org_id = int(org_id)
        if not ccnet_api.get_org_by_id(org_id):
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # check plan
        url_prefix = request.user.org.url_prefix
        org_members = len(ccnet_api.get_org_users_by_url_prefix(url_prefix, -1, -1))

        if ORG_MEMBER_QUOTA_ENABLED:
            from seahub.organizations.models import OrgMemberQuota
            org_members_quota = OrgMemberQuota.objects.get_quota(request.user.org.org_id)
            if org_members_quota is not None and org_members >= org_members_quota:
                err_msg = 'Failed. You can only invite %d members.' % org_members_quota
                return api_error(status.HTTP_403_FORBIDDEN, err_msg)

        if user_number_over_limit():
            return api_error(status.HTTP_403_FORBIDDEN, 'The number of users exceeds the limit')

        email = request.data.get('email', '')
        name = request.data.get('name', '')
        password = request.data.get('password', '')

        if not email or not is_valid_email(email):
            return api_error(status.HTTP_400_BAD_REQUEST, 'Email invalid.')

        if not password:
            return api_error(status.HTTP_400_BAD_REQUEST, 'Password invalid.')

        name = name.strip()
        if not name:
            return api_error(status.HTTP_400_BAD_REQUEST, 'Name invalid.')

        if len(name) > 64:
            error_msg = 'Name is too long (maximum is 64 characters).'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if "/" in name:
            error_msg = "Name should not include '/'."
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        try:
            user = User.objects.get(email=email)
            error_msg = 'User %s already exists.' % email
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        except User.DoesNotExist:
            pass

        try:
            user = User.objects.create_user(email, password, is_staff=False,
                                            is_active=True)
        except User.DoesNotExist as e:
            logger.error(e)
            error_msg = 'Fail to add user %s.' % email
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        if user and name:
            Profile.objects.add_or_update(username=user.username, nickname=name)

        set_org_user(org_id, user.username)

        if IS_EMAIL_CONFIGURED:
            if SEND_EMAIL_ON_ADDING_SYSTEM_MEMBER:
                try:
                    send_user_add_mail(request, email, password)
                except Exception as e:
                    logger.error(str(e))

        user_info = {}
        user_info['id'] = user.id
        user_info['is_active'] = user.is_active
        user_info['ctime'] = timestamp_to_isoformat_timestr(user.ctime)
        user_info['name'] = email2nickname(user.email)
        user_info['email'] = user.email
        user_info['contact_email'] = email2contact_email(user.email)
        user_info['last_login'] = None
        user_info['self_usage'] = 0 # get_org_user_self_usage(org.org_id, user.email)
        try:
            user_info['quota'] = get_org_user_quota(org_id, user.email)
        except SearpcError as e:
            logger.error(e)
            user_info['quota'] = -1

        return Response(user_info)


class OrgAdminUser(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    throttle_classes = (UserRateThrottle,)
    permission_classes = (IsProVersion, IsOrgAdminUser)

    def get(self, request, org_id, email):
        """Get org user info

        """
        # argument check
        avatar_size = request.GET.get('avatar_size', AVATAR_DEFAULT_SIZE)

        # resource check
        org_id = int(org_id)
        if not ccnet_api.get_org_by_id(org_id):
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            err_msg = 'User %s not found.' % email
            return api_error(status.HTTP_404_NOT_FOUND, err_msg)

        # permission check
        if not ccnet_api.org_user_exists(org_id, email):
            err_msg = _('User %s not found in organization.') % email
            return api_error(status.HTTP_404_NOT_FOUND, err_msg)

        # get user info
        user_info = get_user_info(email, org_id)
        avatar_url, is_default, date_uploaded = api_avatar_url(email, avatar_size)
        user_info['avatar_url'] = avatar_url

        return Response(user_info)

    def put(self, request, org_id, email):
        """ update name of an org user.

        Permission checking:
        1. only admin can perform this action.
        """

        # resource check
        org_id = int(org_id)
        if not ccnet_api.get_org_by_id(org_id):
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            error_msg = 'User %s not found.' % email
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        if not is_org_user(email, org_id):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        # update user's name
        name = request.data.get("name", None)
        if name is not None:

            name = name.strip()
            if len(name) > 64:
                error_msg = 'Name is too long (maximum is 64 characters).'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            if "/" in name:
                error_msg = "Name should not include '/'."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            try:
                Profile.objects.add_or_update(email, nickname=name)
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        # update user's contact email
        contact_email = request.data.get("contact_email", None)
        if contact_email is not None:

            contact_email = contact_email.strip()
            if contact_email != '' and not is_valid_email(contact_email):
                error_msg = 'contact_email invalid.'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            try:
                Profile.objects.add_or_update(email, contact_email=contact_email)
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        is_staff = request.data.get("is_staff", None)
        if is_staff is not None:
            try:
                is_staff = to_python_boolean(is_staff)
            except ValueError:
                error_msg = 'is_staff invalid.'
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            if is_staff:
                if is_org_staff(org_id, user.username):
                    error_msg = '%s is already organization staff.' % email
                    return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

                set_org_staff(org_id, user.username)

            if not is_staff:
                if not is_org_staff(org_id, user.username):
                    error_msg = '%s is not organization staff.' % email
                    return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

                unset_org_staff(org_id, user.username)

        quota_total_mb = request.data.get("quota_total", None)
        if quota_total_mb:
            try:
                quota_total_mb = int(quota_total_mb)
            except ValueError:
                error_msg = "Must be an integer that is greater than or equal to 0."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            if quota_total_mb < 0:
                error_msg = "Space quota is too low (minimum value is 0)."
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            org_quota = seafile_api.get_org_quota(org_id)
            org_quota_mb = org_quota / get_file_size_unit('MB')

            # -1 means org has unlimited quota
            if org_quota > 0 and quota_total_mb > org_quota_mb:
                error_msg = _(u'Failed to set quota: maximum quota is %d MB' % org_quota_mb)
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

            quota_total = int(quota_total_mb) * get_file_size_unit('MB')
            try:
                seafile_api.set_org_user_quota(org_id, email, quota_total)
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        info = get_user_info(email, org_id)
        info['is_active'] = user.is_active
        info['id'] = user.id
        info['ctime'] = timestamp_to_isoformat_timestr(user.ctime)

        try:
            last_login = UserLastLogin.objects.get(username=user.email)
            info['last_login'] = datetime_to_isoformat_timestr(last_login.last_login)
        except UserLastLogin.DoesNotExist:
            info['last_login'] = None

        # these two fields are designed to be compatible with the old API
        info['self_usage'] = info.get('quota_usage')
        info['quota'] = info.get('quota_total')

        return Response(info)

    def delete(self, request, org_id, email):
        """Remove an organization user
        """
        # resource check
        org_id = int(org_id)
        if not ccnet_api.get_org_by_id(org_id):
            error_msg = 'Organization %s not found.' % org_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            err_msg = 'User %s not found.' % email
            return api_error(status.HTTP_404_NOT_FOUND, err_msg)

        # permission check
        org = request.user.org
        if not org_user_exists(org.org_id, user.username):
            err_msg = 'User %s does not exist in the organization.' % email
            return api_error(status.HTTP_404_NOT_FOUND, err_msg)

        user.delete()
        unset_org_user(org.org_id, user.username)

        return Response({'success': True})


def get_user_info(email, org_id):

    info = {}
    info['email'] = email
    info['name'] = email2nickname(email)
    info['contact_email'] = email2contact_email(email)

    try:
        info['quota_usage'] = get_org_user_self_usage(org_id, email)
        info['quota_total'] = get_org_user_quota(org_id, email)
    except SearpcError as e:
        logger.error(e)
        info['quota_usage'] = -1
        info['quota_total'] = -1

    return info
