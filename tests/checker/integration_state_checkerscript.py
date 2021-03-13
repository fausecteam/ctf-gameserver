#!/usr/bin/env python3

from ctf_gameserver import checkerlib


class TestChecker(checkerlib.BaseChecker):

    def place_flag(self, tick):
        if checkerlib.load_state('key2') is not None:
            raise Exception('Got state where there should be none')

        if tick == 0:
            if checkerlib.load_state('key1') is not None:
                raise Exception('Got state where there should be none')

        checkerlib.get_flag(tick)

        if self.team == 92:
            if tick == 0:
                checkerlib.store_state('key1', 'Wir können Zustände speichern 🥳')
            else:
                if checkerlib.load_state('key1') != 'Wir können Zustände speichern 🥳':
                    raise Exception('Did not get stored state back')

            if tick == 0:
                checkerlib.store_state('🔑ser', 'Söze')
                if checkerlib.load_state('🔑ser') != 'Söze':
                    raise Exception('Did not get stored state back')
            elif tick == 1:
                if checkerlib.load_state('🔑ser') != 'Söze':
                    raise Exception('Did not get stored state back')
                checkerlib.store_state('🔑ser', ['Roger', '"Verbal"', 'Kint'])
            elif tick == 2:
                if checkerlib.load_state('🔑ser') != ['Roger', '"Verbal"', 'Kint']:
                    raise Exception('Did not get stored state back')
        elif self.team == 93:
            if tick == 1:
                if checkerlib.load_state('key1') is not None:
                    raise Exception('Got state where there should be none')
                data = [{'number': 42}, {'number': 1337}]
                checkerlib.store_state('key1', data)
                checkerlib.set_flagid('value identifier')
            elif tick >= 2:
                if checkerlib.load_state('key1') != [{'number': 42}, {'number': 1337}]:
                    raise Exception('Did not get stored state back')

        return checkerlib.CheckResult.OK

    def check_service(self):
        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        return checkerlib.CheckResult.OK


if __name__ == '__main__':

    checkerlib.run_check(TestChecker)
