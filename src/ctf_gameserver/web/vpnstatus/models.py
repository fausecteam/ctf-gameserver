from django.db import models

from ctf_gameserver.web.registration.models import Team


class VPNStatusCheck(models.Model):
    """
    Database representation of one VPN status check, consisting of the different check results (VPN, ping,
    etc.) for one team at one point in time.
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    wireguard_handshake_time = models.DateTimeField(null=True, blank=True)
    gateway_ping_rtt_ms = models.PositiveIntegerField(null=True, blank=True)
    demo_ping_rtt_ms = models.PositiveIntegerField(null=True, blank=True)
    vulnbox_ping_rtt_ms = models.PositiveIntegerField(null=True, blank=True)
    demo_service_ok = models.BooleanField()
    vulnbox_service_ok = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'VPN status check'

    def __str__(self):
        return 'VPN status check {:d}'.format(self.id)
