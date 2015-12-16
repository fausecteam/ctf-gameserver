from django import forms
from django.utils.translation import ugettext_lazy as _

from . import models


class GameControlAdminForm(forms.ModelForm):
    """
    Form for the GameControl object, designed to be used in GameControlAdmin.
    """

    # Ticks longer than 1 hours are possible but don't seem reasonable and would require addtional cleaning
    # logic below
    tick_duration = forms.IntegerField(min_value=1, max_value=3559, help_text=_('Duration of one tick in '
                                       'seconds'))

    class Meta:
        model = models.GameControl
        fields = '__all__'
        help_texts = {
            'valid_ticks': _('Number of ticks a flag is valid for')
        }

    def clean_tick_duration(self):
        tick_duration = self.cleaned_data['tick_duration']

        # The timer of the gameserver's Controller component is configured with conditions for the minute
        # and seconds values
        if (tick_duration < 60 and 60 % tick_duration != 0) or \
           (tick_duration > 60 and tick_duration % 60 != 0):
            raise forms.ValidationError(_('The tick duration has to be a multitude of 60!'))

        return tick_duration
