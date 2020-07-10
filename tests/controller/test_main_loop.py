from collections import defaultdict
from unittest.mock import Mock, patch

from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.test_util import DatabaseTestCase
from ctf_gameserver.controller import controller, database


@patch('ctf_gameserver.controller.database.update_scoring')
class MainLoopTest(DatabaseTestCase):

    fixtures = ['tests/controller/fixtures/main_loop.json']
    metrics = defaultdict(Mock)

    @patch('time.sleep')
    @patch('logging.warning')
    def test_null(self, warning_mock, sleep_mock, _):
        controller.main_loop_step(self.connection, self.metrics, False)

        warning_mock.assert_called_with('Competition start and end time must be configured in the database')
        sleep_mock.assert_called_once_with(60)

    @patch('time.sleep')
    def test_before_game(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "+1 hour"), '
                           '                               end = datetime("now", "+1 day")')

        controller.main_loop_step(self.connection, self.metrics, False)

        sleep_mock.assert_called_once_with(60)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, -1)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag')
            total_flag_count = cursor.fetchone()[0]
        self.assertEqual(total_flag_count, 0)

    @patch('time.sleep')
    def test_first_tick(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now"), '
                           '                               end = datetime("now", "+1 day")')

        controller.main_loop_step(self.connection, self.metrics, False)
        sleep_mock.assert_called_once_with(0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, 0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag')
            total_flag_count = cursor.fetchone()[0]
        self.assertEqual(total_flag_count, 6)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE service_id=1')
            service_flag_count = cursor.fetchone()[0]
        self.assertEqual(service_flag_count, 3)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE protecting_team_id=4')
            team_flag_count = cursor.fetchone()[0]
        self.assertEqual(team_flag_count, 2)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE tick=0')
            tick_flag_count = cursor.fetchone()[0]
        self.assertEqual(tick_flag_count, 6)

    @patch('time.sleep')
    def test_next_tick_undue(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-1030 seconds"), '
                           '                               end = datetime("now", "+85370 seconds"), '
                           '                               current_tick=5')

        controller.main_loop_step(self.connection, self.metrics, False)

        sleep_mock.assert_called_once()
        sleep_arg = sleep_mock.call_args[0][0]
        self.assertGreater(sleep_arg, 40)
        self.assertLessEqual(sleep_arg, 50)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, 5)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag')
            tick_flag_count = cursor.fetchone()[0]
        self.assertEqual(tick_flag_count, 0)

    @patch('time.sleep')
    def test_next_tick_overdue(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-19 minutes"), '
                           '                               end = datetime("now", "+1421 minutes"), '
                           '                               current_tick=5')

        controller.main_loop_step(self.connection, self.metrics, False)

        sleep_mock.assert_called_once_with(0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, 6)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE tick=6')
            tick_flag_count = cursor.fetchone()[0]
        self.assertEqual(tick_flag_count, 6)

    @patch('time.sleep')
    def test_last_tick(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-1 day"), '
                           '                               end = datetime("now", "+3 minutes"), '
                           '                               current_tick=479')

        controller.main_loop_step(self.connection, self.metrics, False)
        sleep_mock.assert_called_once_with(0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, 480)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE tick=480')
            tick_flag_count = cursor.fetchone()[0]
        self.assertEqual(tick_flag_count, 6)

    @patch('time.sleep')
    def test_shortly_after_game(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-1441 minutes"), '
                           '                               end = datetime("now", "-1 minutes"), '
                           '                               current_tick=479')

        controller.main_loop_step(self.connection, self.metrics, False)
        self.assertEqual(sleep_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_args_list[0][0][0], 0)
        self.assertEqual(sleep_mock.call_args_list[1][0][0], 60)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, 479)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag')
            total_flag_count = cursor.fetchone()[0]
        self.assertEqual(total_flag_count, 0)

    @patch('time.sleep')
    def test_long_after_game(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-1465 minutes"), '
                           '                               end = datetime("now", "-25 minutes"), '
                           '                               current_tick=479')

        controller.main_loop_step(self.connection, self.metrics, False)
        self.assertEqual(sleep_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_args_list[0][0][0], 0)
        self.assertEqual(sleep_mock.call_args_list[1][0][0], 60)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, 479)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag')
            total_flag_count = cursor.fetchone()[0]
        self.assertEqual(total_flag_count, 0)

    @patch('time.sleep')
    def test_after_game_nonstop(self, sleep_mock, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-1 day"), '
                           '                               end = datetime("now"), '
                           '                               current_tick=479')

        controller.main_loop_step(self.connection, self.metrics, True)
        sleep_mock.assert_called_once_with(0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
            new_tick = cursor.fetchone()[0]
        self.assertEqual(new_tick, 480)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE tick=480')
            tick_flag_count = cursor.fetchone()[0]
        self.assertEqual(tick_flag_count, 6)


@patch('ctf_gameserver.controller.database.update_scoring')
class DatabaseTest(DatabaseTestCase):
    """
    Tests for the `ctf_gameserver.controller.database` module. Only tests special cases, the general
    functionality is covered by MainLoopTest.
    """

    fixtures = ['tests/controller/fixtures/main_loop.json']

    def test_prohibit_changes(self, _):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT * FROM scoring_gamecontrol ORDER BY id')
            old_gamecontrol = cursor.fetchall()
            cursor.execute('SELECT * FROM scoring_flag ORDER BY id')
            old_flag = cursor.fetchall()

        database.get_control_info(self.connection, prohibit_changes=True)
        database.increase_tick(self.connection, prohibit_changes=True)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT * FROM scoring_gamecontrol ORDER BY id')
            new_gamecontrol = cursor.fetchall()
            cursor.execute('SELECT * FROM scoring_flag ORDER BY id')
            new_flag = cursor.fetchall()

        self.assertEqual(old_gamecontrol, new_gamecontrol)
        self.assertEqual(old_flag, new_flag)
