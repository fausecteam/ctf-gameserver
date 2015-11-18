#!/usr/bin/python3

from checker import BaseChecker, OK

class DummyChecker(BaseChecker):
    def place_flag(self):
        return OK

    def check_flag(self, tick):
        return OK

    def check_service(self):
        return OK
