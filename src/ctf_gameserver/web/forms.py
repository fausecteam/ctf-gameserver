from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm

from .scoring.models import GameControl


class TeamAuthenticationForm(AuthenticationForm):
    """
    Custom variant of the login form that replaces "Username" with "Team name".
    """

    username = forms.CharField(max_length=254, label=_('Team name'))


class FormalPasswordResetForm(PasswordResetForm):
    """
    Custom variant of the password reset form that replaces "Email" with "Formal email", adds a help text
    and adds the CTF's title to the email rendering context.
    """

    email = forms.EmailField(max_length=254, label=_('Formal email'), help_text='The address you stated '
                             'as authorative for sensitive requests.')

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email,
                  html_email_template_name=None):
        context['competition_name'] = GameControl.get_instance().competition_name

        return super().send_mail(subject_template_name, email_template_name, context, from_email, to_email,
                                 html_email_template_name)
