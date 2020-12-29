from django.conf import settings

from .scoring import models as scoring_models
from .flatpages import models as flatpages_models


def game_control(_):
    """
    Context processor which adds information from the Game Control table to the context.
    """

    control_instance = scoring_models.GameControl.get_instance()

    return {
        'competition_name': control_instance.competition_name,
        'registration_open': control_instance.registration_open,
        'services_public': control_instance.are_services_public()
    }


def flatpage_nav(_):
    """
    Context processor which adds data required for the main navigation of flatpages to the context.
    """

    categories = flatpages_models.Category.objects.all()
    pages = flatpages_models.Flatpage.objects_without_category.all()

    return {'all_categories': categories, 'pages_without_category': pages, 'HOME_URL': settings.HOME_URL}
