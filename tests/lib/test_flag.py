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
            'FAUST_XtS7wBcN2922TQAAAAACthBlPdC0HSgC',
            'FAUST_XuP+ABcN9bnslAAAAACRTsoPjO73wiQy',
            'FAUST_XtS7wBcNcGF5bG9hZDFzidWbRe8CqHKO',
            'FAUST_XuP+ABcNcGF5bG9hZDEXcb0z+FTYkt7g',
            'FAUST_XtS7wBcN2922TQAAAAAPQwnu+Lv1vEoQ',
            'FAUST_XuP+ABcN9bnslAAAAABEAMWzR+6F1IzW',
            'FAUST_XtS7wBcNcGF5bG9hZDEZHhr0IMZiskEw',
            'FAUST_XuP+ABcNcGF5bG9hZDFfhleiyQiT+IAY',
            'FAUST_XtS7wBcl7mgetwAAAAD0D+BaqQDoRZ2F',
            'FAUST_XuP+ABclwAxEbgAAAABtXgKbdTgdlZUm',
            'FAUST_XtS7wBclcGF5bG9hZDFHyHMaoyx63vGK',
            'FAUST_XuP+ABclcGF5bG9hZDEyE9lnk8G5liqM',
            'FAUST_XtS7wBcl7mgetwAAAADQrSmvvv2m3uST',
            'FAUST_XuP+ABclwAxEbgAAAAAF22CcSG/+hGVf',
            'FAUST_XtS7wBclcGF5bG9hZDGMp8Yctst02V2d',
            'FAUST_XuP+ABclcGF5bG9hZDHpucV2lJBMHu4U',
            'FAUST_XtS7wCoNsTX+8wAAAAAPohnEw4ky8klm',
            'FAUST_XuP+ACoNn1GkKgAAAAAdH/Hs3LQrrr/q',
            'FAUST_XtS7wCoNcGF5bG9hZDE9Y+TSR6RfrGGu',
            'FAUST_XuP+ACoNcGF5bG9hZDEaVm4GfnKZMm3T',
            'FAUST_XtS7wCoNsTX+8wAAAAAWtyh/QTfozNFx',
            'FAUST_XuP+ACoNn1GkKgAAAABopz7Xcrz5d/Vn',
            'FAUST_XtS7wCoNcGF5bG9hZDFpFLiAKBfChdNG',
            'FAUST_XuP+ACoNcGF5bG9hZDFZtEL00AW/kMjU',
            'FAUST_XtS7wColhIBWCQAAAACM5V2KyufbVmxv',
            'FAUST_XuP+AColquQM0AAAAADeb1pXAcsQfhlb',
            'FAUST_XtS7wColcGF5bG9hZDEbfR2BqZDRRSd9',
            'FAUST_XuP+AColcGF5bG9hZDFLZCh60AA1M2+E',
            'FAUST_XtS7wColhIBWCQAAAAD5yR3WZtRVgkez',
            'FAUST_XuP+AColquQM0AAAAABuOLGY/bCANp34',
            'FAUST_XtS7wColcGF5bG9hZDFF0om5eAdj4m6e',
            'FAUST_XuP+AColcGF5bG9hZDGpRlcKhhbvnhgj'
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
