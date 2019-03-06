from ctf_gameserver.checker import BaseChecker, OK, NOTFOUND

import time
import telnetlib
import re
import random
import logging

class Faust2048Checker(BaseChecker):
    def __init__(self, tick, team, service, ip):
        BaseChecker.__init__(self, tick, team, service, ip)
        self._connection = telnetlib.Telnet(ip, 9000, 5)
        self._played = False

    def _moves(self):
        while True:
            yield random.choice([b'a', b's', b'a', b's', b'd'])

    def _fetch_fortune(self):
        self._connection.write(b"*")
        self._connection.write(b'X')
        self._connection.read_until(b'wasd q:')

    def check_service(self):
        if self._played:
            return 0

        counter = 1
        self._fetch_fortune()
        for move in self._moves():
            index, _, data = self._connection.expect([b"wasd q:", b"yn:", b"a q:"], 5)

            if index == 0:
                if random.random() < 0.05:
                    self._fetch_fortune()

                self._connection.write(move)
            elif index == 1:
                self._connection.write(b"y")
                counter = counter + 1
            elif index == 2:
                match = re.search(b'Your Score: ([0-9]+)', data)
                logging.info("Finished playing after %d tries with %d points\n" %
                                 (counter, int(match.group(1))))
                self._played = True
                return 0

    def place_flag(self):
        flag = self.get_flag(self._tick)
        self._connection.read_until(b"Please enter your name:")
        self._connection.write(flag.encode('latin-1'))
        self._connection.write(b'\n')
        return 0

    def check_flag(self, tick):
        self.check_service()

        flag = self.get_flag(tick)

        self._connection.write(b'a')
        self._connection.write(flag.encode('latin-1'))
        self._connection.write(b'\n')
        logging.debug("Waiting for data")
        data = self._connection.read_until(b'a q:')
        if flag.encode('latin-1') in data:
            return OK
        else:
            return NOTFOUND
