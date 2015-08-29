"""
Django and project specific settings for usage in production.
Edit this file and adjust the options to your own requirements! You may also set additional options from
https://docs.djangoproject.com/en/1.8/ref/settings/.
"""

# pylint: disable=wildcard-import, unused-wildcard-import
from .base_settings import *


# Set to True if your site is available exclusively through HTTPS and not via plaintext HTTP
HTTPS = False


# Your database settings
# See https://docs.djangoproject.com/en/1.8/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': '',
        'PORT': '',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'CONN_MAX_AGE': 60
    }
}

# Settings for the SMTP server that will be used to send email messages
# See https://docs.djangoproject.com/en/1.8/ref/settings/#email-host and other options
EMAIL_HOST = ''
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
# See https://docs.djangoproject.com/en/1.8/ref/settings/#email-use-tls
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

# Sender address for messages sent by the gameserver
DEFAULT_FROM_EMAIL = ''

# A long, random string, which you are supposed to keep secret
SECRET_KEY = ''

# Insert all hostnames your site is available under
# See https://docs.djangoproject.com/en/1.8/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# The name of the time zone (i.e. something like "Europe/Berlin") in which dates should be displayed
# See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for a list of valid options
TIME_ZONE = ''

# First day of the week: 0 means Sunday, 1 means Monday and so on
FIRST_DAY_OF_WEEK = 1


# You should not have to edit anything below this line

DEBUG = False

if HTTPS:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
