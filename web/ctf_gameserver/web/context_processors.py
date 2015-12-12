from django.conf import settings

from .scoring import models as scoring_models
from .flatpages import models as flatpages_models


# pylint: disable=unused-argument
def competition_name(request):
    """
    Context processor that adds the CTF's title to the context.
    """

    return {'COMPETITION_NAME': settings.COMPETITION_NAME}


def competition_status(request):
    """
    Context processor which adds information about the competition's status (whether it is running or over
    and whether registration is open) to the context.
    """

    game_control = scoring_models.GameControl.objects.get()

    return {
        'competition_running': game_control.competition_running(),
        'competition_over': game_control.competition_over(),
        'registration_open': game_control.registration_open
    }


def flatpage_nav(request):
    """
    Context processor which adds data required for the main navigation of flatpages to the context.
    """

    categories = flatpages_models.Category.objects.all()
    pages = flatpages_models.Flatpage.objects_without_category.all()

    return {'all_categories': categories, 'pages_without_category': pages, 'HOME_URL': settings.HOME_URL}
