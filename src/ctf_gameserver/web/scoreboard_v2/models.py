from django.db import models

from ctf_gameserver.web.registration.models import Team
from ctf_gameserver.web.scoring.models import Service


class Board(models.Model):
    """
    Scoreboard as calculated by external, asyncron helper. May be a
    (materialized) view or a real table and should just be handled
    read-only from within the website.
    """
    tick = models.IntegerField(editable=False, primary_key=True)
    team = models.OneToOneField(Team, editable=False, on_delete=models.PROTECT)
    service = models.OneToOneField(Service, editable=False, on_delete=models.PROTECT)
    attack = models.FloatField(editable=False)
    defense = models.FloatField(editable=False)
    sla = models.FloatField(editable=False)
    flags_captured = models.IntegerField(editable=False)
    flags_lost = models.IntegerField(editable=False)

    class Meta:
        managed = False # django should not create a table for this
        constraints = [
            models.UniqueConstraint(fields=['tick', 'team', 'service'], name='unique_per_tick')
        ]

    def __str__(self):
        return 'Score for tick {} and team {}'.format(self.tick, self.team)

class FirstBloods(models.Model):
    """
    First team to capture a flag per service.
    Calculated externally. May be a view or a real table
    and should just be handled read-only from within the website.
    """
    service = models.OneToOneField(Service, primary_key=True, editable=False, on_delete=models.PROTECT)
    team = models.OneToOneField(Team, editable=False, on_delete=models.PROTECT)
    tick = models.IntegerField(editable=False)
    timestamp = models.DateTimeField(editable=False)

    class Meta:
        managed = False # django should not create a table for this

    def __str__(self):
        return 'Firstblood of service {} by team {} in tick {}'.format(self.service, self.team, self.tick)
