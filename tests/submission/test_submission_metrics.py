# pylint: disable=missing-timeout

import socket
import time
from unittest import TestCase

import prometheus_client
import requests

from ctf_gameserver.lib.metrics import start_metrics_server
from ctf_gameserver.submission.submission import make_metrics


class MetricsTest(TestCase):

    metrics_url = 'http://127.0.0.1:9005/metrics'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Use a dedicated registry to avoid interference with the global default one
        # The metrics server runs in a daemon thread without a clean shutdown, so it is started only once for
        # the whole test case
        cls.registry = prometheus_client.CollectorRegistry()
        cls.metrics = make_metrics(cls.registry)
        start_metrics_server('127.0.0.1', 9005, socket.AF_INET, cls.registry)

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
        self.metrics['flags_ok'].labels(42).inc()

        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('ctf_submission_flags_ok_total{team_net_no="42"} 1.0', resp.text)
