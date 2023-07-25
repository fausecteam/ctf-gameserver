from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from ctf_gameserver.web.registration.models import Team
from .models import VPNStatusCheck


@login_required
def status_history(request):

    if request.user.is_staff:
        allow_team_selection = True

        net_number_param = request.GET.get('net-number')
        if net_number_param is None:
            return render(request, 'status_history.html', {
                'allow_team_selection': allow_team_selection,
                'net_number': None,
                'server_timezone': settings.TIME_ZONE,
                'check_results': None
            })
        try:
            net_number = int(net_number_param)
        except ValueError as e:
            # Cannot return status code 400 in the same easy way ¯\_(ツ)_/¯
            raise Http404('Invalid net number') from e

        team = get_object_or_404(Team, net_number=net_number)
    else:
        allow_team_selection = False

        try:
            team = request.user.team
        except Team.DoesNotExist as e:
            raise Http404('User has no team') from e

    check_results = VPNStatusCheck.objects.filter(team=team).order_by('-timestamp')[:60].values()
    for result in check_results:
        if result['wireguard_handshake_time'] is None:
            result['wireguard_ok'] = False
        else:
            age = result['timestamp'] - result['wireguard_handshake_time']
            result['wireguard_ok'] = age < timedelta(minutes=5)

    return render(request, 'status_history.html', {
        'allow_team_selection': allow_team_selection,
        'net_number': team.net_number,
        'server_timezone': settings.TIME_ZONE,
        'check_results': check_results
    })
