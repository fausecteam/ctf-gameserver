from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class Team(models.Model):
    """
    Database representation of a team participating in the competition.
    This enhances the user model, where the team name, password, formal email address etc. are stored. It is
    particularly attuned to django.contrib.auth.models.User, but should work with other user models as well.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True)

    informal_email = models.EmailField(_('Informal email address'))
    image = models.FileField(null=True, blank=True)
    # TODO: Change this to a selection field
    country = models.CharField(max_length=100)

    class Meta:
        ordering = ['user__username']

    class ActiveObjectsManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(user__is_active=True)

    # QuerySet that only returns Teams whose associated user object is not marked as inactive
    active_objects = ActiveObjectsManager()

    def __str__(self):
        return self.user.username
