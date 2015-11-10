from django.shortcuts import redirect
from django.contrib import admin

from ctf_gameserver.web.admin import admin_site
from . import models


admin_site.register(models.Flag)
admin_site.register(models.Service)
admin_site.register(models.Capture)
admin_site.register(models.StatusCheck)


@admin.register(models.GameControl, site=admin_site)
class GameControlAdmin(admin.ModelAdmin):
    """
    Admin object for the single GameControl object. Since at most one instance exists at any time, 'Add' and
    'Delete links' are hidden and a request for the object list will directly redirect to the instance.
    """

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, instance=None):
        return False

    def changelist_view(self, extra_context=None):
        game_control = models.GameControl.objects.get()
        return redirect('admin:scoring_gamecontrol_change', game_control.pk, permanent=True)
