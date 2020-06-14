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
            'FAUST_XtS7wAAXDQ1BPIUAAAAAWz1i7pmtp/HY',
            'FAUST_XuP+AAAXDfJgMq8AAAAA347vpisJsQcT',
            'FAUST_XtS7wAAXDXBheWxvYWQxDcM2TNj0lCu7',
            'FAUST_XuP+AAAXDXBheWxvYWQxmIKxwcEmDxQX',
            'FAUST_XtS7wAAXDQ1BPIUAAAAAxR5C9S9LXgdi',
            'FAUST_XuP+AAAXDfJgMq8AAAAAcqut7dVSvNOl',
            'FAUST_XtS7wAAXDXBheWxvYWQxrwHKd/CNJgkB',
            'FAUST_XuP+AAAXDXBheWxvYWQxn04LGjrQe4V8',
            'FAUST_XtS7wAAXJTj0lH8AAAAArnmozMnyfMVb',
            'FAUST_XuP+AAAXJcfVmlUAAAAAkUsJ65SCvAZW',
            'FAUST_XtS7wAAXJXBheWxvYWQxIg0Sd0Ll06VT',
            'FAUST_XuP+AAAXJXBheWxvYWQxGiKffkwjRTte',
            'FAUST_XtS7wAAXJTj0lH8AAAAAUAFSjo0EF01t',
            'FAUST_XuP+AAAXJcfVmlUAAAAAoeDpxI2QPjsv',
            'FAUST_XtS7wAAXJXBheWxvYWQx+aIiPy4SC0+Q',
            'FAUST_XuP+AAAXJXBheWxvYWQxYObaBlsWnmOE',
            'FAUST_XtS7wAAqDWepdDsAAAAAfPNLsph2Jw8v',
            'FAUST_XuP+AAAqDZiIehEAAAAA3Q30bTHWo1l9',
            'FAUST_XtS7wAAqDXBheWxvYWQxLdYijGTcd2O3',
            'FAUST_XuP+AAAqDXBheWxvYWQxsOqqEGk2u52r',
            'FAUST_XtS7wAAqDWepdDsAAAAAhQontK+Uoy9h',
            'FAUST_XuP+AAAqDZiIehEAAAAAYmCIMEQJotc4',
            'FAUST_XtS7wAAqDXBheWxvYWQxvzsgxZioxnxY',
            'FAUST_XuP+AAAqDXBheWxvYWQxLDqRTwxgE3yG',
            'FAUST_XtS7wAAqJVIc3MEAAAAAdGtfQQkMd1VT',
            'FAUST_XuP+AAAqJa090usAAAAAk+AN2kRqIVQs',
            'FAUST_XtS7wAAqJXBheWxvYWQxjF+S/iA5tzxY',
            'FAUST_XuP+AAAqJXBheWxvYWQxabGjcfYW9js/',
            'FAUST_XtS7wAAqJVIc3MEAAAAAWUdMoH5KV/un',
            'FAUST_XuP+AAAqJa090usAAAAAUeOaXaFLlwEj',
            'FAUST_XtS7wAAqJXBheWxvYWQxFKDfL+/qydWm',
            'FAUST_XuP+AAAqJXBheWxvYWQxzirUWWy6MwKe'
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
