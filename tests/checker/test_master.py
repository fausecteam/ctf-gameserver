import datetime
from unittest.mock import patch

from ctf_gameserver.checker.master import MasterLoop
from ctf_gameserver.lib.checkresult import CheckResult
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.test_util import DatabaseTestCase


class MasterTest(DatabaseTestCase):

    fixtures = ['tests/checker/fixtures/master.json']

    def setUp(self):
        self.master_loop = MasterLoop(self.connection, None, 'service1', '/dev/null', None, 90, 8, 10,
                                      '0.0.%s.1', b'secret', {})

    def test_handle_flag_request(self):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')

        task_info = {
            'service': 'service1',
            '_team_id': 2,
            'team': 92,
            'tick': 1
        }

        params1 = {'tick': 1}
        resp1 = self.master_loop.handle_flag_request(task_info, params1)
        params2 = {'tick': 1}
        resp2 = self.master_loop.handle_flag_request(task_info, params2)
        params3 = {'tick': 1, 'payload': 'TmV2ZXIgZ28='}
        resp3 = self.master_loop.handle_flag_request(task_info, params3)

        self.assertEqual(resp1, resp2)
        self.assertNotEqual(resp1, resp3)

        params4 = {'tick': 2}
        resp4 = self.master_loop.handle_flag_request(task_info, params4)
        params5 = {'tick': 2}
        resp5 = self.master_loop.handle_flag_request(task_info, params5)

        self.assertEqual(resp4, resp5)
        self.assertNotEqual(resp1, resp4)

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
        start_time = datetime.datetime.utcnow().replace(microsecond=0)
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
        start_time = datetime.datetime.utcnow().replace(microsecond=0)
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

    def test_update_launch_params(self):
        self.master_loop.update_launch_params()
        self.assertEqual(self.master_loop.tasks_per_launch, 0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=1')
        self.master_loop.update_launch_params()
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
        self.master_loop.update_launch_params()
        self.assertEqual(self.master_loop.tasks_per_launch, 9)

        self.master_loop.tick_duration = datetime.timedelta(seconds=360)
        self.master_loop.update_launch_params()
        self.assertEqual(self.master_loop.tasks_per_launch, 3)

        self.master_loop.tick_duration = datetime.timedelta(seconds=180)
        self.master_loop.interval = 5
        self.master_loop.update_launch_params()
        self.assertEqual(self.master_loop.tasks_per_launch, 5)

        self.master_loop.max_check_duration = 30
        self.master_loop.update_launch_params()
        self.assertEqual(self.master_loop.tasks_per_launch, 3)

        self.master_loop.max_check_duration = 3600
        with self.assertRaises(ValueError):
            self.master_loop.update_launch_params()
