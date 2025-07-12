import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from ctf_gameserver.lib import date_time


class EnsureUTCAwareTest(TestCase):

    def test_none(self):
        self.assertIsNone(date_time.ensure_utc_aware(None))

    def test_datetime_utc(self):
        dt_in = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        dt_out = date_time.ensure_utc_aware(dt_in)

        self.assertIs(dt_in, dt_out)
        self.assertEqual(dt_out.utcoffset().total_seconds(), 0)

    def test_datetime_berlin(self):
        timezone = ZoneInfo('Europe/Berlin')
        dt_in = datetime.datetime(2000, 1, 1, tzinfo=timezone)
        dt_out = date_time.ensure_utc_aware(dt_in)

        self.assertIs(dt_in, dt_out)
        self.assertEqual(dt_out.tzinfo, timezone)

    def test_datetime_unaware(self):
        dt_in = datetime.datetime(2000, 1, 1)
        dt_out = date_time.ensure_utc_aware(dt_in)

        self.assertIsNotNone(dt_out.tzinfo)
        self.assertEqual(dt_out.utcoffset().total_seconds(), 0)

    def test_time_utc(self):
        t_in = datetime.time(tzinfo=datetime.timezone.utc)
        t_out = date_time.ensure_utc_aware(t_in)

        self.assertIs(t_in, t_out)
        self.assertEqual(t_out.utcoffset().total_seconds(), 0)

    def test_time_unaware(self):
        t_in = datetime.time()
        t_out = date_time.ensure_utc_aware(t_in)

        self.assertIsNotNone(t_out.tzinfo)
        self.assertEqual(t_out.utcoffset().total_seconds(), 0)
