from django.http import JsonResponse
from django.shortcuts import render

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
