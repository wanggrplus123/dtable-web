# Copyright (c) 2012-2016 Seafile Ltd.
# encoding: utf-8
import datetime
import logging
import json
import os
import re

from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils import translation
from django.utils.translation import ugettext as _

from seaserv import seafile_api, ccnet_api
from seahub.base.models import CommandsLastCheck
from seahub.dtable.models import DTables
from seahub.notifications.models import UserNotification
from seahub.utils import send_html_email, get_site_scheme_and_netloc
from seahub.avatar.templatetags.avatar_tags import avatar
from seahub.avatar.util import get_default_avatar_url
from seahub.base.templatetags.seahub_tags import email2nickname
from seahub.invitations.models import Invitation
from seahub.profile.models import Profile
from seahub.constants import HASH_URLS
from seahub.utils import get_site_name

# Get an instance of a logger
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send Email notifications to user if he/she has an unread notices every period of seconds .'
    label = "notifications_send_notices"

    def handle(self, *args, **options):
        logger.debug('Start sending user notices...')
        self.do_action()
        logger.debug('Finish sending user notices.\n')

    def get_avatar(self, username, default_size=32):
        img_tag = avatar(username, default_size)
        pattern = r'src="(.*)"'
        repl = r'src="%s\1"' % get_site_scheme_and_netloc()
        return re.sub(pattern, repl, img_tag)

    def get_avatar_src(self, username, default_size=32):
        avatar_img = self.get_avatar(username, default_size)
        m = re.search('<img src="(.*?)".*', avatar_img)
        if m:
            return m.group(1)
        else:
            return ''

    def get_default_avatar(self, default_size=32):
        # user default avatar
        img_tag = """<img src="%s" width="%s" height="%s" class="avatar" alt="" />""" % \
                (get_default_avatar_url(), default_size, default_size)
        pattern = r'src="(.*)"'
        repl = r'src="%s\1"' % get_site_scheme_and_netloc()
        return re.sub(pattern, repl, img_tag)

    def get_default_avatar_src(self, default_size=32):
        avatar_img = self.get_default_avatar(default_size)
        m = re.search('<img src="(.*?)".*', avatar_img)
        if m:
            return m.group(1)
        else:
            return ''

    def format_group_message(self, notice):
        d = notice.group_message_detail_to_dict()
        group_id = d['group_id']
        message = d['message']
        group = ccnet_api.get_group(int(group_id))

        notice.group_url = HASH_URLS['GROUP_DISCUSS'] % {'group_id': group.id}
        notice.notice_from = escape(email2nickname(d['msg_from']))
        notice.group_name = group.group_name
        notice.avatar_src = self.get_avatar_src(d['msg_from'])
        notice.grp_msg = message
        return notice

    def format_repo_share_msg(self, notice):
        d = json.loads(notice.detail)
        repo_id = d['repo_id']
        repo = seafile_api.get_repo(repo_id)
        path = d['path']
        org_id = d.get('org_id', None)
        if path == '/':
            shared_type = 'library'
        else:
            shared_type = 'folder'
            if org_id:
                owner = seafile_api.get_org_repo_owner(repo_id)
                repo = seafile_api.get_org_virtual_repo(
                    org_id, repo_id, path, owner)
            else:
                owner = seafile_api.get_repo_owner(repo_id)
                repo = seafile_api.get_virtual_repo(repo_id, path, owner)

        repo_url = reverse('lib_view', args=[repo_id, repo.name, ''])
        notice.repo_url = repo_url
        notice.notice_from = escape(email2nickname(d['share_from']))
        notice.repo_name = repo.name
        notice.avatar_src = self.get_avatar_src(d['share_from'])
        notice.shared_type = shared_type

        return notice

    def format_repo_share_to_group_msg(self, notice):
        d = json.loads(notice.detail)

        repo_id = d['repo_id']
        repo = seafile_api.get_repo(repo_id)
        group_id = d['group_id']
        group = ccnet_api.get_group(group_id)
        org_id = d.get('org_id', None)

        path = d['path']
        if path == '/':
            shared_type = 'library'
        else:
            shared_type = 'folder'
            if org_id:
                owner = seafile_api.get_org_repo_owner(repo_id)
                repo = seafile_api.get_org_virtual_repo(
                    org_id, repo_id, path, owner)
            else:
                owner = seafile_api.get_repo_owner(repo_id)
                repo = seafile_api.get_virtual_repo(repo_id, path, owner)

        repo_url = reverse('lib_view', args=[repo_id, repo.name, ''])
        notice.repo_url = repo_url
        notice.notice_from = escape(email2nickname(d['share_from']))
        notice.repo_name = repo.name
        notice.avatar_src = self.get_avatar_src(d['share_from'])
        notice.group_url = reverse('group', args=[group.id])
        notice.group_name = group.group_name
        notice.shared_type = shared_type

        return notice

    def format_add_user_to_group(self, notice):
        d = json.loads(notice.detail)
        group_staff = d['group_staff']
        group_id = d['group_id']

        group = ccnet_api.get_group(group_id)
        if not group:
            logger.info('group: %s not found', group_id)
            return None

        notice.notice_from = escape(email2nickname(group_staff))
        notice.avatar_src = self.get_avatar_src(group_staff)
        notice.group_staff_profile_url = reverse('user_profile',
                                                  args=[group_staff])
        notice.group_url = reverse('dtable')
        notice.group_name = group.group_name
        return notice

    def format_guest_invitation_accepted_msg(self, notice):
        d = json.loads(notice.detail)
        inv_id = d['invitation_id']
        try:
            inv = Invitation.objects.get(pk=inv_id)
        except Invitation.DoesNotExist:
            self.delete()
            return None

        notice.inv_accepter = inv.accepter
        notice.inv_url = '#invitations/'
        notice.inv_accept_at = inv.accept_time.strftime("%Y-%m-%d %H:%M:%S")
        return notice

    def format_share_dtable_to_user_msg(self, notice):
        d = json.loads(notice.detail)
        dtable = DTables.objects.filter(id=d['table_id']).first()
        if not dtable:
            return None
        notice.dtable = dtable
        notice.share_user = escape(email2nickname(d.get('share_user')))
        notice.share_user_profile_url = reverse('user_profile', args=[d.get('share_user')])
        notice.dtable_url = reverse('dtable:dtable_file_view', args=[dtable.workspace_id, dtable.name])
        notice.avatar_src = self.get_avatar_src(d.get('share_user'))
        return notice

    def get_user_language(self, username):
        return Profile.objects.get_user_language(username)

    def do_action(self):  # todo: complete send-notices-email code, make it works
        now = datetime.datetime.now()

        try:
            cmd_last_check = CommandsLastCheck.objects.get(command_type=self.label)
            logger.debug('Last check time is %s' % cmd_last_check.last_check)

            unseen_notices = UserNotification.objects.get_all_notifications(
                seen=False, time_since=cmd_last_check.last_check)

            logger.debug('Update last check time to %s' % now)
            cmd_last_check.last_check = now
            cmd_last_check.save()
        except CommandsLastCheck.DoesNotExist:
            logger.debug('No last check time found, get all unread notices.')
            unseen_notices = UserNotification.objects.get_all_notifications(
                seen=False)

            logger.debug('Create new last check time: %s' % now)
            CommandsLastCheck(command_type=self.label, last_check=now).save()

        email_ctx = {}
        for notice in unseen_notices:
            if notice.to_user in email_ctx:
                email_ctx[notice.to_user] += 1
            else:
                email_ctx[notice.to_user] = 1

        for to_user, count in list(email_ctx.items()):
            # save current language
            cur_language = translation.get_language()

            # get and active user language
            user_language = self.get_user_language(to_user)
            translation.activate(user_language)
            logger.debug('Set language code to %s for user: %s' % (user_language, to_user))
            self.stdout.write('[%s] Set language code to %s' % (
                str(datetime.datetime.now()), user_language))

            notices = []
            for notice in unseen_notices:
                if notice.to_user != to_user:
                    continue

                logger.info('Processing unseen notice: [%s]' % (notice))

                if notice.is_add_user_to_group_msg():
                    notice = self.format_add_user_to_group(notice)

                elif notice.is_share_dtable_to_user_msg():
                    notice = self.format_share_dtable_to_user_msg(notice)

                if notice is None:
                    continue

                notices.append(notice)

            if not notices:
                continue

            contact_email = Profile.objects.get_contact_email_by_user(to_user)
            to_user = contact_email  # use contact email if any
            c = {
                'to_user': to_user,
                'notice_count': count,
                'notices': notices,
                }

            try:
                send_html_email(_('New notice on %s') % get_site_name(),
                                'notifications/notice_email.html', c,
                                None, [to_user])

                logger.info('Successfully sent email to %s' % to_user)
                self.stdout.write('[%s] Successfully sent email to %s' % (str(datetime.datetime.now()), to_user))
            except Exception as e:
                logger.error('Failed to send email to %s, error detail: %s' % (to_user, e))
                self.stderr.write('[%s] Failed to send email to %s, error detail: %s' % (str(datetime.datetime.now()), to_user, e))

            # restore current language
            translation.activate(cur_language)
