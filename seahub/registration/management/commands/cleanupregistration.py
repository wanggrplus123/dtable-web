"""
A management command which deletes expired accounts (e.g.,
accounts which signed up but never activated) from the database.

Calls ``RegistrationProfile.objects.delete_expired_users()``, which
contains the actual logic for determining which accounts are deleted.

"""
from django.core.management.base import BaseCommand

from seahub.registration.models import RegistrationProfile


class Command(BaseCommand):
    help = "Delete expired user registrations from the database"

    def handle_noargs(self, **options):
        RegistrationProfile.objects.delete_expired_users()
