"""
Django and project specific settings for usage during development.
Everything should be ready-to-go for a common development environment, but you may of course tweak some
options.
"""

# pylint: disable=wildcard-import, unused-wildcard-import
from .base_settings import *


COMPETITION_NAME = 'Development CTF'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'dev-db.sqlite3'),
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'ctf-gameserver.web@localhost'

MEDIA_ROOT = os.path.join(BASE_DIR, 'uploads')

SECRET_KEY = 'OnlySuitableForDevelopment'

TIME_ZONE = 'UTC'
FIRST_DAY_OF_WEEK = 1


DEBUG = True
INTERNAL_IPS = ('127.0.0.1')
