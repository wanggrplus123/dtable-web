# Copyright (c) 2012-2016 Seafile Ltd.
from django.conf import settings

RESERVED_SUBDOMAINS = getattr(settings, 'RESERVED_SUBDOMAINS', ('www', 'api'))

ORG_REDIRECT = getattr(settings, 'ORG_REDIRECT', False)

ORG_MEMBER_QUOTA_ENABLED = getattr(settings, 'ORG_MEMBER_QUOTA_ENABLED', False)

ORG_MEMBER_QUOTA_DEFAULT = getattr(settings, 'ORG_MEMBER_QUOTA_DEFAULT', 10)

ORG_AUTO_URL_PREFIX = getattr(settings, 'ORG_AUTO_URL_PREFIX', True)
