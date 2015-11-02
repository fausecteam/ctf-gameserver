from django.utils.translation import ugettext_lazy as _
from django.contrib import admin

from ctf_gameserver.web.admin import admin_site
from .models import Flatpage
from .forms import FlatpageAdminForm, FlatpageChangelistForm


@admin.register(Flatpage, site=admin_site)
class FlatpageAdmin(admin.ModelAdmin):
    """
    Admin object for the Flatpage objects from the custom flatpages implementation.
    """

    list_display = ('title', 'parent', 'ordering')
    list_editable = ('parent', 'ordering')
    list_filter = ('parent',)
    search_fields = ('title', 'content')

    form = FlatpageAdminForm
    fieldsets = (
        (None, {'fields': ('title', 'content')}),
        (_('Menu hierarchy'), {'fields': ('parent', 'ordering')})
    )
    view_on_site = True

    def get_changelist_form(self, request, **kwargs):
        return FlatpageChangelistForm
