from django import forms
from django.utils.translation import ugettext_lazy as _

from . import models


class GameControlAdminForm(forms.ModelForm):
    """
    Form for the GameControl object, designed to be used in GameControlAdmin.
    """

    class Meta:
        model = models.GameControl
        fields = '__all__'
        help_texts = {
            'tick_duration': _('Duration of one tick in seconds'),
            'valid_ticks': _('Number of ticks a flag is valid for')
        }
