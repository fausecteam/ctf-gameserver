#!/usr/bin/python3

from .abstract import AbstractChecker

import base64
import sys
import codecs

class ContestChecker(AbstractChecker):
    def __init__(self, tick, team, service, ip):
        AbstractChecker.__init__(self, tick, team, service, ip)

    def _rpc(self, function, *args):
        sys.stdout.write("%s %s\n" % (function, " ".join(args)))
        sys.stdout.flush()
        return sys.stdin.readline().strip()

    def get_flag(self, tick, payload=None):
        if payload is None:
            return self._rpc("FLAG", str(tick))
        else:
            payload = codecs.encode(payload, 'hex').decode('latin-1')
            return self._rpc("FLAG", str(tick), payload)

    def store_blob(self, ident, blob):
        data = base64.b64encode(blob)
        return self._rpc("STORE", ident, data.decode('latin-1'))

    def retrieve_blob(self, ident):
        data = self._rpc("RETRIEVE", ident)
        return base64.b64decode(data)
