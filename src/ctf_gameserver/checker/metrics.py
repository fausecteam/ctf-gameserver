import logging
import queue
from wsgiref import simple_server

import prometheus_client

from ctf_gameserver.lib.checkresult import CheckResult
from ctf_gameserver.lib.metrics import SilentHandler


def inc(metrics_queue, name, value=1, labels=None):

    metrics_queue.put(MetricsMessage(name, 'inc', value, labels))


def dec(metrics_queue, name, value=1, labels=None):

    metrics_queue.put(MetricsMessage(name, 'dec', value, labels))


def set(metrics_queue, name, value, labels=None):    # pylint: disable=redefined-builtin

    metrics_queue.put(MetricsMessage(name, 'set', value, labels))


def observe(metrics_queue, name, value, labels=None):

    metrics_queue.put(MetricsMessage(name, 'observe', value, labels))


class MetricsMessage:
    """
    Message to put into run_collector()'s queue for recording metric changes.
    """

    def __init__(self, name, instruction, value, labels=None):
        self.name = name
        self.instruction = instruction
        self.value = value

        if labels is None:
            self.labels = {}
        else:
            self.labels = labels


class HTTPGenMessage:
    """
    Message to put into run_collector()'s queue for receiving a text representation of its metrics (for HTTP
    export) through its pipe.
    """


def checker_metrics_factory(registry, service):

    metrics = {}
    metric_prefix = 'ctf_checkermaster_'

    counters = [
        ('started_tasks', 'Number of started Checker Script instances'),
        ('timeout_tasks', 'Number of Checker Script instances forcibly terminated at end of tick'),
        ('killed_tasks', 'Number of Checker Script instances forcibly terminated because of misbehavior')
    ]
    for name, doc in counters:
        metrics[name] = prometheus_client.Counter(metric_prefix+name, doc, ['service'], registry=registry)
        # Pre-declare possible label value
        metrics[name].labels(service)

    metrics['completed_tasks'] = prometheus_client.Counter(
        # Timeouts do not count as successfully completed checks
        metric_prefix+'completed_tasks', 'Number of successfully completed checks', ['result', 'service'],
        registry=registry
    )
    for result in CheckResult:
        # Pre-declare possible label value combinations
        metrics['completed_tasks'].labels(result.name, service)

    gauges = [
        ('start_timestamp', '(Unix) timestamp when the process was started'),
        ('interval_length_seconds', 'Configured launch interval length'),
        ('last_launch_timestamp', '(Unix) timestamp when tasks were launched the last time'),
        ('tasks_per_launch_count', 'Number of checks to start in one launch interval'),
        ('max_task_duration_seconds', 'Currently estimated maximum runtime of one check')
    ]
    for name, doc in gauges:
        metrics[name] = prometheus_client.Gauge(metric_prefix+name, doc, ['service'], registry=registry)
        metrics[name].labels(service)

    histograms = [
        ('task_launch_delay_seconds', 'Differences between supposed and actual task launch times',
         (0.01, 0.03, 0.05, 0.1, 0.3, 0.5, 1, 3, 5, 10, 30, 60, float('inf'))),
        ('script_duration_seconds', 'Observed runtimes of Checker Scripts',
         (1, 3, 5, 8, 10, 20, 30, 45, 60, 90, 120, 150, 180, 240, 300, float('inf')))
    ]
    for name, doc, buckets in histograms:
        metrics[name] = prometheus_client.Histogram(metric_prefix+name, doc, ['service'], buckets=buckets,
                                                    registry=registry)
        metrics[name].labels(service)

    return metrics


def run_collector(service, metrics_factory, in_queue, pipe_to_server):
    """
    Manages Prometheus metrics. Receives changes to the metrics through a queue and emits their text
    representation (for HTTP export) over a pipe. Designed to be run as "target" in a multiprocessing.Process
    in conjunction with run_http_server().

    Args:
        service: Slug of this checker instance's service.
        metrics_factory: Callable returning a dict of the metrics, mapping from name to Metric object.
        in_queue: Queue over which MetricsMessages and HTTPGenMessages are received.
        pipe_to_server: Pipe to which text representations of the metrics are sent in response to
                        HTTPGenMessages.
    """

    registry = prometheus_client.CollectorRegistry()
    metrics = metrics_factory(registry, service)

    def handle_metrics_message(msg):
        try:
            metric = metrics[msg.name]
        except KeyError:
            logging.error('Recevied message for unknown metric "%s", ignoring', msg.name)
            return

        # Apparently, there is no nicer way to access the label names
        if 'service' in metric._labelnames:    # pylint: disable=protected-access
            msg.labels['service'] = service
        if len(msg.labels) > 0:
            try:
                metric = metric.labels(**(msg.labels))
            except ValueError:
                logging.error('Invalid labels specified for metric "%s", ignoring', msg.name)
                return

        try:
            bound_method = getattr(metric, msg.instruction)
        except AttributeError:
            logging.error('Cannot use instruction "%s" on metric "%s", ignoring', msg.instruction, msg.name)
            return
        try:
            bound_method(msg.value)
        except:    # noqa, pylint: disable=bare-except
            logging.exception('Could not update metric "%s":', msg.name)

    def send_metrics_text():
        metrics_text = prometheus_client.generate_latest(registry)
        pipe_to_server.send(metrics_text)

    while True:
        message = in_queue.get(True)
        if isinstance(message, MetricsMessage):
            handle_metrics_message(message)
        elif isinstance(message, HTTPGenMessage):
            send_metrics_text()
        else:
            logging.error('Received unknown message on collector queue')


def run_http_server(host, port, family, queue_to_collector, pipe_from_collector):
    """
    Runs a server exposing Prometheus metrics via HTTP. The metrics are requested through a HTTPGenMessage
    and received over the pipe. Designed to be run as "target" in a multiprocessing.Process in conjunction
    with run_collector().

    Args:
        host: Host to run the HTTP server on.
        port: Port to run the HTTP server on.
        family: Address family to run the HTTP server with.
        queue_to_collector: Queue to which HTTPGenMessages are sent.
        pipe_from_collector: Pipe from which text representations of the metrics are received.
    """

    def app(_, start_response):
        queue_to_collector.put(HTTPGenMessage())
        output = pipe_from_collector.recv()

        status = '200 OK'
        headers = [
            ('Content-Type', prometheus_client.CONTENT_TYPE_LATEST)
        ]
        start_response(status, headers)
        return [output]

    class FamilyServer(simple_server.WSGIServer):
        address_family = family

    http_server = simple_server.make_server(host, port, app, server_class=FamilyServer,
                                            handler_class=SilentHandler)
    http_server.serve_forever()


class DummyQueue(queue.Queue):
    """
    Queue that discards all elements put into it.
    """

    def put(self, item, block=True, timeout=None):
        pass
