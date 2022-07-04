from collections import defaultdict, OrderedDict

from django.core.cache import cache

from django.db.models import F, Max

from . import models


def scores(tick):
    """
    Returns the scores as currently stored in the database as an OrderedDict
    and the attackers/victims per service in this format:

        {team_id: {
            'services': {
                service_id: {
                    offense_score, offense_delta,
                    defense_score, defense_delta,
                    sla_score, sla_delta,
                    flags_captured, flags_captured_delta,
                    flags_lost, flags_lost_delta
                }}
            'total': {
                total_score,
                offense_score, offense_delta,
                defense_score, defense_delta,
                sla_score, sla_delta
            }
        }},
        {service_id: {
            attackers,
            victims
        }}

    The scores are sorted by the total_score.
    """

    team_scores = defaultdict(lambda: {
        'services': defaultdict(lambda: {
            'offense_score': 0, 'offense_delta': 0,
            'defense_score': 0, 'defense_delta': 0,
            'sla_score': 0, 'sla_delta': 0,
            'flags_captured': 0, 'flags_captured_delta': 0,
            'flags_lost': 0, 'flags_lost_delta': 0,
        }),
        'total': {
            'total_score': 0,
            'offense_score': 0, 'offense_delta': 0,
            'defense_score': 0, 'defense_delta': 0,
            'sla_score': 0, 'sla_delta': 0,
        }
    })

    for score in models.Board.objects.filter(tick=tick).all():
        srv = team_scores[score.team_id]['services'][score.service_id]
        srv['offense_score']  = srv['offense_delta']        = score.attack
        srv['defense_score']  = srv['defense_delta']        =  score.defense
        srv['sla_score']      = srv['sla_delta']            = score.sla
        srv['flags_captured'] = srv['flags_captured_delta'] = score.flags_captured
        srv['flags_lost']     = srv['flags_lost_delta']     = score.flags_lost
        total = team_scores[score.team_id]['total']
        total['offense_score'] += score.attack
        total['defense_score'] += score.defense
        total['sla_score']     += score.sla
        total['total_score']   += score.attack + score.defense + score.sla

    # calculate the difference to the previous tick (if any)
    for score in models.Board.objects.filter(tick=tick - 1).all():
        srv = team_scores[score.team_id]['services'][score.service_id]
        srv['offense_delta']        -= score.attack
        srv['defense_delta']        -= score.defense
        srv['sla_delta']            -= score.sla
        srv['flags_captured_delta'] -= score.flags_captured
        srv['flags_lost_delta']     -= score.flags_lost
        total = team_scores[score.team_id]['total']
        total['offense_delta'] += srv['offense_delta']
        total['defense_delta'] += srv['defense_delta']
        total['sla_delta']     += srv['sla_delta']
    
    attackers_victims = defaultdict(lambda: {'attackers': 0, 'victims': 0})
    for team in team_scores.values():
        for service_id, service in team['services'].items():
            attackers_victims[service_id]['attackers'] += int(service['flags_captured_delta'] > 0)
            attackers_victims[service_id]['victims']   += int(service['flags_lost_delta'] > 0)

    sorted_team_scores = OrderedDict(sorted(team_scores.items(),
        key=lambda kv: kv[1]['total']['total_score'], reverse=True))

    return sorted_team_scores, attackers_victims

def get_scoreboard_tick():
    """
    Get the maximum tick to display on the scoreboard. Usually equal current_tick - 1
    """
    # max tick of scoreboard
    scoreboard_tick = models.Board.objects.aggregate(max_tick=Max('tick'))['max_tick']
    if scoreboard_tick is None:
        # game has not started: current_tick < 0
        # return -1 so scoreboard already shows services when they are public
        return -1
    return scoreboard_tick

def get_firstbloods(scoreboard_tick):
    """
    Get the first bloods for each service (if any).
    """

    # cache based on scoreboard_tick which invalidates the cache
    # when update_scoring() ran in the controller
    cache_key = 'scoreboard_v2_firstbloods_{:d}'.format(scoreboard_tick)
    cached_firstbloods = cache.get(cache_key)

    if cached_firstbloods is not None:
        return cached_firstbloods

    firstbloods = models.FirstBloods.objects.only('service_id', 'team_id', 'tick').all()
    
    cache.set(cache_key, firstbloods, 90)

    return firstbloods

def per_team_scores(team_id, service_ids_order):
    """
    Get the point development of a team during all past ticks.
    Returns an array of arrays.
    The first index is the service in the order given by "service_ids_order".
    The second index is the tick.
    So result[0][0] is the score from service with id service_ids_order[0] and tick 0.
    """
    scoreboard_tick = get_scoreboard_tick()

    # cache based on team_id and scoreboard_tick which invalidates the cache
    # when update_scoring() ran in the controller
    cache_key = 'scoreboard_v2_team_scores_{:d}_{:d}'.format(team_id, scoreboard_tick)
    cached_team_scores = cache.get(cache_key)

    if cached_team_scores is not None:
        return cached_team_scores

    team_total_scores = models.Board.objects \
        .annotate(points=F('attack')+F('defense')+F('sla')) \
        .filter(team_id = team_id, tick__lte = scoreboard_tick) \
        .order_by('tick') \
        .values('service_id', 'points')

    result =  list([] for _ in service_ids_order)

    for total_score in team_total_scores:
        result[service_ids_order.index(total_score['service_id'])].append(total_score['points'])
    
    cache.set(cache_key, result, 90)

    return result
