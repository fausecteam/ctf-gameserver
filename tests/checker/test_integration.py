import os.path
from unittest import SkipTest
from unittest.mock import patch
import sqlite3
import tempfile
import time

from ctf_gameserver.checker.master import MasterLoop
from ctf_gameserver.lib.checkresult import CheckResult
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.test_util import DatabaseTestCase


class IntegrationTest(DatabaseTestCase):

    fixtures = ['tests/checker/fixtures/integration.json']

    def setUp(self):
        self.state_db_conn = sqlite3.connect(':memory:')
        with transaction_cursor(self.state_db_conn) as cursor:
            cursor.execute('CREATE TABLE checkerstate ('
                           '    team_id INTEGER,'
                           '    service_id INTEGER,'
                           '    identifier CHARACTER VARYING (128),'
                           '    data TEXT'
                           ') PRIMARY KEY (team_id, service_id, identifier)')

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_basic(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__), 'integration_basic_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        master_loop.supervisor.queue_timeout = 0.01
        # Sanity check before any tick
        self.assertFalse(master_loop.step())
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 0)

        # Start tick
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        # Checker won't get started because interval is not yet over
        self.assertFalse(master_loop.step())
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE placement_start IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 0)

        # Interval is over, Checker Script gets started
        monotonic_mock.return_value = 20
        # Will return False because no messages yet
        self.assertFalse(master_loop.step())
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE placement_start IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 1)

        master_loop.supervisor.queue_timeout = 10
        # Handle all messages from Checker Script
        while master_loop.step():
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], CheckResult.OK.value)

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_missing_checkerscript(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__), 'does not exist')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        monotonic_mock.return_value = 20

        master_loop.supervisor.queue_timeout = 0.01
        # Checker Script gets started, will return False because no messages yet
        self.assertFalse(master_loop.step())

        master_loop.supervisor.queue_timeout = 10
        while master_loop.step():
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_start IS NOT NULL AND placement_end IS NULL')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 0)

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_exception(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_exception_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        monotonic_mock.return_value = 20

        master_loop.supervisor.queue_timeout = 0.01
        # Checker Script gets started, will return False because no messages yet
        self.assertFalse(master_loop.step())

        master_loop.supervisor.queue_timeout = 10
        while master_loop.step():
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_start IS NOT NULL AND placement_end IS NULL')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 0)

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_timeout(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_timeout_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        monotonic_mock.return_value = 20

        master_loop.supervisor.queue_timeout = 0.01
        # Checker Script gets started, will return False because no messages yet
        self.assertFalse(master_loop.step())

        master_loop.supervisor.queue_timeout = 10
        while master_loop.step():
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], CheckResult.TIMEOUT.value)

    @patch('logging.warning')
    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_unfinished(self, monotonic_mock, warning_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_unfinished_checkerscript.py')

        checkerscript_pidfile = tempfile.NamedTemporaryFile()
        os.environ['CHECKERSCRIPT_PIDFILE'] = checkerscript_pidfile.name

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        monotonic_mock.return_value = 20

        master_loop.supervisor.queue_timeout = 0.01
        # Checker Script gets started, will return False because no messages yet
        self.assertFalse(master_loop.step())
        master_loop.supervisor.queue_timeout = 10
        self.assertTrue(master_loop.step())

        checkerscript_pidfile.seek(0)
        checkerscript_pid = int(checkerscript_pidfile.read())
        # Ensure process is running by sending signal 0
        os.kill(checkerscript_pid, 0)

        master_loop.supervisor.queue_timeout = 0.01
        monotonic_mock.return_value = 50
        self.assertFalse(master_loop.step())
        # Process should still be running
        os.kill(checkerscript_pid, 0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=1')
        monotonic_mock.return_value = 190
        self.assertFalse(master_loop.step())
        # Poll whether the process has been killed
        for _ in range(100):
            try:
                os.kill(checkerscript_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        with self.assertRaises(ProcessLookupError):
            os.kill(checkerscript_pid, 0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_start IS NOT NULL AND placement_end IS NULL')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 0)

        warning_mock.assert_called_with('Terminating all %d Runner processes', 1)

        del os.environ['CHECKERSCRIPT_PIDFILE']
        checkerscript_pidfile.close()

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_multi_teams_ticks(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_multi_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        # Tick 0
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            # Also add flags for service 2 (which does not get checked) to make sure it won't get touched
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0), (1, 3, 0), (2, 2, 0), (2, 3, 0)')
        monotonic_mock.return_value = 20
        master_loop.supervisor.queue_timeout = 0.01
        self.assertFalse(master_loop.step())
        monotonic_mock.return_value = 100
        master_loop.supervisor.queue_timeout = 10
        while master_loop.step() or master_loop.get_running_script_count() > 0:
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 2)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 2)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], CheckResult.FAULTY.value)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=3 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], CheckResult.OK.value)

        # Tick 1
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=1')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 1), (1, 3, 1), (2, 2, 1), (2, 3, 1)')
        monotonic_mock.return_value = 200
        master_loop.supervisor.queue_timeout = 0.01
        self.assertFalse(master_loop.step())
        monotonic_mock.return_value = 280
        master_loop.supervisor.queue_timeout = 10
        while master_loop.step() or master_loop.get_running_script_count() > 0:
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 4)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 4)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], CheckResult.FAULTY.value)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=3 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], CheckResult.OK.value)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=1')
            self.assertEqual(cursor.fetchone()[0], CheckResult.TIMEOUT.value)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=3 AND tick=1')
            self.assertEqual(cursor.fetchone()[0], CheckResult.FAULTY.value)

        # Tick 2
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=2')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 2), (1, 3, 2), (2, 2, 2), (2, 3, 2)')
        monotonic_mock.return_value = 380
        master_loop.supervisor.queue_timeout = 0.01
        self.assertFalse(master_loop.step())
        monotonic_mock.return_value = 460
        master_loop.supervisor.queue_timeout = 10
        while master_loop.step() or master_loop.get_running_script_count() > 0:
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 6)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 6)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=2')
            self.assertEqual(cursor.fetchone()[0], CheckResult.RECOVERING.value)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=3 AND tick=2')
            self.assertEqual(cursor.fetchone()[0], CheckResult.OK.value)

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_state(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_state_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        with transaction_cursor(self.state_db_conn) as cursor:
            # Prepopulate state for the non-checked service to ensure we'll never get this data returned
            data = 'gAN9cQBYAwAAAGZvb3EBWAMAAABiYXJxAnMu'
            cursor.execute('INSERT INTO checkerstate (team_id, service_id, identifier, data)'
                           '    VALUES (2, 2, %s, %s), (3, 2, %s, %s)', ('key1', data, 'key2', data))

        # Tick 0
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0), (1, 3, 0)')
        monotonic_mock.return_value = 20
        master_loop.supervisor.queue_timeout = 0.01
        self.assertFalse(master_loop.step())
        monotonic_mock.return_value = 100
        master_loop.supervisor.queue_timeout = 10
        while master_loop.step() or master_loop.get_running_script_count() > 0:
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 2)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck WHERE status=%s',
                           (CheckResult.OK.value,))
            self.assertEqual(cursor.fetchone()[0], 2)

        # Tick 1
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=1')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 1), (1, 3, 1)')
        monotonic_mock.return_value = 200
        master_loop.supervisor.queue_timeout = 0.01
        self.assertFalse(master_loop.step())
        monotonic_mock.return_value = 280
        master_loop.supervisor.queue_timeout = 10
        while master_loop.step() or master_loop.get_running_script_count() > 0:
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 4)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck WHERE status=%s',
                           (CheckResult.OK.value,))
            self.assertEqual(cursor.fetchone()[0], 4)

        # Tick 2
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=2')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 2), (1, 3, 2)')
        monotonic_mock.return_value = 380
        master_loop.supervisor.queue_timeout = 0.01
        self.assertFalse(master_loop.step())
        monotonic_mock.return_value = 460
        master_loop.supervisor.queue_timeout = 10
        while master_loop.step() or master_loop.get_running_script_count() > 0:
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 6)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck WHERE status=%s',
                           (CheckResult.OK.value,))
            self.assertEqual(cursor.fetchone()[0], 6)

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_shutdown(self, monotonic_mock):
        checkerscript_path = '/dev/null'

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path, None,
                                 90, 1, 10, '0.0.%s.1', b'secret', {})

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')

        master_loop.shutting_down = True
        master_loop.supervisor.queue_timeout = 0.01
        monotonic_mock.return_value = 20
        # Will return False because no messages yet
        self.assertFalse(master_loop.step())
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE placement_start IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 0)

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_sudo(self, monotonic_mock):
        if not os.path.exists('/etc/sudoers.d/ctf-checker'):
            raise SkipTest('sudo config not available')

        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_sudo_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, self.state_db_conn, 'service1', checkerscript_path,
                                 'ctf-checkerrunner', 90, 1, 10, '0.0.%s.1', b'secret', {})

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        monotonic_mock.return_value = 20

        master_loop.supervisor.queue_timeout = 0.01
        # Checker Script gets started, will return False because no messages yet
        self.assertFalse(master_loop.step())

        master_loop.supervisor.queue_timeout = 10
        while master_loop.step():
            pass
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag WHERE placement_end IS NOT NULL')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], CheckResult.OK.value)
