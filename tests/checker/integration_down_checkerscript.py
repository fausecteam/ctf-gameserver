#!/usr/bin/env python3

import errno

from ctf_gameserver import checkerlib


class TestChecker(checkerlib.BaseChecker):

    def place_flag(self, tick):
        checkerlib.get_flag(tick)
        raise OSError(errno.ETIMEDOUT, 'A timeout occurred')

    def check_service(self):
        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        checkerlib.get_flag(tick)
        return checkerlib.CheckResult.OK


if __name__ == '__main__':

    checkerlib.run_check(TestChecker)
