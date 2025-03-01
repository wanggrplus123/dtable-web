import json
from mock import patch

from seahub.base.accounts import UserPermissions
from seahub.invitations.models import Invitation
from seahub.test_utils import BaseTestCase
from seahub.api2.permissions import CanInviteGuest
from tests.common.utils import randstring
from seahub.base.accounts import User
from django.core.urlresolvers import reverse


class InvitationsTest(BaseTestCase):
    def setUp(self):
        self.login_as(self.user)
        self.username = self.user.username

        self.i = Invitation.objects.add(inviter=self.username,
                                        accepter='1@1.com')
        self.endpoint = '/api/v2.1/invitations/' + self.i.token + '/'
        assert len(Invitation.objects.all()) == 1

    @patch.object(CanInviteGuest, 'has_permission')
    @patch.object(UserPermissions, 'can_invite_guest')
    def test_can_get_one(self, mock_can_invite_guest, mock_has_permission):

        mock_can_invite_guest.return_val = True
        mock_has_permission.return_val = True

        resp = self.client.get(self.endpoint)
        self.assertEqual(200, resp.status_code)

        json_resp = json.loads(resp.content)
        assert json_resp['inviter'] == self.username
        assert json_resp['accepter'] == '1@1.com'

    @patch.object(CanInviteGuest, 'has_permission')
    @patch.object(UserPermissions, 'can_invite_guest')
    def test_get_invalid(self, mock_can_invite_guest, mock_has_permission):

        mock_can_invite_guest.return_val = True
        mock_has_permission.return_val = True

        self.i.delete()
        assert len(Invitation.objects.all()) == 0

        resp = self.client.get(self.endpoint)
        self.assertEqual(404, resp.status_code)

    @patch.object(CanInviteGuest, 'has_permission')
    @patch.object(UserPermissions, 'can_invite_guest')
    def test_get_permission_denied(self, mock_can_invite_guest, mock_has_permission):

        mock_can_invite_guest.return_val = True
        mock_has_permission.return_val = True

        self.logout()
        self.login_as(self.admin)

        resp = self.client.get(self.endpoint)
        self.assertEqual(403, resp.status_code)
        self.logout()

    @patch.object(CanInviteGuest, 'has_permission')
    @patch.object(UserPermissions, 'can_invite_guest')
    def test_can_delete(self, mock_can_invite_guest, mock_has_permission):

        mock_can_invite_guest.return_val = True
        mock_has_permission.return_val = True

        resp = self.client.delete(self.endpoint)
        self.assertEqual(204, resp.status_code)

        assert len(Invitation.objects.all()) == 0
