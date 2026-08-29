from collections import defaultdict, OrderedDict

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from ctf_gameserver.web.registration.models import Team
from . import models


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
    select_related_fields = list(set(select_related_fields + ['service', 'team']))
    if only_fields is None:
        only_fields = []
    only_fields = list(set(only_fields +
                           ['attack', 'defense', 'sla', 'total', 'service__id', 'team__user__id']))

    # No good way to invalidate the cache, so use a generic key with a short timeout
    cache_key = 'scores'
    cached_scores = cache.get(cache_key)

    if cached_scores is not None:
        return cached_scores

    team_scores = defaultdict(lambda: {'offense': [{}, 0], 'defense': [{}, 0], 'sla': [{}, 0], 'total': 0})

    # Only the aggregate rows (flagstore IS NULL) carry per-service totals; per-store rows are read
    # separately
    for score in models.ScoreBoard.objects.filter(flagstore__isnull=True) \
                                          .select_related(*select_related_fields).only(*only_fields).all():
        team_scores[score.team]['offense'][0][score.service] = score.attack
        team_scores[score.team]['offense'][1] += score.attack
        team_scores[score.team]['defense'][0][score.service] = score.defense
        team_scores[score.team]['defense'][1] += score.defense
        team_scores[score.team]['sla'][0][score.service] = score.sla
        team_scores[score.team]['sla'][1] += score.sla
        team_scores[score.team]['total'] += score.total

    sorted_team_scores = OrderedDict(sorted(team_scores.items(), key=lambda s: s[1]['total'], reverse=True))
    cache.set(cache_key, sorted_team_scores, 10)

    return sorted_team_scores


def flagstore_scores():
    """
    Returns the per-flagstore offense/defense breakdown as currently stored in the database as a dict in this
    format:

        {team: {service: {flagstore: {'offense': offense_points, 'defense': defense_points}}}}

    Every service has per-store rows (single-store services just have flagstore 0), so this covers all
    services. The aggregate rows (flagstore IS NULL) are excluded.
    """

    # No good way to invalidate the cache, so use a generic key with a short timeout
    cache_key = 'flagstore-scores'
    cached_scores = cache.get(cache_key)

    if cached_scores is not None:
        return cached_scores

    flagstore_team_scores = defaultdict(lambda: defaultdict(dict))

    for score in models.ScoreBoard.objects.filter(flagstore__isnull=False) \
                                          .only('team__user__id', 'service__id', 'flagstore', 'attack',
                                                'defense'):
        flagstore_team_scores[score.team_id][score.service_id][score.flagstore] = {
            'offense': score.attack,
            'defense': score.defense
        }

    # Convert defaultdicts to dicts because serialization in `cache.set()` can't handle them otherwise
    flagstore_team_scores = {team_id: dict(service_scores)
                             for team_id, service_scores in flagstore_team_scores.items()}
    cache.set(cache_key, flagstore_team_scores, 10)

    return flagstore_team_scores


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

    status_checks = models.StatusCheck.objects.filter(task__tick__gte=from_tick, task__tick__lte=to_tick) \
                                              .exclude(status=models.StatusCheck.STATUSES[_('timeout')]) \
                                              .select_related('task')
    for check in status_checks:
        statuses[teams[check.task.team_id]][check.task.tick][check.task.service_id] = check.status

    # Convert defaultdicts to dicts because serialization in `cache.set()` can't handle them otherwise
    for key, val in statuses.items():
        statuses[key] = dict(val)
    cache.set(cache_key, statuses, 10)

    return statuses
