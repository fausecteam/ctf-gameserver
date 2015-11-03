from django.core.urlresolvers import reverse
from django.db import models
from django.utils.safestring import mark_safe
import mistune

_markdown = mistune.Markdown()


class Category(models.Model):
    """
    (Menu) hierarchy level for Flatpages.
    """

    title = models.CharField(max_length=100)
    slug = models.CharField(max_length=100)

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return self.title


class Flatpage(models.Model):
    """
    Data model for pages with static content ("About" pages, rules etc.).
    This custom implementation is quite similar to Django's flat pages, but supports Markdown and
    organization of the pages into Categories. As django.contrib.flatpages adds a dependency to the sites
    framework, it turned out easier to re-implement the base functionality instead of extending it.
    """

    # Title may be blank for the home page
    title = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    category = models.ForeignKey(Category, null=True, blank=True)
    ordering = models.PositiveSmallIntegerField(default=10)
    slug = models.CharField(max_length=100)

    class Meta:
        # Slug is usually (automatically) generated from the title, add constraints for both because of
        # https://code.djangoproject.com/ticket/13091
        unique_together = (
            ('category', 'title'),
            ('category', 'slug')
        )
        ordering = ('category', 'ordering', 'title')

    def __str__(self):
        return self.title

    def clean(self):
        """
        Performs additional validation to ensure the unique constraint for category and title also applies
        when category is NULL. Django's constraint validation skips this case, and the actual constraint's
        behavior is database-specific.
        """
        if self.category is None:
            if self._default_manager.filter(category=self.category, title=self.title).exists():
                raise self.unique_error_message(self.__class__, ('category', 'title'))

    def get_absolute_url(self):
        # Missing URL parts cannot be None or "", but have to be omitted from 'kwargs' parameter
        kwargs = {}

        if self.category is not None:
            kwargs['category'] = self.category.slug
        if self.slug:
            kwargs['slug'] = self.slug

        return reverse('flatpage', kwargs=kwargs)

    def render_content(self):
        """
        Returns the page's content as rendered HTML.
        """
        return mark_safe(_markdown(self.content))
