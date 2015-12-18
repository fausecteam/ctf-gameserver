from collections import defaultdict, OrderedDict
from math import ceil

from django.core.cache import cache
from django.db.models import Count, Max
from django.utils.translation import ugettext as _

from ctf_gameserver.web.registration.models import Team
from . import models


def _zero():
    """
    Helper function which just returns zero as float.
    It is designed as 'default_factory' argument for defaultdicts to be cached, as they cannot be pickled
    when using anonymous functions.
    """

    return 0.0


def _empty_dict():
    """
    Helper function which just returns an empty dictionary.
    It is designed as 'default_factory' argument for defaultdicts to be cached, as they cannot be pickled
    when using anonymous functions.
    """

    return {}

def _zero_defaultdict():
    """
    TODO
    """

    return defaultdict(_zero)


def score(to_tick):
    """
    Returns the score up to the current time (for the offense and defense points) resp. the specified tick
    (for the SLA points) as an OrderedDict in this format:

        {team: {
            'offense': [{service: offense_points}, total_offense_points],
            'defense': [{service: defense_points}, total_defense_points],
            'sla': [{service: sla_points}, total_sla_points],
            'total': total_points
        }}

    The result is sorted by the total points.
    """

    cache_key = 'score_tick-{:d}'.format(to_tick)
    cached_scores = cache.get(cache_key)

    if cached_scores is not None:
        return cached_scores

    team_scores = {}

    for team in Team.active_not_nop_objects.all():
        team_scores[team] = {
            'offense': [defaultdict(_zero), 0.0],
            'defense': [defaultdict(_zero), 0.0],
            'sla': [defaultdict(_zero), 0.0],
            'total': 0.0
        }

    game_control = models.GameControl.objects.get()

    if not (game_control.competition_running() or game_control.competition_over()) or to_tick < 0:
        return team_scores

    service_scores = {}

    for service in models.Service.objects.all():
        service_offense_scores = defaultdict(_zero)
        service_defense_scores = defaultdict(_zero)

        for tick in range(0, to_tick+1):
            offense_scores = _offense_scores(service, tick)
            defense_scores = _defense_scores(service, tick)

            for team in models.Team.active_not_nop_objects.all():
                service_offense_scores[team] += offense_scores[team]
                service_defense_scores[team] += defense_scores[team]

        sla_scores = _sla_scores(service, to_tick, service_offense_scores)

        service_scores[service] = {
            'offense': service_offense_scores,
            'defense': service_defense_scores,
            'sla': sla_scores
        }

    for team in models.Team.active_not_nop_objects.all():
        for service, score in service_scores.items():
            for key in ('offense', 'defense', 'sla'):
                team_scores[team][key][0][service] = score[key][team]
                team_scores[team][key][1] += score[key][team]
                team_scores[team]['total'] += score[key][team]

    sorted_team_scores = OrderedDict(sorted(team_scores.items(), key=lambda t: t[1]['total'], reverse=True))
    cache.set(cache_key, sorted_team_scores)

    return sorted_team_scores


def _offense_scores(service, tick):
    """
    Returns the offense score for flags captured from the specified service in the specified tick. The result
    is a mapping from teams to their respective points.
    """

    try:
        flag_value = float(Team.active_not_nop_objects.count()) / \
                     models.Capture.objects.filter(flag__service=service, tick=tick).count()
    except ZeroDivisionError:
        flag_value = None

    captures = models.Capture.objects.filter(flag__service=service, tick=tick)

    # Explicitly remove possible default ordering which could mess up the aggregation results
    flag_capture_counts_list = models.Capture.objects.filter(tick=tick).order_by().values('flag') \
                                                     .annotate(value=Count('flag'))
    flag_capture_counts = {c['flag']: c['value'] for c in flag_capture_counts_list}

    team_scores = defaultdict(_zero)


    for capture in captures:
        team_scores[capture.capturing_team] += flag_value / flag_capture_counts[capture.flag.id]

    return team_scores


def _defense_scores(service, tick):
    """
    Returns the defense score for the specified service in the specified tick. The result is a mapping from
    teams to their respective points.
    """

    def defense_rating(stolen_flags_count):
        """
        Returns a number of points depending on the given count of captured flags, assuming at most one flag
        can be captured per tick (on average over all ticks).
        """
        if stolen_flags_count < 0:
            raise ValueError('Invalid argument for defense_rating()')
        elif stolen_flags_count == 0:
            return 1.0
        elif stolen_flags_count >= 1 and stolen_flags_count <= 50:
            return (50 - stolen_flags_count) / (49.0 * 2)
        else:
            return 0.0

    valid_ticks = models.GameControl.objects.get().valid_ticks
    from_tick = tick - valid_ticks + 1

    team_scores = {}

    team_capture_counts_list = models.Capture.objects.filter(flag__service=service, flag__tick__gte=from_tick,
                               tick__lte=tick).order_by().values('flag__protecting_team').annotate(value=Count('flag__protecting_team'))
    team_capture_counts = {c['flag__protecting_team']: c['value'] for c in team_capture_counts_list}

    for team in Team.active_not_nop_objects.all():
        try:
            capture_count = team_capture_counts[team.pk]
        except KeyError:
            capture_count = 0
        # For each tick, at most `valid_ticks` flags can be counted as submitted
        team_scores[team] = defense_rating(ceil(capture_count / float(valid_ticks)))

    return team_scores


def _sla_scores(service, tick, offense_scores):
    """
    Returns the share (i.e. percentage) of one team in all ticks for which the specified service has been
    checked as 'up'. The result is a mapping from teams to their respective shares.
    TODO
    """

    up = [models.StatusCheck.STATUSES[_('up')], models.StatusCheck.STATUSES[_('recovering')]]
    status_checks = models.StatusCheck.objects.filter(service=service, tick__lte=tick, status__in=up)

    # Number of status checks with result 'up' per team
    team_counts = status_checks.order_by().values('team').annotate(value=Count('team'))
    team_counts_max = team_counts.aggregate(Max('value'))['value__max']

    offense_score_max = max(offense_scores.values())
    team_scores = defaultdict(_zero)

    for count in team_counts:
        team = Team.objects.get(pk=count['team'])
        team_scores[team] = (count['value'] / float(team_counts_max)) * offense_score_max

    return team_scores


def team_statuses(from_tick, to_tick):
    """
    Returns the statuses of all teams and all services in the specified range of ticks. The result is an
    OrderedDict sorted by the team's names in this format:

        {'team': {
            'tick': {
                'service': status
            }
        }}
    """

    cache_key = 'team-statuses_{:d}-{:d}'.format(from_tick, to_tick)
    cached_statuses = cache.get(cache_key)

    if cached_statuses is not None:
        return cached_statuses

    statuses = {}
    status_checks = models.StatusCheck.objects.filter(tick__gte=from_tick, tick__lte=to_tick)

    for team in Team.active_objects.all():
        statuses[team] = {}

        for tick in range(from_tick, to_tick+1):
            statuses[team][tick] = {}
            for service in models.Service.objects.all():
                statuses[team][tick][service] = ''

        for check in status_checks.filter(team=team):
            statuses[team][check.tick][check.service] = check.get_status_display()

    sorted_statuses = OrderedDict(sorted(statuses.items(), key=lambda s: s[0].user.username))
    cache.set(cache_key, sorted_statuses, 10)

    return sorted_statuses
