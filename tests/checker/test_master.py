import datetime
from unittest.mock import patch

from ctf_gameserver.checker.master import MasterLoop
from ctf_gameserver.checker.metrics import DummyQueue
from ctf_gameserver.lib.checkresult import CheckResult
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.flag import verify
from ctf_gameserver.lib.test_util import DatabaseTestCase


class MasterTest(DatabaseTestCase):

    fixtures = ['tests/checker/fixtures/master.json']

    def setUp(self):
        self.secret = b'secret'
        self.master_loop = MasterLoop(self.connection, 'service1', '/dev/null', None, 2, 8, 10, '0.0.%s.1',
                                      self.secret, {}, DummyQueue())

    def test_handle_flag_request(self):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')

        task_info = {
            'service': 'service1',
            '_team_id': 2,
            'team': 92,
            'tick': 2
        }

        params1 = {'tick': 2}
        resp1 = self.master_loop.handle_flag_request(task_info, params1)
        flag_id1, team1 = verify(resp1, self.secret)

        params2 = {'tick': 2}
        resp2 = self.master_loop.handle_flag_request(task_info, params2)
        flag_id2, team2 = verify(resp2, self.secret)
        # "params3" and "resp3" don't exist anymore

        self.assertEqual(resp1, resp2)
        self.assertEqual(flag_id1, 2)
        self.assertEqual(team1, 92)
        self.assertEqual(flag_id2, 2)
        self.assertEqual(team2, 92)

        params4 = {'tick': 1}
        resp4 = self.master_loop.handle_flag_request(task_info, params4)
        flag_id4, team4 = verify(resp4, self.secret)
        params5 = {'tick': 1}
        resp5 = self.master_loop.handle_flag_request(task_info, params5)
        flag_id5, team5 = verify(resp5, self.secret)

        self.assertEqual(resp4, resp5)
        self.assertNotEqual(resp1, resp4)
        self.assertEqual(flag_id4, 1)
        self.assertEqual(team4, 92)
        self.assertEqual(flag_id5, 1)
        self.assertEqual(team5, 92)

        params6 = {}
        self.assertIsNone(self.master_loop.handle_flag_request(task_info, params6))

        # Changing the start time changes all flags
        with transaction_cursor(self.connection) as cursor:
            # SQLite syntax for tests
            cursor.execute('UPDATE scoring_gamecontrol SET start=DATETIME("now", "+1 hour")')
        resp1_again = self.master_loop.handle_flag_request(task_info, params1)
        resp4_again = self.master_loop.handle_flag_request(task_info, params4)
        self.assertNotEqual(resp1, resp1_again)
        self.assertNotEqual(resp4, resp4_again)

    def test_handle_result_request(self):
        task_info = {
            'service': 'service1',
            '_team_id': 2,
            'team': 92,
            'tick': 1
        }
        param = CheckResult.OK.value
        start_time = datetime.datetime.now(datetime.UTC).replace(microsecond=0, tzinfo=None)
        self.assertIsNone(self.master_loop.handle_result_request(task_info, param))
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id = 1 AND team_id = 2 AND tick = 1')
            self.assertEqual(cursor.fetchone()[0], CheckResult.OK.value)
            cursor.execute('SELECT placement_end FROM scoring_flag'
                           '    WHERE service_id = 1 AND protecting_team_id = 2 AND tick = 1')
            self.assertGreaterEqual(cursor.fetchone()[0], start_time)

        task_info['tick'] = 2
        param = CheckResult.FAULTY.value
        start_time = datetime.datetime.now(datetime.UTC).replace(microsecond=0, tzinfo=None)
        self.assertIsNone(self.master_loop.handle_result_request(task_info, param))
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id = 1 AND team_id = 2 AND tick = 2')
            self.assertEqual(cursor.fetchone()[0], CheckResult.FAULTY.value)
            cursor.execute('SELECT placement_end FROM scoring_flag'
                           '    WHERE service_id = 1 AND protecting_team_id = 2 AND tick = 2')
            self.assertGreaterEqual(cursor.fetchone()[0], start_time)

        task_info['tick'] = 3
        param = 'Not an int'
        self.assertIsNone(self.master_loop.handle_result_request(task_info, param))
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id = 1 AND team_id = 2 AND tick = 3')
            self.assertIsNone(cursor.fetchone())
            cursor.execute('SELECT placement_end FROM scoring_flag'
                           '    WHERE service_id = 1 AND protecting_team_id = 2 AND tick = 3')
            self.assertIsNone(cursor.fetchone()[0])

        param = 1337
        self.assertIsNone(self.master_loop.handle_result_request(task_info, param))
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id = 1 AND team_id = 2 AND tick = 3')
            self.assertIsNone(cursor.fetchone())
            cursor.execute('SELECT placement_end FROM scoring_flag'
                           '    WHERE service_id = 1 AND protecting_team_id = 2 AND tick = 3')
            self.assertIsNone(cursor.fetchone()[0])

    @patch('ctf_gameserver.checker.database.get_check_duration')
    def test_update_launch_params(self, check_duration_mock):
        # Very short duration, but should be ignored in tick 1
        check_duration_mock.return_value = 1

        self.master_loop.update_launch_params(-1)
        self.assertEqual(self.master_loop.tasks_per_launch, 0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=1')
        self.master_loop.update_launch_params(1)
        self.assertEqual(self.master_loop.tasks_per_launch, 1)

        with transaction_cursor(self.connection) as cursor:
            for i in range(10, 400):
                username = 'team{}'.format(i)
                email = '{}@example.org'.format(username)
                cursor.execute('INSERT INTO auth_user (id, username, first_name, last_name, email, password,'
                               '                       is_superuser, is_staff, is_active, date_joined)'
                               '    VALUES (%s, %s, %s, %s, %s, %s, false, false, true, NOW())',
                               (i, username, '', '', '', 'password'))
                cursor.execute('INSERT INTO registration_team (user_id, informal_email, image, affiliation,'
                               '                               country, nop_team)'
                               '    VALUES (%s, %s, %s, %s, %s, false)', (i, email, '', '', 'World'))
                cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                               '    VALUES (1, %s, 1)', (i,))
        self.master_loop.update_launch_params(1)
        self.assertEqual(self.master_loop.tasks_per_launch, 49)

        check_duration_mock.return_value = None
        self.master_loop.update_launch_params(10)
        self.assertEqual(self.master_loop.tasks_per_launch, 49)

        check_duration_mock.return_value = 3600
        self.master_loop.update_launch_params(10)
        self.assertEqual(self.master_loop.tasks_per_launch, 49)

        check_duration_mock.return_value = 90
        self.master_loop.update_launch_params(10)
        self.assertEqual(self.master_loop.tasks_per_launch, 7)

        self.master_loop.interval = 5
        self.master_loop.update_launch_params(10)
        self.assertEqual(self.master_loop.tasks_per_launch, 4)

        check_duration_mock.return_value = 10
        self.master_loop.interval = 10
        self.master_loop.tick_duration = datetime.timedelta(seconds=90)
        self.master_loop.update_launch_params(10)
        self.assertEqual(self.master_loop.tasks_per_launch, 9)
