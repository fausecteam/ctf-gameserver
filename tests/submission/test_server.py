import asyncio
from collections import defaultdict
import datetime
from unittest.mock import Mock
from unittest.mock import patch

from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.flag import generate as generate_flag
from ctf_gameserver.lib.test_util import DatabaseTestCase
from ctf_gameserver.submission.submission import serve


class ServerTest(DatabaseTestCase):

    fixtures = ['tests/submission/fixtures/server.json']
    flag_prefix = 'FAUST_'
    flag_secret = b'topsecret'
    metrics = defaultdict(Mock)

    async def connect(self):
        # For this to work on GitHub Actions (in Docker), we need to use the v4 address instead of
        # "localhost"
        task = asyncio.create_task(serve('127.0.0.1', 6666, self.connection, {
            'flag_secret': self.flag_secret,
            'team_regex': None,
            'competition_name': 'Test CTF',
            'flag_prefix': self.flag_prefix,
            'metrics': self.metrics
        }))

        for _ in range(50):
            try:
                reader, writer = await asyncio.open_connection('127.0.0.1', 6666)
                break
            except OSError:
                await asyncio.sleep(0.1)

        return (task, reader, writer)

    @patch('ctf_gameserver.submission.submission._match_net_number')
    def test_basic(self, net_number_mock):
        async def coroutine():
            net_number_mock.return_value = 103

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now"), '
                               '                               end = datetime("now", "+1 hour")')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 0)

            task, reader, writer = await self.connect()
            await reader.readuntil(b'\n\n')

            expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=60)
            flag = generate_flag(expiration_time, 4, 102, self.flag_secret, self.flag_prefix).encode('ascii')
            writer.write(flag + b'\n')

            response = await reader.readline()
            self.assertEqual(response, flag + b' OK\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
                cursor.execute('SELECT flag_id, capturing_team_id, tick FROM scoring_capture')
                captured_flag, capturing_team, capture_tick = cursor.fetchone()

            self.assertEqual(capture_count, 1)
            self.assertEqual(captured_flag, 4)
            self.assertEqual(capturing_team, 3)
            self.assertEqual(capture_tick, 6)

            writer.close()
            task.cancel()

        asyncio.run(coroutine())

    @patch('ctf_gameserver.submission.submission._match_net_number')
    def test_multiple_flags(self, net_number_mock):
        async def coroutine():
            net_number_mock.return_value = 103

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now"), '
                               '                               end = datetime("now", "+1 hour")')

            task, reader, writer = await self.connect()
            await reader.readuntil(b'\n\n')

            expiration_time = datetime.datetime.now() - datetime.timedelta(seconds=1)
            old_flag = generate_flag(expiration_time, 1, 102, self.flag_secret,
                                     self.flag_prefix).encode('ascii')
            writer.write(old_flag + b'\n')

            response = await reader.readline()
            self.assertEqual(response, old_flag + b' OLD Flag has expired\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 0)

            expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=60)

            own_flag = generate_flag(expiration_time, 5, 103, self.flag_secret,
                                     self.flag_prefix).encode('ascii')
            writer.write(own_flag + b'\n')

            response = await reader.readline()
            self.assertEqual(response, own_flag + b' OWN You cannot submit your own flag\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 0)

            nop_flag = generate_flag(expiration_time, 3, 104, self.flag_secret,
                                     self.flag_prefix).encode('ascii')
            writer.write(nop_flag + b'\n')

            response = await reader.readline()
            self.assertEqual(response, nop_flag + b' INV You cannot submit flags of a NOP team\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 0)

            valid_flag = generate_flag(expiration_time, 4, 102, self.flag_secret,
                                       self.flag_prefix).encode('ascii')
            writer.write(valid_flag + b'\n')

            response = await reader.readline()
            self.assertEqual(response, valid_flag + b' OK\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
                cursor.execute('SELECT flag_id FROM scoring_capture')
                captured_flag = cursor.fetchone()[0]
            self.assertEqual(capture_count, 1)
            self.assertEqual(captured_flag, 4)

            writer.write(valid_flag + b'\n')
            response = await reader.readline()
            self.assertEqual(response, valid_flag + b' DUP You already submitted this flag\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 1)

            writer.close()
            task.cancel()

        asyncio.run(coroutine())

    @patch('ctf_gameserver.submission.submission._match_net_number')
    def test_out_of_order(self, net_number_mock):
        async def coroutine():
            net_number_mock.return_value = 103

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now"), '
                               '                               end = datetime("now", "+1 hour")')

            task, reader, writer = await self.connect()

            expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=60)

            flag1 = generate_flag(expiration_time, 2, 102, self.flag_secret,
                                  self.flag_prefix).encode('ascii')
            writer.write(flag1 + b'\n')

            flag2 = generate_flag(expiration_time, 4, 102, self.flag_secret,
                                  self.flag_prefix).encode('ascii')
            writer.write(flag2 + b'\n')

            own_flag = generate_flag(expiration_time, 5, 103, self.flag_secret,
                                     self.flag_prefix).encode('ascii')
            writer.write(own_flag + b'\n')

            await reader.readuntil(b'\n\n')

            response = await reader.readline()
            self.assertEqual(response, flag1 + b' OK\n')
            response = await reader.readline()
            self.assertEqual(response, flag2 + b' OK\n')
            response = await reader.readline()
            self.assertEqual(response, own_flag + b' OWN You cannot submit your own flag\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
                cursor.execute('SELECT flag_id FROM scoring_capture ORDER BY flag_id')
                captured_flag1 = cursor.fetchone()[0]
                captured_flag2 = cursor.fetchone()[0]
            self.assertEqual(capture_count, 2)
            self.assertEqual(captured_flag1, 2)
            self.assertEqual(captured_flag2, 4)

            writer.close()
            task.cancel()

        asyncio.run(coroutine())

    @patch('ctf_gameserver.submission.submission._match_net_number')
    def test_multiple_clients(self, net_number_mock):
        async def coroutine():
            net_number_mock.side_effect = [103, 102]

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now"), '
                               '                               end = datetime("now", "+1 hour")')

            task, reader_103, writer_103 = await self.connect()
            await reader_103.readuntil(b'\n\n')
            reader_102, writer_102 = await asyncio.open_connection('127.0.0.1', 6666)
            await reader_102.readuntil(b'\n\n')

            expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=60)

            flag_102 = generate_flag(expiration_time, 4, 102, self.flag_secret,
                                     self.flag_prefix).encode('ascii')
            writer_103.write(flag_102 + b'\n')
            writer_102.write(flag_102 + b'\n')

            response = await reader_103.readline()
            self.assertEqual(response, flag_102 + b' OK\n')
            response = await reader_102.readline()
            self.assertEqual(response, flag_102 + b' OWN You cannot submit your own flag\n')

            flag_103 = generate_flag(expiration_time, 4, 103, self.flag_secret,
                                     self.flag_prefix).encode('ascii')
            writer_103.write(flag_103 + b'\n')
            writer_102.write(flag_103 + b'\n')

            response = await reader_103.readline()
            self.assertEqual(response, flag_103 + b' OWN You cannot submit your own flag\n')
            response = await reader_102.readline()
            self.assertEqual(response, flag_103 + b' OK\n')

            writer_103.write(flag_102 + b'\n')

            response = await reader_103.readline()
            self.assertEqual(response, flag_102 + b' DUP You already submitted this flag\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 2)

            writer_102.close()
            writer_103.close()
            task.cancel()

        asyncio.run(coroutine())

    @patch('ctf_gameserver.submission.submission._match_net_number')
    def test_after_competition(self, net_number_mock):
        async def coroutine():
            net_number_mock.return_value = 103

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-1 hour"), '
                               '                               end = datetime("now")')

            task, reader, writer = await self.connect()
            await reader.readuntil(b'\n\n')

            expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=60)
            flag = generate_flag(expiration_time, 4, 102, self.flag_secret, self.flag_prefix).encode('ascii')
            writer.write(flag + b'\n')

            response = await reader.readline()
            self.assertEqual(response, flag + b' ERR Competition is over\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 0)

            writer.close()
            task.cancel()

        asyncio.run(coroutine())

    @patch('ctf_gameserver.submission.submission._match_net_number')
    def test_invalid(self, net_number_mock):
        async def coroutine():
            net_number_mock.return_value = 103

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('UPDATE scoring_gamecontrol SET start = datetime("now", "-1 hour"), '
                               '                               end = datetime("now")')

            task, reader, writer = await self.connect()
            await reader.readuntil(b'\n\n')

            flag = 'überfläg'.encode('utf-8')
            writer.write(flag + b'\n')
            response = await reader.readline()
            self.assertEqual(response, flag + b' INV Invalid flag\n')

            flag = b''
            writer.write(flag + b'\n')
            response = await reader.readline()
            self.assertEqual(response, flag + b' INV Invalid flag\n')

            flag = b'NOTFAUST_Q1RGLSUQmjVTRTmXRZ4ELKTzKyqagXcS'
            writer.write(flag + b'\n')
            response = await reader.readline()
            self.assertEqual(response, flag + b' INV Invalid flag\n')

            flag = b'FAUST_Q1RGLSUQmjVTRTmXRZ4ELKTzKyqagXc\0'
            writer.write(flag + b'\n')
            response = await reader.readline()
            self.assertEqual(response, flag + b' INV Invalid flag\n')

            with transaction_cursor(self.connection) as cursor:
                cursor.execute('SELECT COUNT(*) FROM scoring_capture')
                capture_count = cursor.fetchone()[0]
            self.assertEqual(capture_count, 0)

            writer.close()
            task.cancel()

        asyncio.run(coroutine())
