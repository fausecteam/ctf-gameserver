from collections import defaultdict

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page

import ctf_gameserver.web.registration.models as registration_models

from . import models, calculations
from .decorators import registration_closed_required, services_public_required


@services_public_required('html')
def scoreboard(request):

    return render(request, 'scoreboard.html', {
        'services': models.Service.objects.all()
    })


# Short cache timeout only, because there is already caching going on in calculations
@cache_page(5)
@services_public_required('json')
def scoreboard_json(_):

    game_control = models.GameControl.get_instance()

    if game_control.competition_over():
        to_tick = game_control.current_tick
    else:
        to_tick = game_control.current_tick - 1

    scores = calculations.scores(['team', 'team__user', 'service'],
                                 ['team__image', 'team__user__username', 'service__name'])
    statuses = calculations.team_statuses(to_tick, to_tick, only_team_fields=['user_id'])
    services = models.Service.objects.all()

    response = {
        'tick': to_tick,
        'teams': [],
        'status-descriptions': _get_status_descriptions()
    }

    for rank, (team, points) in enumerate(scores.items(), start=1):
        team_entry = {
            'rank': rank,
            'id': team.user.pk,
            'name': team.user.username,
            'services': [],
            'offense': points['offense'][1],
            'defense': points['defense'][1],
            'sla': points['sla'][1],
            'total': points['total'],
        }
        if team.image:
            team_entry['image'] = team.image.url
            team_entry['thumbnail'] = team.image.get_thumbnail_url()

        for service in services:
            try:
                offense = points['offense'][0][service]
                defense = points['defense'][0][service]
                sla = points['sla'][0][service]
            except KeyError:
                offense = 0
                defense = 0
                sla = 0
            try:
                status = statuses[team][to_tick][service.pk]
            except KeyError:
                status = ''
            team_entry['services'].append({
                'status': status,
                'offense': offense,
                'defense': defense,
                'sla': sla
            })

        response['teams'].append(team_entry)

    return JsonResponse(response)


@services_public_required('json')
def scoreboard_json_ctftime(_):
    """
    View which returns the scoreboard in CTFTime scoreboard feed format,
    see https://ctftime.org/json-scoreboard-feed.
    """

    standings = []
    scores = calculations.scores(['team', 'team__user'], ['team__user__username'])

    for rank, (team, team_points) in enumerate(scores.items(), start=1):
        task_stats = defaultdict(lambda: {'points': 0.0})
        for point_type in ('offense', 'defense', 'sla'):
            for service, points in team_points[point_type][0].items():
                task_stats[service.name]['points'] += points

        for service_name in task_stats:
            task_stats[service_name] = {'points': round(task_stats[service_name]['points'], 4)}

        standings.append({
            'pos': rank,
            'team': team.user.username,
            'score': round(team_points['total'], 4),
            'taskStats': task_stats
        })

    return JsonResponse({'tasks': list(task_stats.keys()), 'standings': standings})


@services_public_required('html')
def service_status(request):

    return render(request, 'service_status.html')


# Short cache timeout only, because there is already caching going on in calculations
@cache_page(5)
@services_public_required('json')
def service_status_json(_):

    game_control = models.GameControl.get_instance()
    to_tick = game_control.current_tick
    from_tick = max(to_tick - 4, 0)

    statuses = calculations.team_statuses(from_tick, to_tick, ['user'], ['image', 'nop_team',
                                                                         'user__username'])
    services = models.Service.objects.all().order_by('name')

    response = {
        'ticks': list(range(from_tick, to_tick+1)),
        'teams': [],
        'services': [],
        'status-descriptions': _get_status_descriptions()
    }

    for team, tick_statuses in statuses.items():
        team_entry = {
            'id': team.user.pk,
            'nop': team.nop_team,
            'name': team.user.username,
            'ticks': [],
        }
        if team.image:
            team_entry['image'] = team.image.url
            team_entry['thumbnail'] = team.image.get_thumbnail_url()

        for tick in response['ticks']:
            tick_services = []
            for service in services:
                try:
                    tick_services.append(tick_statuses[tick][service.pk])
                except KeyError:
                    tick_services.append('')
            team_entry['ticks'].append(tick_services)

        response['teams'].append(team_entry)

    for service in services:
        response['services'].append(service.name)

    return JsonResponse(response)


