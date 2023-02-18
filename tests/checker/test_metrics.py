# pylint: disable=missing-timeout

import multiprocessing
import socket
import time
from unittest import TestCase

import prometheus_client
import requests

from ctf_gameserver.checker import metrics


# Support terminate() on multiprocessing.Process with pytest-cov, see
# https://pytest-cov.readthedocs.io/en/v2.10.0/subprocess-support.html#if-you-use-multiprocessing-process
try:
    from pytest_cov.embed import cleanup_on_sigterm
except ImportError:
    pass
else:
    cleanup_on_sigterm()


class MetricsTest(TestCase):

    metrics_url = 'http://127.0.0.1:9002/metrics'

    def setUp(self):
        def metrics_factory(registry, service):
            service_gauge = prometheus_client.Gauge('service_gauge', 'Gauge with "service" label',
                                                    ['service'], registry=registry)
            service_gauge.labels(service)

            return {
                'plain_gauge': prometheus_client.Gauge('plain_gauge', 'Simple gauge', registry=registry),
                'instance_gauge': prometheus_client.Gauge('instance_gauge', 'Gauge with custom label',
                                                          ['instance'], registry=registry),
                'service_gauge': service_gauge,
                'counter': prometheus_client.Counter('counter', 'Simple counter', registry=registry),
                'summary': prometheus_client.Summary('summary', 'Simple summary', registry=registry),
                'histogram': prometheus_client.Histogram('histogram', 'Histogram with custom and "service" '
                                                         'labels', ['instance', 'service'],
                                                         registry=registry)
            }

        self.queue = multiprocessing.Queue()
        recv, send = multiprocessing.Pipe()

        self.collector_process = multiprocessing.Process(target=metrics.run_collector,
                                                         args=('test', metrics_factory, self.queue, send))
        self.collector_process.start()
        self.http_server_process = multiprocessing.Process(target=metrics.run_http_server,
                                                           args=('127.0.0.1', 9002, socket.AF_INET,
                                                                 self.queue, recv))
        self.http_server_process.start()

        # Wait for server start-up to avoid race conditions
        retries = 0
        while True:
            if retries >= 100:
                raise Exception('Metrics server did not start up')
            try:
                requests.get(self.metrics_url)
            except requests.ConnectionError:
                retries += 1
                time.sleep(0.1)
            else:
                break

    def tearDown(self):
        self.http_server_process.terminate()
        self.collector_process.terminate()
        self.http_server_process.join()
        self.collector_process.join()

    def test_gauge(self):
        metrics.set(self.queue, 'plain_gauge', 42)
        # "If multiple processes are enqueuing objects, it is possible for the objects to be received at the
        # other end out-of-order"
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('plain_gauge 42.0', resp.text)

        metrics.inc(self.queue, 'plain_gauge')
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('plain_gauge 43.0', resp.text)

        metrics.dec(self.queue, 'plain_gauge', 1.5)
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('plain_gauge 41.5', resp.text)

    def test_custom_label(self):
        metrics.set(self.queue, 'instance_gauge', 42, {'instance': 1})
        metrics.set(self.queue, 'instance_gauge', 13.37, {'instance': 2})

        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('instance_gauge{instance="1"} 42.0', resp.text)
        self.assertIn('instance_gauge{instance="2"} 13.37', resp.text)

    def test_service_label(self):
        metrics.set(self.queue, 'service_gauge', 23)

        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('service_gauge{service="test"} 23.0', resp.text)

    def test_counter(self):
        metrics.inc(self.queue, 'counter')
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('counter_total 1.0', resp.text)

        metrics.inc(self.queue, 'counter')
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('counter_total 2.0', resp.text)

        metrics.inc(self.queue, 'counter', 0)
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('counter_total 2.0', resp.text)

    def test_multiple(self):
        metrics.set(self.queue, 'plain_gauge', 1337)
        metrics.set(self.queue, 'instance_gauge', 23, {'instance': 1})
        metrics.set(self.queue, 'service_gauge', 42)
        metrics.inc(self.queue, 'counter')

        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('plain_gauge 1337.0', resp.text)
        self.assertIn('instance_gauge{instance="1"} 23.0', resp.text)
        self.assertIn('service_gauge{service="test"} 42.0', resp.text)
        self.assertIn('counter_total 1.0', resp.text)

    def test_summary(self):
        metrics.observe(self.queue, 'summary', 10)
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('summary_count 1.0', resp.text)
        self.assertIn('summary_sum 10.0', resp.text)

        metrics.observe(self.queue, 'summary', 20)
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('summary_count 2.0', resp.text)
        self.assertIn('summary_sum 30.0', resp.text)

    def test_histogram(self):
        metrics.observe(self.queue, 'histogram', 0.02, {'instance': 3})
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('histogram_bucket{instance="3",le="0.01",service="test"} 0.0', resp.text)
        self.assertIn('histogram_bucket{instance="3",le="0.025",service="test"} 1.0', resp.text)
        self.assertIn('histogram_bucket{instance="3",le="10.0",service="test"} 1.0', resp.text)

        metrics.observe(self.queue, 'histogram', 0.5, {'instance': 3})
        time.sleep(0.1)
        resp = requests.get(self.metrics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('histogram_bucket{instance="3",le="0.25",service="test"} 1.0', resp.text)
        self.assertIn('histogram_bucket{instance="3",le="0.5",service="test"} 2.0', resp.text)
        self.assertIn('histogram_bucket{instance="3",le="10.0",service="test"} 2.0', resp.text)
