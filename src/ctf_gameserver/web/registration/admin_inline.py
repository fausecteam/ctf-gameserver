from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Team
from .forms import AdminTeamForm


class InlineTeamAdmin(admin.StackedInline):
    """
    InlineModelAdmin for Team objects. Primarily designed to be used within a UserAdmin.
    """

    model = Team
    form = AdminTeamForm

    # Abuse the plural title as headline, since more than one team will never be edited using this inline
    verbose_name_plural = _('Associated team')
