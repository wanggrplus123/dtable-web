from mock import patch
from seaserv import ccnet_api

from seahub.test_utils import BaseTestCase
from seahub.api2.serializers import AuthTokenSerializer
from seahub.profile.models import Profile

class AuthTokenSerializerTest(BaseTestCase):
    def setUp(self):
        self.inactive_user = self.create_user('inactive@test.com', is_active=False)
        Profile.objects.add_or_update(self.user.username,
                                      login_id='user_login_id',
                                      contact_email='contact@test.com')

        ccnet_api.set_reference_id(self.user.username, 'another_email@test.com')

    def assertSuccess(self, s):
        assert s.is_valid() is True
        assert s.errors == {}

    def assertFailed(self, s):
        assert s.is_valid() is False
        assert 'Unable to login with provided credentials.' in s.errors['non_field_errors']

    def test_invalid_user(self):
        d = {
            'username': 'test_does_not_exist',
            'password': '123',
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        self.assertFailed(s)

    def test_inactive_user(self):
        d = {
            'username': self.inactive_user.username,
            'password': 'secret',
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        assert s.is_valid() is False
        assert 'User account is disabled.' in s.errors['non_field_errors']

    def test_inactive_user_incorrect_password(self):
        """An invalid login doesn't leak the inactive status of a user."""
        d = {
            'username': self.inactive_user.username,
            'password': 'incorrect'
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        self.assertFailed(s)

    def test_login_failed(self):
        d = {
            'username': self.user.username,
            'password': 'incorrect',
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        self.assertFailed(s)

    def test_login_success(self):
        d = {
            'username': self.user.username,
            'password': self.user_password,
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        self.assertSuccess(s)

    def test_login_id(self):
        d = {
            'username': 'user_login_id',
            'password': self.user_password,
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        self.assertSuccess(s)

    def test_contact_email(self):
        d = {
            'username': 'contact@test.com',
            'password': self.user_password,
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        self.assertSuccess(s)

    def test_primary_id(self):
        d = {
            'username': 'another_email@test.com',
            'password': self.user_password,
        }

        s = AuthTokenSerializer(data=d, context={'request': self.fake_request})
        self.assertSuccess(s)
