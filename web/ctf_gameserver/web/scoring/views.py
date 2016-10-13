from django.shortcuts import render

from . import models, calculations
from .decorators import competition_started_required


@competition_started_required
def scoreboard(request):

    game_control = models.GameControl.objects.get()

    if game_control.competition_over():
        to_tick = game_control.current_tick
    else:
        to_tick = game_control.current_tick - 1

    scores = models.ScoreBoard.objects.all()

    return render(request, 'scoreboard.html', {
        'scores': scores,
        'tick': to_tick
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