@cache_page(60)
# Don't provide a list of all teams while registration is open to prevent
# crawling of registered teams and comparing with this list
@registration_closed_required
def teams_json(_):

    teams = registration_models.Team.active_objects.values_list('net_number', flat=True)

    game_control = models.GameControl.get_instance()
    # Only publish Flag IDs after the respective Tick is over
    flagid_max_tick = game_control.current_tick - 1
    flagid_min_tick = flagid_max_tick - game_control.valid_ticks

    flag_ids = defaultdict(lambda: defaultdict(lambda: []))
    for flag in models.Flag.objects.exclude(flagid=None) \
                                   .exclude(flagid='') \
                                   .filter(tick__gte=flagid_min_tick, tick__lte=flagid_max_tick) \
                                   .select_related('service', 'protecting_team') \
                                   .only('service__name', 'protecting_team__net_number', 'flagid'):
        flag_ids[flag.service.name][flag.protecting_team.net_number].append(flag.flagid)

    response = {
        'teams': sorted(list(teams)),
        'flag_ids': flag_ids
    }

    return JsonResponse(response, json_dumps_params={'indent': 2})


@staff_member_required
def service_history(request):

    game_control = models.GameControl.get_instance()
    max_tick = game_control.current_tick
    min_tick = max(max_tick - 30, 0)

    return render(request, 'service_history.html', {
        'services': models.Service.objects.all().order_by('name'),
        'initial_min_tick': min_tick,
        'initial_max_tick': max_tick
    })


@staff_member_required
def service_history_json(request):
    """
    View which returns the check results for a specific service for all teams in JSON format, as required
    by the JavaScript code in service_history().
    """

    service_slug = request.GET.get('service')
    if service_slug is None:
        return JsonResponse({'error': 'Service must be specified'}, status=400)

    try:
        service = models.Service.objects.get(slug=service_slug)
    except models.Service.DoesNotExist:
        return JsonResponse({'error': 'Unknown service'}, status=404)

    max_tick = models.GameControl.get_instance().current_tick
    try:
        from_tick = int(request.GET.get('from-tick', 0))
        to_tick = int(request.GET.get('to-tick', max_tick+1))
    except ValueError:
        return JsonResponse({'error': 'Ticks must be integers'})

    status_checks = models.StatusCheck.objects.filter(service=service) \
                                              .filter(tick__gte=from_tick, tick__lt=to_tick) \
                                              .select_related('team', 'team__user') \
                                              .only('tick', 'status', 'team__user__id', 'team__net_number') \
                                              .order_by('team__user__id', 'tick')

    # Get teams separately to reduce size of "status_checks" result
    teams = registration_models.Team.active_objects.select_related('user').only('net_number',
                                                                                'user__username').in_bulk()
    max_team_id = registration_models.Team.active_objects.aggregate(Max('user__id'))['user__id__max']

    result = []
    current_team = {'id': 0}
    current_tick = from_tick

    def append_result(next_team_id):
        nonlocal current_team, current_tick

        # Fill up completely missing teams (i.e. they don't have any status checks in the selected ticks)
        fillup_team_id = current_team['id'] + 1
        while fillup_team_id < next_team_id:
            try:
                result.append({'id': fillup_team_id, 'name': teams[fillup_team_id].user.username,
                               'checks': [-1]*(to_tick-from_tick),
                               'net_number': teams[fillup_team_id].net_number})
            except KeyError:
                # No team with this ID
                pass
            fillup_team_id += 1

        # First call of `append_result()` (before any checks have been processed) has no data to add
        if current_team['id'] != 0:
            # Fill up missing ticks at the end
            while current_tick < to_tick:
                current_team['checks'].append(-1)
                current_tick += 1
            result.append(current_team)

    for check in status_checks:
        # Status checks are ordered by team ID, finalize result for a team when it changes
        if current_team['id'] != check.team.user.id:
            append_result(check.team.user.id)
            current_team = {'id': check.team.user.id, 'name': teams[check.team.user.id].user.username,
                            'checks': [], 'net_number': teams[check.team.user.id].net_number}
            current_tick = from_tick

        # Fill up missing ticks
        while current_tick < check.tick:
            current_team['checks'].append(-1)
            current_tick += 1

        current_team['checks'].append(check.status)
        current_tick = check.tick + 1

    # Add result from last iteration
    append_result(max_team_id+1)

    response = {
        'teams': result,
        'min-tick': from_tick,
        'max-tick': to_tick-1,
        'service-name': service.name,
        'service-slug': service.slug,
        'status-descriptions': _get_status_descriptions()
    }
    if hasattr(settings, 'GRAYLOG_SEARCH_URL'):
        response['graylog-search-url'] = settings.GRAYLOG_SEARCH_URL

    return JsonResponse(response)


