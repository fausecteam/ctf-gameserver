from django.shortcuts import render

from . import models, calculations
from .decorators import competition_started_required


@competition_started_required
def scoreboard(request):

    game_control = models.GameControl.objects.get()

    if game_control.competition_over():
        last_tick = game_control.current_tick
    else:
        last_tick = game_control.current_tick - 1

    services = models.Service.objects.all()
    score = calculations.score(last_tick)
    statuses = calculations.team_statuses(last_tick, last_tick)

    return render(request, 'scoreboard.html', {
        'score': score,
        'services': services,
        'statuses': statuses,
        'tick': last_tick
    })


@competition_started_required
def service_status(request):

    game_control = models.GameControl.objects.get()
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
