from django.contrib import admin

from ctf_gameserver.web.admin import admin_site
from .models import TeamDownload


@admin.register(TeamDownload, site=admin_site)
class FlagAdmin(admin.ModelAdmin):

    search_fields = ('filename', 'description')
