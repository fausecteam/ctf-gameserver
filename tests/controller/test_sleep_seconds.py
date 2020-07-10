from collections import defaultdict
import datetime
from unittest import TestCase
from unittest.mock import Mock

from ctf_gameserver.controller import controller


class SleepSecondsTest(TestCase):

    metrics = defaultdict(Mock)

    def test_before(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        control_info = {
            'start': now+datetime.timedelta(minutes=5),
            'end': now+datetime.timedelta(minutes=10),
            'tick_duration': 60,
            'current_tick': -1
        }

        sleep_seconds = controller.get_sleep_seconds(control_info, self.metrics, now)
        self.assertEqual(sleep_seconds, 300)

    def test_start(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        control_info = {
            'start': now,
            'end': now+datetime.timedelta(minutes=10),
            'tick_duration': 60,
            'current_tick': -1
        }

        sleep_seconds = controller.get_sleep_seconds(control_info, self.metrics, now)
        self.assertEqual(sleep_seconds, 0)

    def test_during_1(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        control_info = {
            'start': now,
            'end': now+datetime.timedelta(minutes=10),
            'tick_duration': 60,
            'current_tick': 0
        }

        sleep_seconds = controller.get_sleep_seconds(control_info, self.metrics, now)
        self.assertEqual(sleep_seconds, 60)

    def test_during_2(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        control_info = {
            'start': now-datetime.timedelta(seconds=200),
            'end': now+datetime.timedelta(minutes=10),
            'tick_duration': 60,
            'current_tick': 3
        }

        sleep_seconds = controller.get_sleep_seconds(control_info, self.metrics, now)
        self.assertEqual(sleep_seconds, 40)

    def test_late(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        control_info = {
            'start': now-datetime.timedelta(seconds=200),
            'end': now+datetime.timedelta(minutes=10),
            'tick_duration': 60,
            # We should already be in tick 3
            'current_tick': 2
        }

        sleep_seconds = controller.get_sleep_seconds(control_info, self.metrics, now)
        self.assertEqual(sleep_seconds, 0)
