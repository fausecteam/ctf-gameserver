from django.conf import settings

from .flatpages import models


# pylint: disable=unused-argument
def competition_name(request):
    """
    Context processor that adds the CTF's title to the context.
    """

    return {'COMPETITION_NAME': settings.COMPETITION_NAME}


def flatpage_nav(request):
    """
    Context processor which adds data required for the main navigation of flatpages to the context.
    """

    categories = models.Category.objects.all()
    pages = models.Flatpage.objects_without_category.all()

    return {'all_categories': categories, 'pages_without_category': pages, 'HOME_URL': settings.HOME_URL}
