#!/usr/bin/env python3

from ctf_gameserver import checkerlib


class TestChecker(checkerlib.BaseChecker):

    def place_flag(self, tick):
        if self.team != 92:
            raise Exception('Team {} != 92'.format(self.team))
        if self.ip != '0.0.92.1':
            raise Exception('IP {} != 0.0.92.1'.format(self.ip))
        if tick != 0:
            raise Exception('Tick {} != 0'.format(tick))

        checkerlib.get_flag(tick)
        checkerlib.set_flagid('value identifier')
        return checkerlib.CheckResult.OK

    def check_service(self):
        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        if tick != 0:
            raise Exception('Tick {} != 0'.format(tick))

        checkerlib.get_flag(tick)
        return checkerlib.CheckResult.OK


if __name__ == '__main__':

    checkerlib.run_check(TestChecker)
