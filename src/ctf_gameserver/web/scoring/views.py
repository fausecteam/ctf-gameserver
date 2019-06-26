from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render

import ctf_gameserver.web.registration.models as registration_models

from . import models, calculations
from .decorators import competition_started_required


@competition_started_required
def scoreboard(request):

    game_control = models.GameControl.get_instance()

    if game_control.competition_over():
        to_tick = game_control.current_tick
    else:
        to_tick = game_control.current_tick - 1

    scores = calculations.scores()
    statuses = calculations.team_statuses(to_tick, to_tick)

    return render(request, 'scoreboard.html', {
        'scores': scores,
        'services': models.Service.objects.all(),
        'statuses': statuses,
        'tick': to_tick
    })


def scoreboard_json(_):
    """
    View which returns the scoreboard in CTFTime scoreboard feed format,
    see https://ctftime.org/json-scoreboard-feed.
    """

    game_control = models.GameControl.get_instance()

    if not game_control.competition_running() and not game_control.competition_over():
        return JsonResponse({'error': 'Scoreboard is not available yet'}, status=404)

    tasks = ['Offense', 'Defense', 'SLA']
    standings = []
    scores = calculations.scores()

    for rank, (team, points) in enumerate(scores.items(), start=1):
        standings.append({
            'pos': rank,
            'team': team.user.username,
            'score': points['total'],
            'taskStats': {
                'Offense': {'points': points['offense'][1]},
                'Defense': {'points': points['defense'][1]},
                'SLA': {'points': points['sla'][1]}
            }
        })

    return JsonResponse({'tasks': tasks, 'standings': standings})


@competition_started_required
def service_status(request):

    game_control = models.GameControl.get_instance()
    to_tick = game_control.current_tick
    from_tick = to_tick - 4

    if from_tick < 0:
        from_tick = 0

    statuses = calculations.team_statuses(from_tick, to_tick)

    return render(request, 'service_status.html', {
        'statuses': statuses,
        'ticks': range(from_tick, to_tick+1),
        'services': models.Service.objects.all().order_by('name')
    })


@staff_member_required
def service_history(request):

    game_control = models.GameControl.get_instance()
    max_tick = game_control.current_tick
    min_tick = max_tick - 30

    if min_tick < 0:
        min_tick = 0

    return render(request, 'service_history.html', {
        'services': models.Service.objects.all().order_by('name'),
        'initial_min_tick': min_tick,
        'initial_max_tick': max_tick
    })


@staff_member_required
def service_history_json(request):
    """
    View which returns the check results for a specific service for all teams in JSON format, as required
    by the JavaScript code in service_history().
    """

    service_slug = request.GET.get('service')
    if service_slug is None:
        return JsonResponse({'error': 'Service must be specified'}, status=400)

    try:
        service = models.Service.objects.get(slug=service_slug)
    except models.Service.DoesNotExist:
        return JsonResponse({'error': 'Unknown service'}, status=404)

    max_tick = models.GameControl.get_instance().current_tick
    try:
        from_tick = int(request.GET.get('from-tick', 0))
        to_tick = int(request.GET.get('to-tick', max_tick+1))
    except ValueError:
        return JsonResponse({'error': 'Ticks must be integers'})

    status_checks = models.StatusCheck.objects.filter(service=service) \
                                              .filter(tick__gte=from_tick, tick__lt=to_tick) \
                                              .select_related('team') \
                                              .only('tick', 'status', 'team__user__id') \
                                              .order_by('team__user__id', 'tick')

    teams = registration_models.Team.active_objects.select_related('user').only('user__username').in_bulk()
    max_team_id = registration_models.Team.active_objects.aggregate(Max('user__id'))['user__id__max']

    result = []
    current_team = {'id': 0}
    current_tick = from_tick

    def append_result(next_team_id):
        nonlocal current_team, current_tick

        # Fill up completely missing teams (i.e. they don't have any status checks in the selected ticks)
        fillup_team_id = current_team['id'] + 1
        while fillup_team_id < next_team_id:
            try:
                result.append({'id': fillup_team_id, 'name': teams[fillup_team_id].user.username,
                               'checks': [-1]*(to_tick-from_tick)})
            except KeyError:
                # No team with this ID
                pass
            fillup_team_id += 1

        # First call of `append_result()` (before any checks have been processed) has no data to add
        if current_team['id'] != 0:
            # Fill up missing ticks at the end
            while current_tick < to_tick:
                current_team['checks'].append(-1)
                current_tick += 1
            result.append(current_team)

    for check in status_checks:
        # Status checks are ordered by team ID, finalize result for a team when it changes
        if current_team['id'] != check.team.user.id:
            append_result(check.team.user.id)
            # TODO: status check for inactive teams causes this key error
            # (active_objects returns only active objects)
            try:
                team_name = teams[check.team.user.id].user.username
            except KeyError:
                team_name = '<unknown>'
            current_team = {'id': check.team.user.id, 'name': team_name,
                            'checks': []}
            current_tick = from_tick

        # Fill up missing ticks
        while current_tick < check.tick:
            current_team['checks'].append(-1)
            current_tick += 1

        current_team['checks'].append(check.status)
        current_tick = check.tick + 1

    # Add result from last iteration
    append_result(max_team_id+1)

    status_descriptions = {num: desc for desc, num in models.StatusCheck.STATUSES.items()}
    status_descriptions[-1] = 'not checked'

    response = {
        'teams': result,
        'min-tick': from_tick,
        'max-tick': to_tick-1,
        'service-name': service.name,
        'service-slug': service.slug,
        'status-descriptions': status_descriptions
    }
    if hasattr(settings, 'GRAYLOG_SEARCH_URL'):
        response['graylog-search-url'] = settings.GRAYLOG_SEARCH_URL

    return JsonResponse(response)
