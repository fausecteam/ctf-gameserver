from django.conf import settings


# pylint: disable=unused-argument
def competition_name(request):
    """
    Context processor that adds the CTF's title to the context.
    """

    return {'COMPETITION_NAME': settings.COMPETITION_NAME}


def home_url(request):
    """
    Context processor which adds the home page's URL to the context.
    """

    return {'HOME_URL': settings.HOME_URL}
