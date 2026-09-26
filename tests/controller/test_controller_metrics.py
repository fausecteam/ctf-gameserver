# pylint: disable=missing-timeout

import socket
import time

import prometheus_client
import requests

from ctf_gameserver.controller import controller
from ctf_gameserver.lib.metrics import start_metrics_server
from ctf_gameserver.lib.test_util import DatabaseTestCase


class MetricsTest(DatabaseTestCase):

    fixtures = ['tests/controller/fixtures/metrics.json']

    metrics_url = 'http://127.0.0.1:9001/metrics'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Use a dedicated registry to avoid interference with the global default one
        # The metrics server runs in a daemon thread without a clean shutdown, so it is started only once for
        # the whole test case
        cls.registry = prometheus_client.CollectorRegistry()
        cls.metrics = controller.make_metrics(cls.connection, cls.registry)
        start_metrics_server('127.0.0.1', 9001, socket.AF_INET, cls.registry)

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

    def test_database_metrics(self):
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)

        self.assertIn('ctf_controller_open_tasks_total{service="service1",ticks="cur"} 1.0', resp.text)
        self.assertIn('ctf_controller_open_tasks_total{service="service1",ticks="old"} 0.0', resp.text)
        self.assertIn('ctf_controller_open_tasks_total{service="service2",ticks="cur"} 0.0', resp.text)
        self.assertIn('ctf_controller_open_tasks_total{service="service2",ticks="old"} 1.0', resp.text)
        self.assertIn('ctf_controller_incomplete_tasks_total{service="service1",ticks="cur"} 1.0',
                      resp.text)

        self.assertIn('ctf_controller_exploiting_teams_total{flagstore="0",service="service1"} 0.0',
                      resp.text)
        self.assertIn('ctf_controller_exploiting_teams_total{flagstore="0",service="service2"} 2.0',
                      resp.text)
        self.assertIn('ctf_controller_exploiting_teams_total{flagstore="1",service="service2"} 1.0',
                      resp.text)
        self.assertIn('ctf_controller_is_exploited{flagstore="0",service="service1"} 0.0', resp.text)
        self.assertIn('ctf_controller_is_exploited{flagstore="0",service="service2"} 1.0', resp.text)
        self.assertIn('ctf_controller_is_exploited{flagstore="1",service="service2"} 1.0', resp.text)

    def test_manual_metric(self):
        self.metrics['current_tick'].set(5)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('ctf_controller_current_tick 5.0', resp.text)
