from django.utils.translation import gettext_lazy as _
from django.contrib import admin

from ctf_gameserver.web.admin import admin_site
from . import models, forms


@admin.register(models.Category, site=admin_site)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin object for the flatpage Categories.
    """

    list_display = ('title', 'ordering')
    list_editable = ('ordering',)
    search_fields = ('title',)

    form = forms.CategoryAdminForm


@admin.register(models.Flatpage, site=admin_site)
class FlatpageAdmin(admin.ModelAdmin):
    """
    Admin object for Flatpage objects from the custom flatpages implementation.
    """

    list_display = ('title', 'category', 'ordering')
    list_editable = ('category', 'ordering')
    list_filter = ('category',)
    search_fields = ('title', 'content')

    form = forms.FlatpageAdminForm
    fieldsets = (
        (None, {'fields': ('title', 'content')}),
        (_('Menu hierarchy'), {'fields': ('category', 'ordering')})
    )
    view_on_site = True
