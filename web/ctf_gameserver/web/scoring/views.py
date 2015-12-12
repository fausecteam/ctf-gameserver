from django.shortcuts import render

from . import models, calculations
from .decorators import competition_started_required


@competition_started_required
def scoreboard(request):

    game_control = models.GameControl.objects.get()

    if game_control.competition_over():
        last_tick = game_control.current_tick
    else:
        # REVISIT when assumptions about tick values are fixed
        last_tick = game_control.current_tick - 1

    services = models.Service.objects.all()
    score = calculations.score(last_tick)
    statuses = calculations.team_statuses(last_tick)

    return render(request, 'scoreboard.html', {
        'score': score,
        'services': services,
        'statuses': statuses,
        'tick': last_tick
    })
