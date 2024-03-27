from collections import defaultdict, OrderedDict

from django.core.cache import cache

from ctf_gameserver.web.registration.models import Team
from . import models


STATUS_PRIORITY = [
    0,  # up
    4,  # recovering
    3,  # flag not found
    2,  # faulty
    1,  # down
    -1, # not checked
]

STATUS_PRIORITY_DICT = {n:i for i,n in enumerate(STATUS_PRIORITY)}


def scores(select_related_fields=None, only_fields=None):
    """
    Returns the scores as currently stored in the database as an OrderedDict in this format:

        {team: {
            'offense': [{service: offense_points}, total_offense_points],
            'defense': [{service: defense_points}, total_defense_points],
            'sla': [{service: sla_points}, total_sla_points],
            'total': total_points
        }}

    The result is sorted by the total points.
    "select_related_fields" and "only_fields" can provide lists of fields for database query optimization
    using Django's select_related() resp. only().
    """

    if select_related_fields is None:
        select_related_fields = []
    select_related_fields = list(set(select_related_fields + ['service_group', 'team']))
    if only_fields is None:
        only_fields = []
    only_fields = list(set(only_fields +
                           ['attack', 'defense', 'sla', 'total', 'service_group__id', 'team__user__id']))

    # No good way to invalidate the cache, so use a generic key with a short timeout
    cache_key = 'scores'
    cached_scores = cache.get(cache_key)

    if cached_scores is not None:
        return cached_scores

    team_scores = defaultdict(lambda: {'offense': [{}, 0], 'defense': [{}, 0], 'sla': [{}, 0], 'total': 0})

    for score in models.ScoreBoard.objects.select_related(*select_related_fields).only(*only_fields).all():
        team_scores[score.team]['offense'][0][score.service_group] = score.attack
        team_scores[score.team]['offense'][1] += score.attack
        team_scores[score.team]['defense'][0][score.service_group] = score.defense
        team_scores[score.team]['defense'][1] += score.defense
        team_scores[score.team]['sla'][0][score.service_group] = score.sla
        team_scores[score.team]['sla'][1] += score.sla
        team_scores[score.team]['total'] += score.total

    sorted_team_scores = OrderedDict(sorted(team_scores.items(), key=lambda s: s[1]['total'], reverse=True))
    cache.set(cache_key, sorted_team_scores, 10)

    return sorted_team_scores


def team_statuses(from_tick, to_tick, select_related_team_fields=None, only_team_fields=None):
    """
    Returns the statuses of all teams and all services in the specified range of ticks. The result is an
    OrderedDict sorted by the teams' names in this format:

        {'team': {
            'tick': {
                'service': status
            }
        }}

    If a check did not happen ("Not checked"), no status will be contained in the result.
    The "select_related_team_fields" and "only_team_fields" parameters can provide lists of fields for
    database query optimization using Django's select_related() resp. only() for queries on the "Team" model.
    """

    cache_key = 'team-statuses_{:d}-{:d}'.format(from_tick, to_tick)
    cached_statuses = cache.get(cache_key)

    if cached_statuses is not None:
        return cached_statuses

    statuses = OrderedDict()
    teams = {}

    team_qset = Team.active_objects
    if select_related_team_fields is not None:
        team_qset = team_qset.select_related(*select_related_team_fields)
    if only_team_fields is not None:
        team_qset = team_qset.only(*only_team_fields)

    for team in team_qset.order_by('user__username').all():
        statuses[team] = defaultdict(lambda: {})
        teams[team.pk] = team
        for tick in range(from_tick, to_tick+1):
            statuses[team][tick] = defaultdict(lambda: {})

    service_to_group = {}
    services_by_group = {}

    for service in models.Service.objects.all():
        service_to_group[service.id] = service.service_group.id
        if service.service_group.id in services_by_group:
            services_by_group[service.service_group.id].append(service.id)
        else:
            services_by_group[service.service_group.id] = [service.id]

    status_checks = models.StatusCheck.objects.filter(tick__gte=from_tick, tick__lte=to_tick)
    for check in status_checks:
        statuses[teams[check.team_id]][check.tick][service_to_group[check.service_id]][check.service_id] = (check.status, check.message)

    for team in statuses.values():
        for team_tick in team.values():
             for group, services in services_by_group.items():
                joint_status = 0
                for service in services:
                    if service not in team_tick[group]:
                        team_tick[group][service] = (-1, '')
                    status, _ = team_tick[group][service]
                    if STATUS_PRIORITY_DICT[status] > STATUS_PRIORITY_DICT[joint_status]:
                        joint_status = status
                team_tick[group][-1] = joint_status

    # Convert defaultdicts to dicts because serialization in `cache.set()` can't handle them otherwise
    for key, val in statuses.items():
        for key2, val2 in val.items():
            statuses[key][key2] = dict(val2)
        statuses[key] = dict(val)
    cache.set(cache_key, statuses, 10)

    return statuses
