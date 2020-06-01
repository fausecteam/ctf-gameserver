import random
import time
import unittest
from unittest.mock import patch

from ctf_gameserver.lib import flag


class FlagTestCase(unittest.TestCase):

    def test_deterministic(self):
        tstamp = time.time()
        flag1 = flag.generate(12, 13, b'secret', timestamp=tstamp)
        flag2 = flag.generate(12, 13, b'secret', timestamp=tstamp)
        self.assertEqual(flag1, flag2)

    def test_valid_flag(self):
        payload = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        timestamp = int(time.time() + 12)
        team = 12
        service = 13
        flag1 = flag.generate(team, service, b'secret', payload=payload, timestamp=timestamp)
        team_, service_, payload_, timestamp_ = flag.verify(flag1, b'secret')
        self.assertEqual(team, team_)
        self.assertEqual(service, service_)
        self.assertEqual(payload, payload_)
        self.assertEqual(timestamp, timestamp_)

    def test_old_flag(self):
        timestamp = int(time.time() - 12)
        test_flag = flag.generate(12, 13, b'secret', timestamp=timestamp)
        with self.assertRaises(flag.FlagExpired):
            flag.verify(test_flag, b'secret')

    def test_invalid_format(self):
        with self.assertRaises(flag.InvalidFlagFormat):
            flag.verify('ABC123', b'secret')

    def test_invalid_mac(self):
        test_flag = flag.generate(12, 13, b'secret')

        # Replace last character of the flag with a differnt one
        chars = set("0123456789")
        try:
            chars.remove(test_flag[-1])
        except KeyError:
            pass
        wrong_flag = test_flag[:-1] + random.choice(list(chars))

        with self.assertRaises(flag.InvalidFlagMAC):
            flag.verify(wrong_flag, b'secret')

    @patch('time.time')
    def test_known_flags(self, time_mock):
        expected_flags = [
            'FAUST_XtS7wBcN2922TQAAAADSnUcLXKXGH30q',
            'FAUST_XuP+ABcN9bnslAAAAADDwPeBY7wmFYjw',
            'FAUST_XtS7wBcNcGF5bG9hZDFM5ROP4sHaLcsR',
            'FAUST_XuP+ABcNcGF5bG9hZDFr00COGTziHA3x',
            'FAUST_XtS7wBcN2922TQAAAAACjQSDjDb3XsfX',
            'FAUST_XuP+ABcN9bnslAAAAABSfn7ZZv9MUdOa',
            'FAUST_XtS7wBcNcGF5bG9hZDHIVxdVlk+e4eqH',
            'FAUST_XuP+ABcNcGF5bG9hZDEW9JVaF+SpvGjt',
            'FAUST_XtS7wBcl7mgetwAAAAAUchUPA70Po5S6',
            'FAUST_XuP+ABclwAxEbgAAAACIaVSdLpnP0Y4H',
            'FAUST_XtS7wBclcGF5bG9hZDF6FqMljkT5Od/X',
            'FAUST_XuP+ABclcGF5bG9hZDEFllCIW/o9Bhcr',
            'FAUST_XtS7wBcl7mgetwAAAAADCfGNhj4PvyvG',
            'FAUST_XuP+ABclwAxEbgAAAABH1rm5RTqWBU5O',
            'FAUST_XtS7wBclcGF5bG9hZDEZ37yBKXTHZTsR',
            'FAUST_XuP+ABclcGF5bG9hZDF1YXgV/BxZO6JN',
            'FAUST_XtS7wCoNsTX+8wAAAADtem2URl6q86dl',
            'FAUST_XuP+ACoNn1GkKgAAAACHIDvkaJiLkiAp',
            'FAUST_XtS7wCoNcGF5bG9hZDFPZ+fJIVMBeKsO',
            'FAUST_XuP+ACoNcGF5bG9hZDHb6/3QxWC7EFm1',
            'FAUST_XtS7wCoNsTX+8wAAAACgWog43ewOo5/J',
            'FAUST_XuP+ACoNn1GkKgAAAABQE9kx+uxZVGvG',
            'FAUST_XtS7wCoNcGF5bG9hZDEB2vTDF3rTpJUc',
            'FAUST_XuP+ACoNcGF5bG9hZDHwBM9FJWNIP0c4',
            'FAUST_XtS7wColhIBWCQAAAADWgZp9BbfRUUBK',
            'FAUST_XuP+AColquQM0AAAAADA3XmMDD4y4Lrp',
            'FAUST_XtS7wColcGF5bG9hZDGeTfptV0+8OU3i',
            'FAUST_XuP+AColcGF5bG9hZDE6tMCOD9jehXJ3',
            'FAUST_XtS7wColhIBWCQAAAAA1vuUOcNeT2Bf4',
            'FAUST_XuP+AColquQM0AAAAAC9ypT0SGIHdnrs',
            'FAUST_XtS7wColcGF5bG9hZDGsPqS59iOdknql',
            'FAUST_XuP+AColcGF5bG9hZDEkKGiIraClaKLo'
        ]
        actual_flags = []

        for team in (23, 42):
            for service in (13, 37):
                for secret in (b'secret1', b'secret2'):
                    for payload in (None, b'payload1'):
                        for timestamp in (1591000000, 1592000000):
                            actual_flag = flag.generate(team, service, secret, payload, timestamp)
                            actual_flags.append(actual_flag)

                            time_mock.return_value = timestamp - 5
                            actual_team, actual_service, actual_payload, actual_timestamp = \
                                flag.verify(actual_flag, secret)
                            self.assertEqual(actual_team, team)
                            self.assertEqual(actual_service, service)
                            if payload is not None:
                                self.assertEqual(actual_payload, payload)
                            self.assertEqual(actual_timestamp, timestamp)

        self.assertEqual(actual_flags, expected_flags)
