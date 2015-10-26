from django import forms
from django.core.mail import send_mail
from django.template import Context, loader
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site

from .models import Team
from .util import email_token_generator


class UserForm(forms.ModelForm):
    """
    The portion of the registration form which ends up in the 'User' model. Designed to be used in
    conjunction with TeamForm.
    As specifc fields are directly referred to, there's no advantage in using `get_user_model()`: This won't
    work with user models other than django.contrib.auth.models.User out-of-the-box.
    """

    password_repetition = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'password', 'password_repetition', 'email']
        labels = {
            'username': _('Name'),
            'email': _('Formal email')
        }
        help_texts = {
            'username': None,
            'email': _('Your authorative contact address. It will be used sensitive requests, such as '
                       'password resets or prize pay-outs.')
        }
        widgets = {
            'password': forms.PasswordInput
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make 'Formal email' field required, despite not being required in the User model
        self.fields['email'].required = True

        if self.instance.pk:
            # Editing an existing user
            self.fields['username'].widget.attrs['readonly'] = True
            self.fields['password'].required = False
            self.fields['password_repetition'].required = False

    def clean_username(self):
        if self.instance.pk:
            # Field is read-only, so discard its user-provided value
            return self.instance.username

        return self.cleaned_data['username']

    def clean_password_repetition(self):
        password = self.cleaned_data.get('password')
        repetition = self.cleaned_data.get('password_repetition')

        if password != repetition:
            raise forms.ValidationError(_("The passwords don't match!"), code='password_mismatch')

        return repetition

    def save(self, commit=True):
        """
        save() variant which hashes the password and sets the user to inactive when the email address has
        been changed. It should stay that way until the address is confirmed.
        """
        user = super().save(commit=False)

        if self.cleaned_data['password']:
            user.set_password(self.cleaned_data['password'])
        else:
            # Provide the correct change status to the view
            try:
                self.changed_data.remove('password')
            except ValueError:
                pass

        if 'email' in self.changed_data:
            user.is_active = False

        if commit:
            user.save()

        return user

    def send_confirmation_mail(self, request):
        """
        Sends an email containing the address confirmation link to the user associated with this form. As it
        requires a User instance, it should only be called after the object has initially been saved.

        Args:
            request: The HttpRequest from which this function is being called
        """
        context = Context({
            'competition_name': settings.COMPETITION_NAME,
            'protocol': 'https' if request.is_secure() else 'http',
            'domain': get_current_site(request),
            'user': self.instance.pk,
            'token': email_token_generator.make_token(self.instance)
        })
        message = loader.render_to_string('confirmation_mail.txt', context)

        send_mail(settings.COMPETITION_NAME+' email confirmation', message, settings.DEFAULT_FROM_EMAIL,
                  [self.instance.email])


class TeamForm(forms.ModelForm):
    """
    The portion of the registration form which ends up in the 'Team' model. Designed to be used in
    conjunction with UserForm.
    """

    class Meta:
        model = Team
        fields = ['informal_email', 'image', 'country']
        labels = {
            'informal_email': _('Informal email')
        }
        help_texts = {
            'informal_email': _("A less authorative contact address, e.g. your team's mailing list. It will "
                                "receive all relevant information for participants."),
            'image': _('Your logo or similar.'),
        }

    def save(self, user, commit=True):   # pylint: disable=arguments-differ
        """
        save() variant which takes as an additional parameter the user model to be associated with the team.
        """
        team = super().save(commit=False)
        team.user = user

        if commit:
            team.save()

        return team
