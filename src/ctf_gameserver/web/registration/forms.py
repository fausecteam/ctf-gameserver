from django import forms
from django.core.mail import send_mail
from django.template import loader
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site

import ctf_gameserver.web.scoring.models as scoring_models

from .models import Team
from .fields import ClearableThumbnailImageInput
from .util import email_token_generator, get_country_names

FIVE_MB = 5 * 1024**2


class UserForm(forms.ModelForm):
    """
    The portion of the registration form which ends up in the 'User' model. Designed to be used in
    conjunction with TeamForm.
    As specifc fields are directly referred to, there's no advantage in using `get_user_model()`: This won't
    work with user models other than django.contrib.auth.models.User out-of-the-box.
    """

    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {
            'username': _('Name'),
            'email': _('Formal email')
        }
        help_texts = {
            'username': None,
            'email': _('Your authorative contact address. It will be used for sensitive requests, such as '
                       'password resets or prize pay-outs.')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make 'Formal email' field required, despite not being required in the User model
        self.fields['email'].required = True

        if not self.instance.pk:
            # Creating a new user
            self.fields['password'] = forms.CharField(widget=forms.PasswordInput, required=True)
            self.fields['password_repetition'] = forms.CharField(widget=forms.PasswordInput, required=True)
        else:
            # Editing an existing user
            self.fields['username'].widget.attrs['readonly'] = True

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

        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])

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
        competition_name = scoring_models.GameControl.get_instance().competition_name

        context = {
            'competition_name': competition_name,
            'protocol': 'https' if request.is_secure() else 'http',
            'domain': get_current_site(request),
            'user': self.instance.pk,
            'token': email_token_generator.make_token(self.instance)
        }
        message = loader.render_to_string('confirmation_mail.txt', context)

        send_mail(competition_name+' email confirmation', message, settings.DEFAULT_FROM_EMAIL,
                  [self.instance.email])


class TeamForm(forms.ModelForm):
    """
    The portion of the registration form which ends up in the 'Team' model. Designed to be used in
    conjunction with UserForm.
    """

    country = forms.ChoiceField(choices=[(name, name) for name in get_country_names()])

    class Meta:
        model = Team
        fields = ['informal_email', 'image', 'affiliation', 'country']
        labels = {
            'informal_email': _('Informal email')
        }
        widgets = {
            'image': ClearableThumbnailImageInput
        }
        help_texts = {
            'informal_email': _("A less authorative contact address, e.g. your team's mailing list (may "
                                "also be identical to the formal email). It will receive all relevant "
                                "information for participants."),
            'affiliation': _("Your university for academic teams, your team's hacker space or similar."),
            'image': _('Your logo or similar.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add 'empty' option to the country choices, see https://stackoverflow.com/a/16279536
        # Editing the existing list in place doesn't work since choices are stored in the widget as well
        self.fields['country'].choices = [('', '----------')] + self.fields['country'].choices

        confirm_text = scoring_models.GameControl.get_instance().registration_confirm_text
        if confirm_text and not self.instance.pk:
            self.fields['confirm_text'] = forms.BooleanField(label=mark_safe(confirm_text), required=True)

    def clean_image(self):
        if self.cleaned_data['image'] and self.cleaned_data['image'].size > FIVE_MB:
            raise forms.ValidationError(_('The file must not be larger than 5 MB!'))

        return self.cleaned_data['image']

    def save(self, user, commit=True):   # pylint: disable=arguments-renamed
        """
        save() variant which takes as an additional parameter the user model to be associated with the team.
        """
        team = super().save(commit=False)
        team.user = user

        if commit:
            team.save()

        return team


class AdminTeamForm(forms.ModelForm):
    """
    Form for Team objects to be used in TeamAdmin.
    """

    class Meta:
        fields = '__all__'
        labels = {
            'nop_team': _('NOP team')
        }
        help_texts = {
            'nop_team': _("NOP teams are meant for demo purposes (to provide a reference image) and don't "
                          "get included in the scoring.")
        }


class DeleteForm(forms.Form):
    """
    Simple form with one password field for confirmation when deleting a Team.
    """

    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, data=None, *args, user=None, **kwargs):    # pylint: disable=keyword-arg-before-vararg
        """
        Custom initializer which takes the user account to be deleted as an additional argument.
        """
        super().__init__(data, *args, **kwargs)

        # Have to set a default value in the method signature because 'data' should always be first
        if user is None:
            raise TypeError("'user' argument must not be None")

        self.user = user

    def clean_password(self):
        """
        Ensures that the entered password is valid for the specified user account.
        """
        if not self.user.check_password(self.cleaned_data['password']):
            raise forms.ValidationError(_('Please enter the correct password!'))

        return self.cleaned_data['password']


class MailTeamsForm(forms.Form):
    """
    Form to control the parameters of the 'mail_teams' view.
    """

    # Use short property names because they will end up in (visible) GET parameters
    addrs = forms.ChoiceField(
        choices = [('formal', 'Formal'), ('informal', 'Informal')],
        label = _('Address type'),
        widget = forms.RadioSelect,
        required = False,
        initial = 'formal',

    )
    batch = forms.IntegerField(
        min_value = 1,
        label = _('Number of recipients per batch'),
        required = False,
        initial = 50,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use default values if parameters are not specified
        # This cannot be done in clean_() methods as the set values wouldn't show up in the rendered form
        # that way
        if 'addrs' not in self.data:
            # Make the QueryDict mutable
            self.data = self.data.copy()
            self.data['addrs'] = self.fields['addrs'].initial
        if 'batch' not in self.data:
            self.data = self.data.copy()
            self.data['batch'] = self.fields['batch'].initial
