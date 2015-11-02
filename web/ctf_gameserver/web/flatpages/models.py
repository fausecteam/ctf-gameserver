from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
import mistune

_markdown = mistune.Markdown()


class Flatpage(models.Model):
    """
    Data model for pages with static content ("About" pages, rules etc.).
    This custom implementation is quite similar to Django's flat pages, but supports Markdown and
    hierarchical organization of the pages. As django.contrib.flatpages adds a dependency to the sites
    framework, it turned out easier to re-implement the base functionality instead of extending it.
    """

    # Title may be blank for the home page
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True)
    ordering = models.PositiveSmallIntegerField(default=10)
    slug = models.CharField(max_length=100)

    class Meta:
        verbose_name = _('flatpage')
        # Slug is usually (automatically) generated from the title, add constraints for both because of
        # https://code.djangoproject.com/ticket/13091
        unique_together = (
            ('parent', 'title'),
            ('parent', 'slug')
        )
        # Need to specify the parent's exact attribute because of https://code.djangoproject.com/ticket/7101
        ordering = ('parent__title', 'ordering', 'title')

    def __str__(self):
        return self.title

    def clean(self):
        """
        Performs additional validation to ensure the unique constraint for parent and title also applies
        when parent is NULL. Django's constraint validation skips this case, and the actual constraint's
        behavior is database-specific.
        """
        if self.parent is None:
            if self._default_manager.filter(parent=self.parent, title=self.title).exists():
                raise self.unique_error_message(self.__class__, ('parent', 'title'))

    def get_absolute_url(self):
        path_parts = [self.slug]
        current_parent = self.parent

        while current_parent is not None:
            path_parts.append(current_parent.slug)
            current_parent = current_parent.parent

        path = '/'.join(reversed(path_parts))

        # Add a trailing slash, except for the home page
        if path:
            path += '/'

        return reverse('flatpage', kwargs={'path': path})

    def render_content(self):
        """
        Returns the page's content as rendered HTML.
        """
        return mark_safe(_markdown(self.content))
