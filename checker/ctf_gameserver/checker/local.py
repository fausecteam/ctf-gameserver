#!/usr/bin/python3

from .abstract import AbstractChecker
from ctf_gameserver.lib import flag

import os
import os.path
import logging
import sys

class LocalChecker(AbstractChecker):
    def __init__(self, tick, team, service, ip):
        AbstractChecker.__init__(self, tick, team, service, ip)
        self._starttime = 0
        self._backend = '/tmp'
        self._secret = b'testtestte'
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler(sys.stderr))

    def store_blob(self, ident, blob):
        filename = os.path.join(self._backend, "%s.blob" % ident)
        try:
            with open(filename, "wb") as handle:
                return handle.write(blob)
        except FileNotFoundError:
            return None

    def retrieve_blob(self, ident):
        filename = os.path.join(self._backend, "%s.blob" % ident)
        try:
            with open(filename, "rb") as handle:
                return handle.read()
        except FileNotFoundError:
            return None

    def get_flag(self, tick, payload=None):
        generatedflag = flag.generate(self._team, self._service, self._secret, payload,
                                      self._starttime + self._tickduration * tick)
        return generatedflag

    def set_backend(self, backend):
        self._backend = backend

    def set_starttime(self, starttime):
        self._starttime = starttime

    def set_secret(self, secret):
        self._secret = secret