def _get_status_descriptions():

    status_descriptions = {num: desc for desc, num in models.StatusCheck.STATUSES.items()}
    status_descriptions[-1] = 'not checked'

    return status_descriptions


@staff_member_required
def missing_checks(request):

    game_control = models.GameControl.get_instance()
    # For the current tick, "not checked" can also mean "still scheduled or running", so it makes little
    # sense to include it
    max_tick = game_control.current_tick - 1
    min_tick = max(max_tick - 30, 0)

    return render(request, 'missing_checks.html', {
        'services': models.Service.objects.all().order_by('name'),
        'initial_min_tick': min_tick,
        'initial_max_tick': max_tick
    })


@staff_member_required
def missing_checks_json(request):
    """
    View which returns the teams with status "not checked" or "timeout" per tick for a specific service. The
    result is in JSON format as required by the JavaScript code in missing_checks().
    This can help to find unhandled exceptions in checker scripts, as "not checked" normally shouldn't occur.
    """

    service_slug = request.GET.get('service')
    if service_slug is None:
        return JsonResponse({'error': 'Service must be specified'}, status=400)

    try:
        service = models.Service.objects.get(slug=service_slug)
    except models.Service.DoesNotExist:
        return JsonResponse({'error': 'Unknown service'}, status=404)

    max_tick = models.GameControl.get_instance().current_tick - 1
    try:
        from_tick = int(request.GET.get('from-tick', 0))
        to_tick = int(request.GET.get('to-tick', max_tick+1))
    except ValueError:
        return JsonResponse({'error': 'Ticks must be integers'})

    status_timeout = models.StatusCheck.STATUSES[_('timeout')]

    all_flags = models.Flag.objects.filter(service=service) \
                                   .filter(tick__gte=from_tick, tick__lt=to_tick) \
                                   .values_list('tick', 'protecting_team')
    all_status_checks = models.StatusCheck.objects.filter(service=service) \
                                                  .filter(tick__gte=from_tick, tick__lt=to_tick) \
                                                  .exclude(status=status_timeout) \
                                                  .values_list('tick', 'team')
    checks_missing = all_flags.difference(all_status_checks).order_by('-tick', 'protecting_team')

    checks_timeout = defaultdict(set)
    for tick, team in models.StatusCheck.objects.filter(service=service) \
                                                .filter(tick__gte=from_tick, tick__lt=to_tick) \
                                                .filter(status=status_timeout) \
                                                .values_list('tick', 'team'):
        checks_timeout[tick].add(team)

    result = []
    current_tick = {'tick': -1}

    def append_result():
        nonlocal current_tick

        # First call of `append_result()` (before any checks have been processed) has no data to add
        if current_tick['tick'] != -1:
            result.append(current_tick)

    for check in checks_missing:
        check_tick, check_team = check

        # Status checks are ordered by tick, finalize result for a tick when it changes
        if current_tick['tick'] != check_tick:
            append_result()
            current_tick = {'tick': check_tick, 'teams': []}

        current_tick['teams'].append((check_team, check_team in checks_timeout[check_tick]))

    # Add result from last iteration
    append_result()

    teams = registration_models.Team.active_objects.select_related('user') \
                                                   .only('pk', 'net_number', 'user__username')
    teams_dict = {}
    for team in teams:
        teams_dict[team.pk] = {'name': team.user.username, 'net-number': team.net_number}

    response = {
        'checks': result,
        'all-teams': teams_dict,
        'min-tick': from_tick,
        'max-tick': to_tick-1,
        'service-name': service.name,
        'service-slug': service.slug
    }
    if hasattr(settings, 'GRAYLOG_SEARCH_URL'):
        response['graylog-search-url'] = settings.GRAYLOG_SEARCH_URL

    return JsonResponse(response)
