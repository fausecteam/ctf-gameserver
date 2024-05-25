import os.path
from unittest import SkipTest
from unittest.mock import patch
import shutil
import subprocess
import tempfile
import time

from ctf_gameserver.checker.master import MasterLoop
from ctf_gameserver.checker.metrics import DummyQueue
from ctf_gameserver.lib.checkresult import CheckResult
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.test_util import DatabaseTestCase


class IntegrationTest(DatabaseTestCase):

    fixtures = ['tests/checker/fixtures/integration.json']

    def setUp(self):
        self.check_duration_patch = patch('ctf_gameserver.checker.database.get_check_duration')
        check_duration_mock = self.check_duration_patch.start()
        check_duration_mock.return_value = None

    def tearDown(self):
        self.check_duration_patch.stop()

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_basic(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__), 'integration_basic_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        master_loop.supervisor.queue_timeout = 0.01
        # Sanity check before any tick
        self.assertFalse(master_loop.step())
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_statuscheck')
            self.assertEqual(cursor.fetchone()[0], 0)

        # Start tick
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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
            cursor.execute('SELECT flagid FROM scoring_flag'
                           '    WHERE service_id=1 AND protecting_team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], 'value identifier')

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_missing_checkerscript(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__), 'does not exist')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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
    def test_down(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_down_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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
            self.assertEqual(cursor.fetchone()[0], CheckResult.DOWN.value)

    @patch('logging.warning')
    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_unfinished(self, monotonic_mock, warning_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_unfinished_checkerscript.py')

        checkerscript_pidfile = tempfile.NamedTemporaryFile()
        os.environ['CHECKERSCRIPT_PIDFILE'] = checkerscript_pidfile.name

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        monotonic_mock.return_value = 20

        master_loop.supervisor.queue_timeout = 0.01
        # Checker Script gets started, will return False because no messages yet
        self.assertFalse(master_loop.step())
        master_loop.supervisor.queue_timeout = 10
        self.assertTrue(master_loop.step())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT data FROM scoring_checkerstate WHERE service_id=1 AND team_id=2')
            state_result = cursor.fetchone()
        self.assertEqual(state_result[0], 'gASVHgAAAAAAAACMGkxvcmVtIGlwc3VtIGRvbG9yIHNpdCBhbWV0lC4=')

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
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], 5)

        warning_mock.assert_called_with('Terminating all %d Runner processes', 1)

        del os.environ['CHECKERSCRIPT_PIDFILE']
        checkerscript_pidfile.close()

    @patch('logging.warning')
    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_cancel_checks(self, monotonic_mock, warning_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_unfinished_checkerscript.py')

        checkerscript_pidfile = tempfile.NamedTemporaryFile()
        os.environ['CHECKERSCRIPT_PIDFILE'] = checkerscript_pidfile.name

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=0')
            cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                           '    VALUES (1, 2, 0)')
        monotonic_mock.return_value = 20

        master_loop.supervisor.queue_timeout = 0.01
        # Checker Script gets started, will return False because no messages yet
        self.assertFalse(master_loop.step())
        master_loop.supervisor.queue_timeout = 10
        self.assertTrue(master_loop.step())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT data FROM scoring_checkerstate WHERE service_id=1 AND team_id=2')
            state_result = cursor.fetchone()
        self.assertEqual(state_result[0], 'gASVHgAAAAAAAACMGkxvcmVtIGlwc3VtIGRvbG9yIHNpdCBhbWV0lC4=')

        checkerscript_pidfile.seek(0)
        checkerscript_pid = int(checkerscript_pidfile.read())
        # Ensure process is running by sending signal 0
        os.kill(checkerscript_pid, 0)

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET cancel_checks=true')

        master_loop.supervisor.queue_timeout = 0.01
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

        warning_mock.assert_called_with('Terminating all %d Runner processes', 1)

        del os.environ['CHECKERSCRIPT_PIDFILE']
        checkerscript_pidfile.close()

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_multi_teams_ticks(self, monotonic_mock):
        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_multi_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        # Tick 0
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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
            self.assertEqual(cursor.fetchone()[0], CheckResult.DOWN.value)
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
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            # Prepopulate state for the non-checked service to ensure we'll never get this data returned
            data = 'gAN9cQBYAwAAAGZvb3EBWAMAAABiYXJxAnMu'
            cursor.execute('INSERT INTO scoring_checkerstate (team_id, service_id, key, data)'
                           '    VALUES (2, 2, %s, %s), (3, 2, %s, %s)', ('key1', data, 'key2', data))

        # Tick 0
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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
            cursor.execute('SELECT flagid FROM scoring_flag'
                           '    WHERE service_id=1 AND protecting_team_id=3 AND tick=0')
            self.assertIsNone(cursor.fetchone()[0])

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
            cursor.execute('SELECT flagid FROM scoring_flag'
                           '    WHERE service_id=1 AND protecting_team_id=3 AND tick=1')
            self.assertEqual(cursor.fetchone()[0], 'value identifier')

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
            cursor.execute('SELECT flagid FROM scoring_flag'
                           '    WHERE service_id=1 AND protecting_team_id=3 AND tick=2')
            self.assertIsNone(cursor.fetchone()[0])

    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_shutdown(self, monotonic_mock):
        checkerscript_path = '/dev/null'

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, None, 2, 1, 10,
                                 '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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
        if shutil.which('sudo') is None or not os.path.exists('/etc/sudoers.d/ctf-checker'):
            raise SkipTest('sudo or sudo config not available')

        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_sudo_checkerscript.py')

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, 'ctf-checkerrunner', 2, 1,
                                 10, '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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

    @patch('logging.warning')
    @patch('ctf_gameserver.checker.master.get_monotonic_time')
    def test_sudo_unfinished(self, monotonic_mock, warning_mock):
        if shutil.which('sudo') is None or not os.path.exists('/etc/sudoers.d/ctf-checker'):
            raise SkipTest('sudo or sudo config not available')

        checkerscript_path = os.path.join(os.path.dirname(__file__),
                                          'integration_unfinished_checkerscript.py')

        # NOTE: This needs `sysctl fs.protected_regular=0` if tempfile is created in /tmp
        checkerscript_pidfile = tempfile.NamedTemporaryFile()
        os.chmod(checkerscript_pidfile.name, 0o666)
        os.environ['CHECKERSCRIPT_PIDFILE'] = checkerscript_pidfile.name

        monotonic_mock.return_value = 10
        master_loop = MasterLoop(self.connection, 'service1', checkerscript_path, 'ctf-checkerrunner', 2, 1,
                                 10, '0.0.%s.1', b'secret', {}, DummyQueue())

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET start=NOW()')
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

        def signal_script():
            subprocess.check_call(['sudo', '--user=ctf-checkerrunner', '--non-interactive', '--',
                                   'kill', '-0', str(checkerscript_pid)])

        # Ensure process is running by sending signal 0
        signal_script()

        master_loop.supervisor.queue_timeout = 0.01
        monotonic_mock.return_value = 50
        self.assertFalse(master_loop.step())
        # Process should still be running
        signal_script()

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('UPDATE scoring_gamecontrol SET current_tick=1')
        monotonic_mock.return_value = 190
        self.assertFalse(master_loop.step())
        # Poll whether the process has been killed
        for _ in range(100):
            try:
                signal_script()
            except subprocess.CalledProcessError:
                break
            time.sleep(0.1)
        with self.assertRaises(subprocess.CalledProcessError):
            signal_script()

        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT COUNT(*) FROM scoring_flag'
                           '    WHERE placement_start IS NOT NULL AND placement_end IS NULL')
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute('SELECT status FROM scoring_statuscheck'
                           '    WHERE service_id=1 AND team_id=2 AND tick=0')
            self.assertEqual(cursor.fetchone()[0], 5)

        warning_mock.assert_called_with('Terminating all %d Runner processes', 1)

        del os.environ['CHECKERSCRIPT_PIDFILE']
        checkerscript_pidfile.close()
