import random
import time
import unittest

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
