from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ctf_gameserver.web.registration.models import Team


class Service(models.Model):
    """
    Database representation of a service from the competition.
    """

    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=30, unique=True, help_text=_('Simplified name for use in paths'))
    margin = models.PositiveIntegerField(default=30,
                                         help_text=_('Safety margin (in seconds) for checker scheduling, '
                                                     'gets added to the automatically determined check '
                                                     'duration'))

    def __str__(self):    # pylint: disable=invalid-str-returned
        return self.name


class Flag(models.Model):
    """
    Database representation of a flag. The actual flag string needn't be stored, as its relevant parts can be
    reconstructed from this information.
    """

    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    protecting_team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tick = models.PositiveIntegerField()
    # NULL means the flag has been generated, but not yet placed
    placement_start = models.DateTimeField(null=True, blank=True, default=None)
    placement_end = models.DateTimeField(null=True, blank=True, default=None)
    # Optional identifier to help Teams retrieve the Flag, we don't enforce this to uniquely identify a Flag
    flagid = models.CharField(max_length=200, null=True, blank=True, default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['service', 'protecting_team', 'tick'],
                                    name='scoring_flag_service_protecting_team_tick_uniq')
        ]
        indexes = [
            models.Index(fields=['service', 'tick']),
            models.Index(fields=['service', 'protecting_team', 'tick'])
        ]

    def __str__(self):
        return 'Flag {:d}'.format(self.id)


class Capture(models.Model):
    """
    Database representation of a capture, i.e. the (successful) submission of a particular flag by one team.
    """

    flag = models.ForeignKey(Flag, on_delete=models.PROTECT)
    capturing_team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tick = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This constraint is necessary for correct behavior of the submission server
        constraints = [
            models.UniqueConstraint(fields=['flag', 'capturing_team'],
                                    name='scoring_capture_flag_capturing_team_uniq')
        ]
        indexes = [
            models.Index(fields=['flag', 'capturing_team'])
        ]

    def __str__(self):
        return 'Capture {:d}'.format(self.id)


class StatusCheck(models.Model):
    """
    Storage for the result from a status check. We store the checker script's result for every service and
    team per tick.
    """

    # Mapping from human-readable status texts to their integer values in the database
    # For a discussion on the plural form of "status", refer to https://english.stackexchange.com/q/877
    STATUSES = {
        # "up" maps to "OK" from the checkers' perspective
        _('up'): 0,
        _('down'): 1,
        _('faulty'): 2,
        _('flag not found'): 3,
        _('recovering'): 4,
        # Script has been forcefully terminated at end of tick, publicly displayed as "Not checked"
        _('timeout'): 5
    }

    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tick = models.PositiveIntegerField(db_index=True)
    # REVISIT: Add check constraint for the values as soon as we have Django >= 2.2
    status = models.SmallIntegerField(choices=[(i, t) for t, i in STATUSES.items()])
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['service', 'team', 'tick'],
                                    name='scoring_statuscheck_service_team_tick_uniq')
        ]
        indexes = [
            models.Index(fields=['service', 'tick', 'status']),
            models.Index(fields=['service', 'team', 'status'])
        ]

    def __str__(self):
        return 'Status check {:d}'.format(self.id)


class ScoreBoard(models.Model):
    """
    Calculated current state of the scoreboard.
    Can be recreated from other data at any point, but persisted for performance reasons.
    """
    team = models.ForeignKey(Team, editable=False, on_delete=models.PROTECT)
    service = models.ForeignKey(Service, editable=False, on_delete=models.PROTECT)
    attack = models.FloatField(editable=False)
    defense = models.FloatField(editable=False)
    sla = models.FloatField(editable=False)
    total = models.FloatField(editable=False)

    class Meta:
        ordering = ('team', '-total', '-attack', '-defense')

    def __str__(self):
        return 'Score for team {}'.format(self.team)


class CheckerState(models.Model):
    """
    Persistent state from Checker Scripts.
    """

    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    data = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['service', 'team', 'key'],
                                    name='scoring_checkerstate_service_team_key_uniq')
        ]
        indexes = [
            models.Index(fields=['service', 'team', 'key'])
        ]

    def __str__(self):
        return 'Checker state "{}" for service {} and team {}'.format(self.key, self.service, self.team)


class GameControl(models.Model):
    """
    Single-row database table to store control information for the competition.
    """

    competition_name = models.CharField(max_length=100, default='My A/D CTF')
    # Start and end times for the whole competition: Make them NULL-able (for the initial state), but not
    # blank-able (have to be set upon editing); "services_public" is the point at which information about the
    # services is public, but the actual game has not started yet
    services_public = models.DateTimeField(null=True)
    start = models.DateTimeField(null=True)
    end = models.DateTimeField(null=True)
    # Tick duration in seconds
    tick_duration = models.PositiveSmallIntegerField(default=180)
    # Number of ticks a flag is valid for including the one it was generated in
    # See https://github.com/fausecteam/ctf-gameserver/issues/84
    valid_ticks = models.PositiveSmallIntegerField(default=5, help_text=_('Currently unused'))
    current_tick = models.IntegerField(default=-1)
    # Instruct Checker Runners to cancel any running checks
    cancel_checks = models.BooleanField(default=False)
    flag_prefix = models.CharField(max_length=20, default='FLAG_')
    registration_open = models.BooleanField(default=False)
    registration_confirm_text = models.TextField(blank=True)
    min_net_number = models.PositiveIntegerField(null=True, blank=True)
    max_net_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Game control'

    @classmethod
    def get_instance(cls):
        try:
            return cls.objects.get()
        except cls.DoesNotExist:
            game_control = GameControl()
            game_control.save()
            return game_control

    def clean(self):
        """
        Ensures that only one instance of the class gets created.
        Inspired by https://stackoverflow.com/a/6436008.
        """
        cls = self.__class__

        if cls.objects.count() > 0 and self.id != cls.objects.get().id:
            # pylint: disable=no-member
            raise ValidationError(_('Only a single instance of {cls} can be created')
                                  .format(cls=cls.__name__))

    def are_services_public(self):
        """
        Indicates whether information about the services is public yet.
        """
        if self.services_public is None:
            return False

        return self.services_public <= timezone.now()

    def competition_started(self):
        """
        Indicates whether the competition has already begun (i.e. running or over).
        """
        if self.start is None or self.end is None:
            return False

        return self.start <= timezone.now()

    def competition_over(self):
        """
        Indicates whether the competition is already over.
        """
        if self.start is None or self.end is None:
            return False

        return self.end < timezone.now()
