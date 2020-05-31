#!/usr/bin/env python3

import os

from ctf_gameserver import checkerlib


class TestChecker(checkerlib.BaseChecker):

    def place_flag(self, tick):
        checkerlib.get_flag(tick)

        # Try to send a signal to our parent, this should not be possible when running as another user
        parent_pid = os.getppid()
        try:
            os.kill(parent_pid, 0)
        except PermissionError:
            return checkerlib.CheckResult.OK

        raise Exception('Should not be able to kill the parent')

    def check_service(self):
        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        checkerlib.get_flag(tick)
        return checkerlib.CheckResult.OK


if __name__ == '__main__':

    checkerlib.run_check(TestChecker)
