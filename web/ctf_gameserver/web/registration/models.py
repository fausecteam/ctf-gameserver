from os.path import splitext

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


def _gen_image_name(instance, filename):
    """
    Returns the upload path (relative to settings.MEDIA_ROOT) for the specified Team's image.
    """

    extension = splitext(filename)[1]

    # Must "return a Unix-style path (with forward slashes)"
    return 'team-images' + '/' + instance.user.username + extension


class Team(models.Model):
    """
    Database representation of a team participating in the competition.
    This enhances the user model, where the team name, password, formal email address etc. are stored. It is
    particularly attuned to django.contrib.auth.models.User, but should work with other user models as well.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True)

    informal_email = models.EmailField(_('Informal email address'))
    image = models.ImageField(upload_to=_gen_image_name, blank=True)
    affiliation = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)

    class ActiveObjectsManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(user__is_active=True)

    objects = models.Manager()
    # QuerySet that only returns Teams whose associated user object is not marked as inactive
    active_objects = ActiveObjectsManager()

    def __str__(self):
        return self.user.username
