from mock import patch
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.html import escape

from tests.common.utils import randstring

from tests.common.common import USERNAME

LOGIN_URL = reverse('auth_login')
class LoginTest(TestCase):
    def test_renders_correct_template(self):
        resp = self.client.get(LOGIN_URL)

        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'registration/login.html')

    def test_invalid_password(self):
        # load it once for test cookie
        self.client.get(LOGIN_URL)

        resp = self.client.post(LOGIN_URL, {
            'login': USERNAME,
            'password': 'fakepasswd',
        })
        assert resp.status_code == 200
        assert resp.context['form'].errors['__all__'] == [
            'Please enter a correct email/username and password. Note that both fields are case-sensitive.'
        ]
