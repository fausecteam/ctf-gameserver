from django.contrib import admin

from ctf_gameserver.web.admin import admin_site
from . import models


@admin.register(models.VPNStatusCheck, site=admin_site)
class VPNStatusCheckAdmin(admin.ModelAdmin):

    list_display = ('team', 'timestamp', 'wireguard_handshake_time')
    list_filter = ('team',)
    search_fields = ('team__user__username', 'team__net_number')
    ordering = ('timestamp', 'team')
