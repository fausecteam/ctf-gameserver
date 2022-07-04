import datetime

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

import ctf_gameserver.web.registration.models as registration_models

from ctf_gameserver.web.scoring.views import _get_status_descriptions
from ctf_gameserver.web.scoring.decorators import registration_closed_required, services_public_required
from ctf_gameserver.web.scoring import models as scoring_models
from ctf_gameserver.web.scoring import calculations as scoring_calculations

from . import calculations

# old scoreboard currently uses [] so database defined order
SCOREBOARD_SERVICE_ORDER = ['name']

# data per tick does not change so can use longer caching
@cache_page(90)
@services_public_required('json')
def round_json(_, tick=-1):
    tick = int(tick)

    scoreboard_tick = calculations.get_scoreboard_tick()

    if tick > scoreboard_tick or tick < -1:
        raise PermissionDenied()

    scores, attackers_victims = calculations.scores(tick)
    statuses = scoring_calculations.team_statuses(tick - 3, tick, only_team_fields=['user_id'])
    # convert team-keys to team_id-keys
    statuses = {team.user_id: v for team, v in statuses.items()}

    services = scoring_models.Service.objects.order_by(*SCOREBOARD_SERVICE_ORDER).only('name').all()
    service_ids = []
    services_json = []
    for service in services:
        service_ids.append(service.id)
        services_json.append({
            "name": service.name,
            "first_blood": [], # this is an array for multiple flag stores
            "attackers": attackers_victims[service.id]["attackers"],
            "victims": attackers_victims[service.id]["victims"],
        })

    firstbloods = calculations.get_firstbloods(scoreboard_tick)
    for firstblood in firstbloods:
        if firstblood.tick <= tick:
            service_idx = service_ids.index(firstblood.service_id)
            services_json[service_idx]["first_blood"] = [firstblood.team_id]

    response = {
        'tick': tick,
        'scoreboard': [],
        'status-descriptions': _get_status_descriptions(),
        'services': services_json
    }

    for rank, (team_id, points) in enumerate(scores.items(), start=1):
        team_entry = {
            'rank': rank,
            'team_id': team_id,
            'services': [],
            'points':  points['total']['total_score'],
            'o':  points['total']['offense_score'],
            'do': points['total']['offense_delta'],
            'd':  points['total']['defense_score'],
            'dd': points['total']['defense_delta'],
            's':  points['total']['sla_score'],
            'ds': points['total']['sla_delta'],
        }

        for service in services:
            service_statuses = []
            for status_tick in range(tick - 3, tick + 1):
                try:
                    service_statuses.insert(0, statuses[team_id][status_tick][service.id])
                except KeyError:
                    service_statuses.insert(0, -1)

            service_points = points['services'][service.id]
            team_entry['services'].append({
                'c': service_statuses[0],
                'dc': service_statuses[1:4],
                'o':  service_points['offense_score'],
                'do': service_points['offense_delta'],
                'd':  service_points['defense_score'],
                'dd': service_points['defense_delta'],
                's':  service_points['sla_score'],
                'ds': service_points['sla_delta'],
                'cap': service_points['flags_captured'],
                'dcap': service_points['flags_captured_delta'],
                'st': service_points['flags_lost'],
                'dst': service_points['flags_lost_delta'],
            })

        response['scoreboard'].append(team_entry)

    return JsonResponse(response)

# Short cache timeout only, because there is already caching going on in calculations
@cache_page(5)
@services_public_required('json')
def per_team_json(_, team=-1):
    team = int(team)

    # get service ids in scoreboard order
    service_ids = list(scoring_models.Service.objects \
                       .order_by(*SCOREBOARD_SERVICE_ORDER) \
                       .values_list('id', flat=True))

    team_scores = calculations.per_team_scores(team, service_ids)

    response = {
        'points': team_scores
    }

    return JsonResponse(response)

# every scoreboard UI will query this every 2-10 sec so better cache this
# but don't cache it too long to avoid long wait times after tick increment
# it's not expensive anyway (two single row queries)
@cache_page(2)
@registration_closed_required
def current_json(_):
    game_control = scoring_models.GameControl.get_instance()
    current_tick = game_control.current_tick

    scoreboard_tick = calculations.get_scoreboard_tick()

    next_tick_start_offset = (current_tick + 1) * game_control.tick_duration
    current_tick_until = game_control.start + datetime.timedelta(seconds=next_tick_start_offset)
    unix_epoch = datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)
    current_tick_until_unix = (current_tick_until-unix_epoch).total_seconds()

    state = int(not game_control.competition_started() or game_control.competition_over())

    result = {
        "state": state,
        "current_tick": current_tick,
        "current_tick_until": current_tick_until_unix,
        "scoreboard_tick": scoreboard_tick
    }
    return JsonResponse(result, json_dumps_params={'indent': 2})

@cache_page(60)
# This is essentially just a registered teams list so could be made public even earlier
@registration_closed_required
def teams_json(_):

    teams = registration_models.Team.active_not_nop_objects \
      .select_related('user') \
      .only('user__username', 'affiliation', 'country', 'image') \
      .order_by('user_id') \
      .all()

    result = {}
    for team in teams:
        team_json = {
            "name": team.user.username,
            "aff": team.affiliation,
            "country": team.country,
            "logo": None if not team.image else team.image.get_thumbnail_url()
        }
        result[team.user_id] = team_json

    return JsonResponse(result, json_dumps_params={'indent': 2})
