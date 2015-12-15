from collections import defaultdict, OrderedDict

from django.db.models import Count
from django.utils.translation import ugettext as _

from ctf_gameserver.web.registration.models import Team
from . import models

# Base value for the (offense) points per service and tick, all other scores are calculated as a function of
# this
BASE_POINTS = 100


def score(last_tick):
    """
    Returns the score up to the current time (for the offense points) resp. the specified tick (for the
    SLA points) as an OrderedDict in this format:

        {team: {
            'offense': [{service: offense_points}, total_offense_points],
            'sla': [{service: sla_points}, total_sla_points],
            'total': total_points
        }}

    The result is sorted by the total points.
    """

    team_scores = {}

    for team in Team.active_not_nop_objects.all():
        team_scores[team] = {
            'offense': [defaultdict(lambda: 0.0), 0.0],
            'sla': [defaultdict(lambda: 0.0), 0.0],
            'total': 0.0
        }

    game_control = models.GameControl.objects.get()

    # REVISIT when assumptions about tick values are fixed
    if not (game_control.competition_running() or game_control.competition_over()) or last_tick < 1:
        return team_scores

    # Offense points per service (nested per team)
    service_offense_points = {}
    # SLA points per service (nested per team)
    service_sla_shares = {}

    for service in models.Service.objects.all():
        service_offense_points[service] = _capture_points(service)
        service_sla_shares[service] = _uptime_shares(service, last_tick)

    # Total offense points of all teams and services
    global_offense_points = 0
    number_of_services = models.Service.objects.count()

    for team in Team.active_not_nop_objects.all():
        for service, team_points in service_offense_points.items():
            team_scores[team]['offense'][0][service] = team_points[team]
            team_scores[team]['offense'][1] += team_points[team]
            team_scores[team]['total'] += team_points[team]
            global_offense_points += team_points[team]

    for team in Team.active_not_nop_objects.all():
        for service, team_shares in service_sla_shares.items():
            sla_score = team_shares[team] * global_offense_points / number_of_services
            team_scores[team]['sla'][0][service] = sla_score
            team_scores[team]['sla'][1] += sla_score
            team_scores[team]['total'] += sla_score

    return OrderedDict(sorted(team_scores.items(), key=lambda t: t[1]['total'], reverse=True))


def _capture_points(service):
    """
    Returns the (offense) points for all flags captured from the specified service up to the moment when it
    is called. The result is a mapping from teams to their respective points.
    """

    captures = models.Capture.objects.filter(flag__service=service)

    # Explicitly remove possible default ordering which could mess up the aggregation results
    tick_capture_counts_list = captures.order_by().values('flag__tick').annotate(value=Count('flag__tick'))
    # Mapping from ticks to the total number of captures of flags which had been generated in that tick
    tick_capture_counts = {c['flag__tick']: c['value'] for c in tick_capture_counts_list}

    # Points scored by capturing flags from this service per team
    team_points = defaultdict(lambda: 0.0)
    game_control = models.GameControl.objects.get()

    for capture in captures:
        reference_tick = capture.flag.tick - game_control.valid_ticks

        # REVISIT when assumptions about tick values are fixed
        if reference_tick < 1:
            reference_tick = 1

        # This is prone to non-repeatable reads after the generation of captures_per_tick
        try:
            points = BASE_POINTS / tick_capture_counts[reference_tick]
        except KeyError:
            points = BASE_POINTS

        team_points[capture.capturing_team] += points

    return team_points


def _uptime_shares(service, last_tick):
    """
    Returns the share (i.e. percentage) of one team in all ticks for which the specified service has been
    checked as 'up'. The result is a mapping from teams to their respective shares.
    """

    up = models.StatusCheck.STATUSES[_('up')]
    status_checks = models.StatusCheck.objects.filter(service=service, tick__lte=last_tick, status=up)

    # Total number of status checks with result 'up' for this service
    global_count = status_checks.count()
    # Number of status checks with result 'up' per team
    team_counts = status_checks.order_by().values('team').annotate(value=Count('team'))

    # Share in the total 'up' checks per team
    team_shares = defaultdict(lambda: 0.0)

    for count in team_counts:
        team = Team.objects.get(pk=count['team'])
        team_shares[team] = count['value'] / global_count

    return team_shares


def team_statuses(tick):
    """
    Returns the status of all teams and all services in the specified tick. The result is a mapping from
    teams to a mapping from services to the respective status string.
    """

    team_statuses = {}
    status_checks = models.StatusCheck.objects.filter(tick=tick)

    for team in Team.active_objects.all():
        team_status_checks = status_checks.filter(team=team)
        team_statuses[team] = {check.service: check.get_status_display() for check in team_status_checks}

    return team_statuses
