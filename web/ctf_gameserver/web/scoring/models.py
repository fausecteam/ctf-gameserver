from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from ctf_gameserver.web.registration.models import Team


class Service(models.Model):
    """
    Database representation of a service from the competition.
    """

    name = models.CharField(max_length=30, unique=True)


class Flag(models.Model):
    """
    Database representation of a flag. The actual flag string needn't be stored, as it can easily be
    reconstructed from this information.
    """

    service = models.ForeignKey(Service)
    protecting_team = models.ForeignKey(Team)
    tick = models.PositiveSmallIntegerField()
    # NULL means the flag has been generated, but not yet placed
    placement_time = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        unique_together = ('service', 'protecting_team', 'tick')


class Capture(models.Model):
    """
    Database representation of a capture, i.e. the (successful) submission of a particular flag by one team.
    """

    flag = models.ForeignKey(Flag)
    capturing_team = models.ForeignKey(Team)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('flag', 'capturing_team')


class StatusCheck(models.Model):
    """
    Storage for the result from a status check. We store the checker script's result for every service and
    team per tick.
    """

    # Mapping from human-readable status texts to their integer values in the database
    # For a discussion on the plural form of "status", refer to https://english.stackexchange.com/q/877
    STATUSES = {
        _('up'): 0,
        _('faulty'): 1,
        _('down'): 2
    }

    service = models.ForeignKey(Service)
    team = models.ForeignKey(Team)
    tick = models.PositiveSmallIntegerField()
    status = models.PositiveSmallIntegerField(choices=[(i, t) for t, i in STATUSES.items()])
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('service', 'team', 'tick')


class GameControl(models.Model):
    """
    Single-column database table to store control information for the competition.
    """

    # Make start end and NULL-able (for the initial state), but not blank-able (have to be set upon editing)
    start = models.DateTimeField(null=True)
    end = models.DateTimeField(null=True)
    current_tick = models.PositiveSmallIntegerField(default=0, editable=False)

    def clean(self):
        """
        Ensures that only one instance of the class gets created.
        Inspired by https://stackoverflow.com/a/6436008.
        """
        cls = self.__class__

        if cls.objects.count() > 0 and self.id != cls.objects.get().id:
            # pylint: disable=no-member
            raise ValidationError(_('Only a single instance of {} can be created').format(cls.__name__))
