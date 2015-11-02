from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .models import Flatpage


class FlatpageChangelistForm(forms.ModelForm):
    """
    Form which adds custom validation to inline editing of object lists in FlatpageAdmin.
    """

    def clean_parent(self):
        current_parent = self.cleaned_data['parent']

        while current_parent is not None:
            if current_parent == self.instance:
                raise forms.ValidationError(_('A flatpage cannot be its own ancestor'))
            current_parent = current_parent.parent

        return self.cleaned_data['parent']


class FlatpageAdminForm(FlatpageChangelistForm):
    """
    Form for Flatpage objects, designed primarily to be used in FlatpageAdmin.
    This is not a descendant of FlatpageChangelistForm semantically, but requires the same cleaning method.
    """

    class Meta:
        model = Flatpage
        exclude = ('slug',)
        help_texts = {
            'title': _('Leave empty for the home page.'),
            'content': mark_safe(_('{markdown} or raw HTML are allowed.').format(
                markdown='<a href="https://daringfireball.net/projects/markdown/syntax" target="_blank">'
                         'Markdown</a>'
            ))
        }

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data['parent'] is not None and not cleaned_data['title']:
            raise forms.ValidationError(_('The home page must not have a parent, every other page has to '
                                          'have a title'))

        return cleaned_data

    def save(self, commit=True):
        page = super().save(commit=False)
        slug = slugify(page.title)

        raw_slug = slug
        counter = 1

        # Titles are just as unique as slugs, but slugify() is not bijective
        while Flatpage.objects.filter(parent=page.parent, slug=slug).exists():
            slug = '{}-{:d}'.format(raw_slug, counter)
            counter += 1

        page.slug = slug

        if commit:
            page.save()

        return page
