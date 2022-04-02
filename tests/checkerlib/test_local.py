import io
import os
import socket
import sys
import tempfile
from unittest import TestCase
from unittest.mock import Mock, call, patch

from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult


class LocalTest(TestCase):
    """
    Test case for the checkerlib being run locally (such as during development).
    """

    def setUp(self):
        self.old_working_dir = os.getcwd()
        self.working_dir = tempfile.TemporaryDirectory()
        os.chdir(self.working_dir.name)

    def tearDown(self):
        os.chdir(self.old_working_dir)
        self.working_dir.cleanup()

    def test_get_flag(self):
        checkerlib.get_flag._team = 1    # pylint: disable=protected-access
        team1_tick1_flag1 = checkerlib.get_flag(1)
        team1_tick1_flag2 = checkerlib.get_flag(1)
        team1_tick2_flag = checkerlib.get_flag(2)
        checkerlib.get_flag._team = 2    # pylint: disable=protected-access
        team2_tick1_flag = checkerlib.get_flag(1)

        self.assertEqual(team1_tick1_flag1, team1_tick1_flag2)
        self.assertNotEqual(team1_tick1_flag1, team1_tick2_flag)
        self.assertNotEqual(team1_tick1_flag1, team2_tick1_flag)

    def test_state_primitive(self):
        self.assertIsNone(checkerlib.load_state('primitive'))

        checkerlib.store_state('primitive', 1337)
        self.assertEqual(checkerlib.load_state('primitive'), 1337)

    def test_state_object(self):
        self.assertIsNone(checkerlib.load_state('object'))

        obj = {'data': [b'foo', b'bar']}
        checkerlib.store_state('object', obj)
        self.assertEqual(checkerlib.load_state('object'), obj)

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_basic(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.OK
        MockChecker.service_mock.return_value = CheckResult.OK
        MockChecker.flag_mock.return_value = CheckResult.OK

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(10)
        MockChecker.service_mock.assert_called_once()
        self.assertEqual(MockChecker.flag_mock.call_count, 6)
        self.assertEqual(MockChecker.flag_mock.call_args_list, [call(10), call(9), call(8), call(7), call(6),
                                                                call(5)])
        self.assertEqual(stdout_io.getvalue(), 'Check result: OK\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '0'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_tick0(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.OK
        MockChecker.service_mock.return_value = CheckResult.OK
        MockChecker.flag_mock.return_value = CheckResult.OK

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(0)
        MockChecker.service_mock.assert_called_once()
        MockChecker.flag_mock.assert_called_once_with(0)
        self.assertEqual(stdout_io.getvalue(), 'Check result: OK\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '3'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_tick3(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.OK
        MockChecker.service_mock.return_value = CheckResult.OK
        MockChecker.flag_mock.return_value = CheckResult.OK

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(3)
        MockChecker.service_mock.assert_called_once()
        self.assertEqual(MockChecker.flag_mock.call_count, 4)
        self.assertEqual(MockChecker.flag_mock.call_args_list, [call(3), call(2), call(1), call(0)])
        self.assertEqual(stdout_io.getvalue(), 'Check result: OK\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_place_fail(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.DOWN
        MockChecker.service_mock.return_value = CheckResult.OK
        MockChecker.flag_mock.return_value = CheckResult.OK

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(10)
        MockChecker.service_mock.assert_not_called()
        MockChecker.flag_mock.assert_not_called()
        self.assertEqual(stdout_io.getvalue(), 'Check result: DOWN\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_service_fail(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.OK
        MockChecker.service_mock.return_value = CheckResult.FAULTY
        MockChecker.flag_mock.return_value = CheckResult.OK

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(10)
        MockChecker.service_mock.assert_called_once()
        MockChecker.flag_mock.assert_not_called()
        self.assertEqual(stdout_io.getvalue(), 'Check result: FAULTY\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_flag_fail(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.OK
        MockChecker.service_mock.return_value = CheckResult.OK
        MockChecker.flag_mock.return_value = CheckResult.FLAG_NOT_FOUND

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(10)
        MockChecker.service_mock.assert_called_once()
        MockChecker.flag_mock.assert_called_once_with(10)
        self.assertEqual(stdout_io.getvalue(), 'Check result: FLAG_NOT_FOUND\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_recovering(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.OK
        MockChecker.service_mock.return_value = CheckResult.OK
        MockChecker.flag_mock.side_effect = [CheckResult.OK, CheckResult.OK, CheckResult.FLAG_NOT_FOUND,
                                             CheckResult.OK, CheckResult.OK, CheckResult.OK]

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(10)
        MockChecker.service_mock.assert_called_once()
        self.assertEqual(MockChecker.flag_mock.call_count, 6)
        self.assertEqual(stdout_io.getvalue(), 'Check result: RECOVERING\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_not_recovering(self, stdout_io):
        MockChecker.reset_mocks()
        MockChecker.place_mock.return_value = CheckResult.OK
        MockChecker.service_mock.return_value = CheckResult.OK
        MockChecker.flag_mock.side_effect = [CheckResult.OK, CheckResult.OK, CheckResult.FLAG_NOT_FOUND,
                                             CheckResult.OK, CheckResult.FAULTY]

        checkerlib.run_check(MockChecker)

        MockChecker.place_mock.assert_called_once_with(10)
        MockChecker.service_mock.assert_called_once()
        self.assertEqual(MockChecker.flag_mock.call_count, 5)
        self.assertEqual(stdout_io.getvalue(), 'Check result: FAULTY\n')

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    def test_run_check_exception(self):
        # pylint: disable=abstract-method
        class ExceptionChecker(checkerlib.BaseChecker):
            def place_flag(self, tick):
                raise ValueError()

        with self.assertRaises(ValueError):
            checkerlib.run_check(ExceptionChecker)

    @patch.object(sys, 'argv', ['argv-0', '0.0.0.0', '42', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_run_check_exception_timeout(self, stdout_io):
        # pylint: disable=abstract-method
        class ExceptionChecker(checkerlib.BaseChecker):
            def place_flag(self, tick):
                raise socket.timeout()

        checkerlib.run_check(ExceptionChecker)
        self.assertEqual(stdout_io.getvalue(), 'Check result: DOWN\n')


class MockChecker(checkerlib.BaseChecker):
    @classmethod
    def reset_mocks(cls):
        cls.place_mock = Mock()
        cls.service_mock = Mock()
        cls.flag_mock = Mock()

    def place_flag(self, tick):
        return self.__class__.place_mock(tick)

    def check_service(self):
        return self.__class__.service_mock()

    def check_flag(self, tick):
        return self.__class__.flag_mock(tick)
