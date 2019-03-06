import time
import unittest
import random

from unittest import mock

from ctf_gameserver.lib import flag

class FlagTestCase(unittest.TestCase):
    def test_deterministic(self):
        tstamp = time.time()
        flag1 = flag.generate(12, 13, timestamp=tstamp)
        flag2 = flag.generate(12, 13, timestamp=tstamp)
        self.assertEqual(flag1, flag2)


    def test_valid_flag(self):
        payload = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        timestamp = int(time.time() + 12)
        team = 12
        service = 13
        flag1 = flag.generate(team, service, payload=payload, timestamp=timestamp)
        team_, service_, payload_, timestamp_ = flag.verify(flag1)
        self.assertEqual(team, team_)
        self.assertEqual(service, service_)
        self.assertEqual(payload, payload_)
        self.assertEqual(timestamp, timestamp_)


    def test_old_flag(self):
        timestamp = int(time.time() - 12)
        testflag = flag.generate(12, 13, timestamp=timestamp)
        self.assertRaises(flag.FlagExpired, flag.verify, testflag)


    def test_invalid_mac(self):
        testflag = flag.generate(12, 13)
        s = set("0123456789")
        try:
            s.remove(testflag[-1])
        except KeyError:
            pass

        wrongflag = testflag[:-1] + random.choice(list(s))
        self.assertRaises(flag.InvalidFlagMAC, flag.verify, wrongflag)
