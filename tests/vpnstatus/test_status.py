import asyncio
from collections import defaultdict
from datetime import datetime, UTC
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.test_util import DatabaseTestCase
from ctf_gameserver.vpnstatus.status import loop_step


class VPNStatusTest(DatabaseTestCase):

    fixtures = ['tests/vpnstatus/fixtures/status.json']
    metrics = defaultdict(Mock)

    def test_wireguard(self):
        with TemporaryDirectory(prefix='ctf-fake-path-') as fake_path_dir:
            os.environ['PATH'] = fake_path_dir + ':' + os.environ['PATH']

            with (Path(fake_path_dir) / 'sudo').open('w', encoding='utf-8') as sudo_file:
                os.fchmod(sudo_file.fileno(), 0o755)
                script_lines = [
                    '#!/bin/sh',
                    'if [ "$*" != "--non-interactive -- /usr/bin/wg show all latest-handshakes" ]; then',
                    '    exit 1',
                    'fi',
                    'echo "wg_102\tZeymPBFvUbfWHyZSccoWaf5CKEO96YZkCH5lbv8rqU0=\t1689415702"',
                    'echo "wg_103\toWaR/kbHAUBvrOMxFN5frtZZRgNZ5EAJdb56PrdFPX4=\t0"'
                ]
                sudo_file.write('\n'.join(script_lines) + '\n')

            asyncio.run(loop_step(self.connection, self.metrics, wireguard_if_pattern='wg_%d'))

        checks = self._fetch_checks()
        self.assertEqual(len(checks), 3)

        self.assertEqual(checks[0]['team_id'], 2)
        self.assertEqual(checks[0]['wireguard_handshake_time'], datetime.fromtimestamp(1689415702, UTC))

        self.assertEqual(checks[1]['team_id'], 3)
        self.assertIsNone(checks[1]['wireguard_handshake_time'])

        self.assertEqual(checks[2]['team_id'], 4)
        self.assertIsNone(checks[2]['wireguard_handshake_time'])

    @patch('ctf_gameserver.vpnstatus.status.NETWORK_TIMEOUT', 1)
    def test_ping(self):
        asyncio.run(loop_step(self.connection, self.metrics, gateway_ip_pattern='127.0.%s.1',
                              demo_ip_pattern='127.0.%s.2', vulnbox_ip_pattern='169.254.%s.42'))

        checks = self._fetch_checks()
        self.assertEqual(len(checks), 3)
        self.assertEqual(checks[0]['team_id'], 2)
        self.assertEqual(checks[1]['team_id'], 3)
        self.assertEqual(checks[2]['team_id'], 4)

        for check in checks:
            self.assertIsNone(check['wireguard_handshake_time'])
            self.assertGreaterEqual(check['gateway_ping_rtt_ms'], 0)
            self.assertLess(check['gateway_ping_rtt_ms'], 1000)
            self.assertGreaterEqual(check['demo_ping_rtt_ms'], 0)
            self.assertLess(check['demo_ping_rtt_ms'], 1000)
            self.assertIsNone(check['vulnbox_ping_rtt_ms'])
            self.assertFalse(check['demo_service_ok'])
            self.assertFalse(check['vulnbox_service_ok'])

    @patch('ctf_gameserver.vpnstatus.status.NETWORK_TIMEOUT', 1)
    def test_net_numbers(self):
        asyncio.run(loop_step(self.connection, self.metrics, gateway_ip_pattern='127.0.%s.1',
                              team_net_numbers=set([103, 104])))

        checks = self._fetch_checks()
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[0]['team_id'], 3)
        self.assertEqual(checks[1]['team_id'], 4)

        for check in checks:
            self.assertGreaterEqual(check['gateway_ping_rtt_ms'], 0)
            self.assertLess(check['gateway_ping_rtt_ms'], 1000)

    @patch('ctf_gameserver.vpnstatus.status.NETWORK_TIMEOUT', 1)
    def test_tcp(self):
        async def handle_conn(_reader, writer):
            writer.close()
            await writer.wait_closed()

        async def tcp_server(host, port):
            server = await asyncio.start_server(handle_conn, host, port)
            async with server:
                await server.serve_forever()

        async def coroutine():
            task = asyncio.create_task(tcp_server('127.0.102.2', 7777))

            # Wait for the server to start up
            for _ in range(50):
                try:
                    _reader, writer = await asyncio.open_connection('127.0.102.2', 7777)
                except OSError:
                    await asyncio.sleep(0.1)
                else:
                    writer.close()
                    await writer.wait_closed()
                    break

            await loop_step(self.connection, self.metrics,
                            demo_ip_pattern='127.0.%s.2', demo_service_port=7777,
                            vulnbox_ip_pattern='169.254.%s.42', vulnbox_service_port=7777)

            task.cancel()

        asyncio.run(coroutine())

        checks = self._fetch_checks()
        self.assertEqual(len(checks), 3)

        self.assertEqual(checks[0]['team_id'], 2)
        self.assertTrue(checks[0]['demo_service_ok'])
        self.assertFalse(checks[0]['vulnbox_service_ok'])

        self.assertEqual(checks[1]['team_id'], 3)
        self.assertFalse(checks[1]['demo_service_ok'])
        self.assertFalse(checks[1]['vulnbox_service_ok'])

    def test_nothing(self):
        asyncio.run(loop_step(self.connection, self.metrics))

        checks = self._fetch_checks()
        self.assertEqual(len(checks), 3)

        self.assertEqual(checks[0], {
            'team_id': 2,
            'wireguard_handshake_time': None,
            'gateway_ping_rtt_ms': None,
            'demo_ping_rtt_ms': None,
            'vulnbox_ping_rtt_ms': None,
            'demo_service_ok': False,
            'vulnbox_service_ok': False
        })

    def _fetch_checks(self):
        with transaction_cursor(self.connection) as cursor:
            cursor.execute('SELECT team_id, wireguard_handshake_time, gateway_ping_rtt_ms, demo_ping_rtt_ms,'
                           '       vulnbox_ping_rtt_ms, demo_service_ok, vulnbox_service_ok '
                           'FROM vpnstatus_vpnstatuscheck ORDER BY team_id')
            checks = cursor.fetchall()

        return [{'team_id': c[0],
                 'wireguard_handshake_time': c[1],
                 'gateway_ping_rtt_ms': c[2],
                 'demo_ping_rtt_ms': c[3],
                 'vulnbox_ping_rtt_ms': c[4],
                 'demo_service_ok': c[5],
                 'vulnbox_service_ok': c[6]
                 } for c in checks]
