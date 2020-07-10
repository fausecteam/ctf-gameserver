import threading
from wsgiref import simple_server

import prometheus_client


def start_metrics_server(host, port, family, registry=prometheus_client.REGISTRY):
    """
    Custom variant of prometheus_client.start_wsgi_server() with support for specifying the address family to
    listen on.
    """

    class FamilyServer(prometheus_client.exposition.ThreadingWSGIServer):
        address_family = family

    app = prometheus_client.make_wsgi_app(registry)
    http_server = simple_server.make_server(host, port, app, FamilyServer, handler_class=SilentHandler)
    thread = threading.Thread(target=http_server.serve_forever)
    thread.daemon = True
    thread.start()


class SilentHandler(simple_server.WSGIRequestHandler):

    def log_message(self, _, *args):
        """
        Doesn't log anything.
        """
