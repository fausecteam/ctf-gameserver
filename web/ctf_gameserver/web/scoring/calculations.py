from collections import defaultdict, OrderedDict
from math import ceil

from django.core.cache import cache
from django.db.models import Count, Max
from django.utils.translation import ugettext as _

from ctf_gameserver.web.registration.models import Team
from . import models


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
