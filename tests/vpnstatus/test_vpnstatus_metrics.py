# pylint: disable=missing-timeout

import socket
import time
from unittest import TestCase

import prometheus_client
import requests

from ctf_gameserver.lib.metrics import start_metrics_server
from ctf_gameserver.vpnstatus.status import make_metrics


class MetricsTest(TestCase):

    metrics_url = 'http://127.0.0.1:9002/metrics'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Use a dedicated registry to avoid interference with the global default one
        # The metrics server runs in a daemon thread without a clean shutdown, so it is started only once for
        # the whole test case
        cls.registry = prometheus_client.CollectorRegistry()
        cls.metrics = make_metrics(cls.registry)
        start_metrics_server('127.0.0.1', 9002, socket.AF_INET, cls.registry)

        # Wait for server start-up to avoid race conditions
        retries = 0
        while True:
            if retries >= 100:
                raise Exception('Metrics server did not start up')
            try:
                requests.get(cls.metrics_url)
            except requests.ConnectionError:
                retries += 1
                time.sleep(0.1)
            else:
                break

    def test_metric(self):
        self.metrics['ping_milliseconds'].labels('vulnbox').observe(42)

        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('ctf_vpnstatus_ping_milliseconds_bucket{le="10.0",target="vulnbox"} 0.0', resp.text)
        self.assertIn('ctf_vpnstatus_ping_milliseconds_bucket{le="50.0",target="vulnbox"} 1.0', resp.text)
        self.assertIn('ctf_vpnstatus_ping_milliseconds_count{target="vulnbox"} 1.0', resp.text)
