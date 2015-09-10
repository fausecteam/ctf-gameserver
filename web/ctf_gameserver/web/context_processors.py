from django.conf import settings


def competition_name(request):    # pylint: disable=unused-argument
    """
    Context processor that adds the CTF's title to the context.
    """

    return {'COMPETITION_NAME': settings.COMPETITION_NAME}
