import logging
from pathlib import Path
import random

from django.db import transaction, IntegrityError
from django.http import FileResponse, Http404
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from ctf_gameserver.web.scoring.decorators import before_competition_required, registration_open_required
import ctf_gameserver.web.scoring.models as scoring_models
from . import forms
from .models import Team, TeamDownload
from .util import email_token_generator

User = get_user_model()    # pylint: disable=invalid-name


class TeamList(ListView):

    queryset = Team.active_not_nop_objects.select_related('user').order_by('user__username')
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

            messages.success(request,
                             mark_safe(_('Successful registration! A confirmation mail has been sent to '
                                         'your formal email address. <strong>You must click the link inside '
                                         'that email to complete your sign-up, otherwise you will not be '
                                         'able to participate.</strong>')))

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

    game_control = scoring_models.GameControl.get_instance()
    # Theoretically, there can be cases where registration is still open (meaning Teams can be edited) after
    # the competition has begun; this is usually not much of a problem, but deleting a Team in that situation
    # will break scoring
    show_delete_button = not game_control.competition_started()

    return render(request, 'edit_team.html', {
        'team': team,
        'user_form': user_form,
        'team_form': team_form,
        'show_delete_button': show_delete_button,
        'delete_form': None
    })


@login_required
@before_competition_required
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

    if not email_token_generator.check_token(user, token):
        messages.error(request, error_message)
        return render(request, '400.html', status=400)

    if user.is_active:
        # Nothing to do, don't generate net number again!
        return redirect(settings.HOME_URL)

    team = Team.objects.get(user__pk=user_pk)

    game_control = scoring_models.GameControl.get_instance()
    if game_control.min_net_number is None or game_control.max_net_number is None:
        # Assign team IDs as net numbers when no net number range is configured
        possible_net_numbers = set([user_pk])
    else:
        possible_net_numbers = set(range(game_control.min_net_number, game_control.max_net_number + 1))

    while True:
        try:
            # Nested transactions are possible in Django
            with transaction.atomic():
                net_numbers = Team.objects.values_list('net_number', flat=True)
                for number in net_numbers:
                    possible_net_numbers.discard(number)

                try:
                    random_net_number = random.choice(list(possible_net_numbers))    # nosec
                except IndexError:
                    logging.error('Net numbers exhausted, could not confirm team (ID) %d', user_pk)
                    return render(request, '500.html', status=500)

                team.net_number = random_net_number
                team.save()

                break
        except IntegrityError:
            pass

    user.is_active = True
    user.save()
    messages.success(request, _('Email address confirmed. Your registration is now complete.'))

    return redirect(settings.HOME_URL)


@login_required
def list_team_downloads(request):
    """
    Provides an HTML listing of available per-team downloads for the logged-in user.
    """

    try:
        team = request.user.team
    except Team.DoesNotExist as e:
        raise Http404('User has no team') from e

    team_downloads_root = Path(settings.TEAM_DOWNLOADS_ROOT)

    downloads = []
    for download in TeamDownload.objects.order_by('filename'):
        fs_path = team_downloads_root / str(team.net_number) / download.filename
        if fs_path.is_file():
            downloads.append(download)

    return render(request, 'team_downloads.html', {'downloads': downloads})


@login_required
def get_team_download(request, filename):
    """
    Delivers a single per-team download to the logged-in user.
    """

    try:
        team = request.user.team
    except Team.DoesNotExist as e:
        raise Http404('User has no team') from e

    get_object_or_404(TeamDownload, filename=filename)

    team_downloads_root = Path(settings.TEAM_DOWNLOADS_ROOT)
    fs_path = team_downloads_root / str(team.net_number) / filename

    if not fs_path.is_file():
        raise Http404('File not found')

    return FileResponse(fs_path.open('rb'), as_attachment=True)


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
