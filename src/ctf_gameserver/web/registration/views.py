from django.db import transaction
from django.views.generic import ListView
from django.shortcuts import render, redirect
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.auth import logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from ctf_gameserver.web.scoring.decorators import registration_open_required
from . import forms
from .models import Team
from .util import email_token_generator

User = get_user_model()    # pylint: disable=invalid-name


class TeamList(ListView):

    queryset = Team.active_not_nop_objects.order_by('user__username')
    context_object_name = 'teams'
    template_name = 'team_list.html'


@registration_open_required
@transaction.atomic
def register(request):

    if request.method == 'POST':
        user_form = forms.UserForm(request.POST, prefix='user')
        team_form = forms.TeamForm(request.POST, request.FILES, prefix='team')

        if user_form.is_valid() and team_form.is_valid():
            user = user_form.save()
            team_form.save(user)
            user_form.send_confirmation_mail(request)

            messages.success(request, _('Successful registration! A confirmation mail has been sent to your '
                                        'formal email address. Please open the link inside that email in '
                                        'order to complete your sign-up.'))

            return redirect(settings.HOME_URL)
    else:
        user_form = forms.UserForm(prefix='user')
        team_form = forms.TeamForm(prefix='team')

    return render(request, 'register.html', {'user_form': user_form, 'team_form': team_form})


@login_required
@registration_open_required
@transaction.atomic
def edit_team(request):

    try:
        team = request.user.team
    except Team.DoesNotExist:
        team = None

    if request.method == 'POST':
        user_form = forms.UserForm(request.POST, prefix='user', instance=request.user)
        team_form = forms.TeamForm(request.POST, request.FILES, prefix='team', instance=team)

        if user_form.is_valid() and team_form.is_valid():
            user = user_form.save()
            team_form.save(user)

            if 'password' in user_form.changed_data:
                # Keep the current session active although all sessions are invalidated on password change
                update_session_auth_hash(request, user)

            if 'email' in user_form.changed_data:
                user_form.send_confirmation_mail(request)
                logout(request)

                messages.warning(request, _('A confirmation mail has been sent to your new formal email '
                                            'address. Please visit the link inside that email. Until then, '
                                            'your team has been deactivated and you have been logged out.'))
                return redirect(settings.HOME_URL)

            # Work around the fact that FileField/ImageField will not automatically update to its new (bound)
            # state
            team_form = forms.TeamForm(prefix='team', instance=team)
    else:
        user_form = forms.UserForm(prefix='user', instance=request.user)
        team_form = forms.TeamForm(prefix='team', instance=team)

    return render(request, 'edit_team.html', {
        'user_form': user_form,
        'team_form': team_form,
        'delete_form': None
    })


@login_required
@registration_open_required
@transaction.atomic
def delete_team(request):
    """
    View for deletion of a User and the associated Team.
    This renders the 'edit_team' template with a modal overlay for deletion. The modal is rendered in static
    HTML instead of showing it dynamically to avoid the need for (custom) JavaScript, especially when
    handling form errors in the modal.
    """

    try:
        team = request.user.team
    except Team.DoesNotExist:
        team = None

    # These forms will only be visible in the background
    user_form = forms.UserForm(prefix='user', instance=request.user)
    team_form = forms.TeamForm(prefix='team', instance=team)

    if request.method == 'POST':
        delete_form = forms.DeleteForm(request.POST, user=request.user, prefix='delete')

        if delete_form.is_valid():
            request.user.delete()
            logout(request)
            messages.success(request, _('Your team has been deleted.'))

            return redirect(settings.HOME_URL)
    else:
        delete_form = forms.DeleteForm(user=request.user, prefix='delete')

    return render(request, 'edit_team.html', {
        'user_form': user_form,
        'team_form': team_form,
        'delete_form': delete_form
    })


@transaction.atomic
def confirm_email(request):

    try:
        user_pk = request.GET['user']
        token = request.GET['token']
    except KeyError:
        messages.error(request, _('Missing parameters, email address could not be confirmed.'))
        return render(request, '400.html', status=400)

    error_message = _('Invalid user or token, email address could not be confirmed.')

    # pylint: disable=protected-access
    try:
        user = User._default_manager.get(pk=user_pk)
    except User.DoesNotExist:
        messages.error(request, error_message)
        return render(request, '400.html', status=400)

    if email_token_generator.check_token(user, token):
        User._default_manager.filter(pk=user_pk).update(is_active=True)
        messages.success(request, _('Email address confirmed. Your registration is now complete.'))
    else:
        messages.error(request, error_message)
        return render(request, '400.html', status=400)

    return redirect(settings.HOME_URL)


@staff_member_required
def mail_teams(request):
    """
    View which allows the generation of 'mailto' links to write emails to the formal or informal addresses of
    all teams.
    Addresses are split into batches because most mail servers limit the number of recipients per single
    message.
    """

    form = forms.MailTeamsForm(request.GET)

    if not form.is_valid():
        return render(request, '400.html', status=400)

    if form.cleaned_data['addrs'] == 'formal':
        addresses = [values['user__email'] for values in
                     Team.active_objects.values('user__email').distinct()]
    else:
        addresses = [values['informal_email'] for values in
                     Team.active_objects.values('informal_email').distinct()]

    batch_size = form.cleaned_data['batch']
    batches = []

    for i in range(0, len(addresses), batch_size):
        # Comma-separated recipients for 'mailto' are against the spec, but should work in practice
        batches.append(','.join(addresses[i:i+batch_size]))

    return render(request, 'mail_teams.html', {'form': form, 'batches': batches})
