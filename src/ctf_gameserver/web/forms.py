from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm


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
        context['competition_name'] = settings.COMPETITION_NAME

        return super().send_mail(subject_template_name, email_template_name, context, from_email, to_email,
                                 html_email_template_name)
