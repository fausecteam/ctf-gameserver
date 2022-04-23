import datetime
import random
import unittest
from unittest.mock import patch

from ctf_gameserver.lib import flag


class FlagTestCase(unittest.TestCase):

    def test_deterministic(self):
        now = self._now()
        flag1 = flag.generate(now, 12, 13, b'secret')
        flag2 = flag.generate(now, 12, 13, b'secret')
        self.assertEqual(flag1, flag2)

    def test_valid_flag(self):
        expiration = self._now() + datetime.timedelta(seconds=12)
        flag_id = 12
        team = 13
        test_flag = flag.generate(expiration, flag_id, team, b'secret')
        flag_id_, team_ = flag.verify(test_flag, b'secret')
        self.assertEqual(flag_id, flag_id_)
        self.assertEqual(team, team_)

    def test_old_flag(self):
        expiration = self._now() - datetime.timedelta(seconds=12)
        test_flag = flag.generate(expiration, 12, 13, b'secret', 'FLAGPREFIX-')
        with self.assertRaises(flag.FlagExpired):
            flag.verify(test_flag, b'secret', 'FLAGPREFIX-')

    def test_invalid_format(self):
        with self.assertRaises(flag.InvalidFlagFormat):
            flag.verify('ABC123', b'secret')

    def test_invalid_mac(self):
        test_flag = flag.generate(self._now(), 12, 13, b'secret')

        # Replace last character of the flag with a differnt one
        chars = set("0123456789")
        try:
            chars.remove(test_flag[-1])
        except KeyError:
            pass
        wrong_flag = test_flag[:-1] + random.choice(list(chars))

        with self.assertRaises(flag.InvalidFlagMAC):
            flag.verify(wrong_flag, b'secret')

    @patch('ctf_gameserver.lib.flag._now')
    def test_known_flags(self, now_mock):
        expected_flags = [
            'FAUST_Q1RGLRmVnOVTRVJBRV9tRpcBKDNOCUPW',
            'FAUST_Q1RGLRml7uVTRVJBRV9IP7yOZriI07tT',
            'FAUST_Q1RGLRmVnOVTRVJBRV/EFBYyQ5hGkkhc',
            'FAUST_Q1RGLRml7uVTRVJBRV9+4LvDGpI37WnR',
            'FAUST_Q1RGLRmVnOVTRVJBRXe71HlVK0TqWwjD',
            'FAUST_Q1RGLRml7uVTRVJBRXdsFhEI3jhxey9I',
            'FAUST_Q1RGLRmVnOVTRVJBRXfGLg3ip26nfSaS',
            'FAUST_Q1RGLRml7uVTRVJBRXcQmzzAV65TUUFp',
            'FAUST_Q1RGLRmVnOVTRVJ8RV/j9Ys/9UjHdsfL',
            'FAUST_Q1RGLRml7uVTRVJ8RV/QpLXRXAao2VOL',
            'FAUST_Q1RGLRmVnOVTRVJ8RV9MXCvXvUVKmW6+',
            'FAUST_Q1RGLRml7uVTRVJ8RV9JoxKWWPdJ1BE0',
            'FAUST_Q1RGLRmVnOVTRVJ8RXfMkW+dK2FfyJlQ',
            'FAUST_Q1RGLRml7uVTRVJ8RXdxXbELYwjVp8Ku',
            'FAUST_Q1RGLRmVnOVTRVJ8RXePbyjg1uvCeQcH',
            'FAUST_Q1RGLRml7uVTRVJ8RXf/lT8Q1kehBFw9'
        ]
        actual_flags = []

        for flag_id in (23, 42):
            for team in (13, 37):
                for secret in (b'secret1', b'secret2'):
                    timestamp1 = datetime.datetime(2020, 6, 1, 10, 0, tzinfo=datetime.timezone.utc)
                    timestamp2 = datetime.datetime(2020, 6, 13, 10, 0, tzinfo=datetime.timezone.utc)
                    for timestamp in (timestamp1, timestamp2):
                        actual_flag = flag.generate(timestamp, flag_id, team, secret, 'FAUST_')
                        actual_flags.append(actual_flag)

                        now_mock.return_value = timestamp - datetime.timedelta(seconds=5)
                        actual_flag_id, actual_team = flag.verify(actual_flag, secret, 'FAUST_')
                        self.assertEqual(actual_flag_id, flag_id)
                        self.assertEqual(actual_team, team)

        self.assertEqual(actual_flags, expected_flags)

    def _now(self):
        return datetime.datetime.now(datetime.timezone.utc)
