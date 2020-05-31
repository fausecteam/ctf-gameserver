#!/usr/bin/env python3

from ctf_gameserver import checkerlib


class TestChecker(checkerlib.BaseChecker):

    def place_flag(self, tick):
        self._tick = tick    # pylint: disable=attribute-defined-outside-init

        if self.team != 2 and self.team != 3:
            raise Exception('Invalid team {}'.format(self.team))

        checkerlib.get_flag(tick)

        if self.team == 2 and tick == 0:
            return checkerlib.CheckResult.FAULTY
        else:
            return checkerlib.CheckResult.OK

    def check_service(self):
        if self.team == 2 and self._tick == 1:
            return checkerlib.CheckResult.TIMEOUT
        else:
            return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        checkerlib.get_flag(tick)

        if self.team == 2 and self._tick == 2:
            if tick == 0:
                return checkerlib.CheckResult.FLAG_NOT_FOUND
            else:
                return checkerlib.CheckResult.OK
        elif self.team == 3 and self._tick == 1:
            return checkerlib.CheckResult.FAULTY
        else:
            return checkerlib.CheckResult.OK


if __name__ == '__main__':

    checkerlib.run_check(TestChecker)
