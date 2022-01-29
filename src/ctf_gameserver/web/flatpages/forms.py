from django import forms
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from . import models


class CategoryAdminForm(forms.ModelForm):
    """
    Form for Category objects, designed primarily to be used in CategoryAdmin.
    """

    class Meta:
        model = models.Category
        exclude = ('slug',)

    def save(self, commit=True):
        category = super().save(commit=False)
        slug = slugify(category.title)

        raw_slug = slug
        counter = 1

        # Titles are just as unique as slugs, but slugify() is not bijective
        while models.Category.objects.filter(slug=slug).exclude(pk=category.pk).exists():
            slug = '{}-{:d}'.format(raw_slug, counter)
            counter += 1

        category.slug = slug

        if commit:
            category.save()

        return category


class FlatpageAdminForm(forms.ModelForm):
    """
    Form for Flatpage objects, designed primarily to be used in FlatpageAdmin.
    """

    class Meta:
        model = models.Flatpage
        exclude = ('slug',)
        help_texts = {
            'title': _('Leave empty for the home page.'),
            # pylint: disable=no-member
            'content': mark_safe(_('{markdown} or raw HTML are allowed.').format(
                markdown='<a href="https://daringfireball.net/projects/markdown/syntax" target="_blank">'
                         'Markdown</a>'
            ))
        }

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data['category'] is not None and not cleaned_data['title']:
            raise forms.ValidationError(_('The home page must not have a category, every other page has to '
                                          'have a title'))

        return cleaned_data

    def save(self, commit=True):
        page = super().save(commit=False)
        slug = slugify(page.title)

        raw_slug = slug
        counter = 1

        while models.Flatpage.objects.filter(category=page.category, slug=slug).exclude(pk=page.pk).exists():
            slug = '{}-{:d}'.format(raw_slug, counter)
            counter += 1

        page.slug = slug

        if commit:
            page.save()

        return page
