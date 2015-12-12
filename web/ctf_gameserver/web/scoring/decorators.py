from functools import wraps

from django.shortcuts import redirect
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib import messages

from .models import GameControl


def registration_open_required(view):
    """
    View decorator which prohibts access to the decorated view if registration is closed from the GameControl
    object.
    """

    @wraps(view)
    def func(request, *args, **kwargs):
        if not GameControl.objects.get().registration_open:
            messages.error(request, _('Sorry, registration is currently closed.'))
            return redirect(settings.HOME_URL)

        return view(request, *args, **kwargs)

    return func


def competition_started_required(view):
    """
    View decorator which prohibts access to the decorated view if the competition has not yet started (i.e.
    it must be running or over).
    """

    @wraps(view)
    def func(request, *args, **kwargs):
        game_control = GameControl.objects.get()

        if not game_control.competition_running() and not game_control.competition_over():
            messages.error(request, _('Sorry, the scoreboard is not available yet.'))
            return redirect(settings.HOME_URL)

        return view(request, *args, **kwargs)

    return func
