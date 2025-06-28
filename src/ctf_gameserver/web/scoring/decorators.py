from functools import wraps

from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib import messages

from .models import GameControl


def registration_open_required(view):
    """
    View decorator which prohibits access to the decorated view if registration is closed from the
    GameControl object.
    """

    @wraps(view)
    def func(request, *args, **kwargs):
        if not GameControl.get_instance().registration_open:
            messages.error(request, _('Sorry, registration is currently closed.'))
            return redirect(settings.HOME_URL)

        return view(request, *args, **kwargs)

    return func


def registration_closed_required(view):
    """
    View decorator which only allows access to the decorated view if registration is closed from the
    GameControl object.
    Format of the response is currently always JSON.
    """

    @wraps(view)
    def func(request, *args, **kwargs):
        if GameControl.get_instance().registration_open:
            return JsonResponse({'error': 'Not available yet'}, status=404)

        return view(request, *args, **kwargs)

    return func


def before_competition_required(view):
    """
    View decorator which prohibits access to the decorated view if the competition has already begun (i.e.
    running or over).
    """

    @wraps(view)
    def func(request, *args, **kwargs):
        if GameControl.get_instance().competition_started():
            messages.error(request, _('Sorry, that is only possible before the competition.'))
            return redirect(settings.HOME_URL)

        return view(request, *args, **kwargs)

    return func


def services_public_required(resp_format):
    """
    View decorator which prohibits access to the decorated view if information about the services is not
    public yet.

    Args:
        resp_format: Format of the response when the competition has not yet started. Supported options are
                     'html' and 'json'.
    """

    def decorator(view):
        @wraps(view)
        def func(request, *args, **kwargs):
            game_control = GameControl.get_instance()
            if game_control.are_services_public():
                return view(request, *args, **kwargs)

            if resp_format == 'json':
                return JsonResponse({'error': 'Not available yet'}, status=404)
            else:
                messages.error(request, _('Sorry, the page you requested is not available yet.'))
                return redirect(settings.HOME_URL)

        return func

    return decorator
