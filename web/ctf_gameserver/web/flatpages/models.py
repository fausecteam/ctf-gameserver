from django.core.urlresolvers import reverse
from django.db import models
from django.utils.safestring import mark_safe
from markdown import markdown


class Category(models.Model):
    """
    (Menu) hierarchy level for Flatpages.
    """

    title = models.CharField(max_length=100)
    ordering = models.PositiveSmallIntegerField(default=10)
    slug = models.CharField(max_length=100)

    class Meta:
        ordering = ('ordering', 'title')

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

    class ObjectsWithoutCategoryManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(category=None).exclude(title='')

    objects = models.Manager()
    # QuerySet that only returns Flatpages without a category, but not the home page
    objects_without_category = ObjectsWithoutCategoryManager()

    def __str__(self):
        return self.title

    def clean(self):
        """
        Performs additional validation to ensure the unique constraint for category and title also applies
        when category is NULL. Django's constraint validation skips this case, and the actual constraint's
        behavior is database-specific.
        """
        if self.category is None and self._default_manager.filter(
            category = self.category,
            title = self.title
        ).exclude(pk=self.pk).exists():
            raise self.unique_error_message(self.__class__, ('category', 'title'))

    def get_absolute_url(self):
        if self.is_home_page():
            return reverse('home_flatpage')
        elif self.category is None:
            return reverse('no_category_flatpage', kwargs={'slug': self.slug})
        else:
            return reverse('category_flatpage', kwargs={'category': self.category.slug, 'slug': self.slug})

    @property
    def siblings(self):
        """
        Access siblings of this page, i.e. pages in the same category. For convenience, this includes this
        page itself.
        """
        return self._default_manager.filter(category=self.category)

    def has_siblings(self):
        """
        Indicates whether the page has any siblings. This does not include the page itself, so it is False
        when `len(self.siblings) == 1`.
        """
        return self.siblings.exclude(pk=self.pk).exists()

    def is_home_page(self):
        """
        Indicates whether the page is the home page.
        """
        return not self.title and self.category is None

    def render_content(self):
        """
        Returns the page's content as rendered HTML.
        """
        return mark_safe(markdown(self.content))
