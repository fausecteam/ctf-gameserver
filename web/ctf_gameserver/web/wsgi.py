import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ctf_gameserver.web.prod_settings')

# pylint: disable=invalid-name
application = get_wsgi_application()
