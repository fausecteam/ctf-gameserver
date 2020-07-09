import socket
from unittest import TestCase

from ctf_gameserver.lib import args


class HostPortTest(TestCase):

    def test_ipv4(self):
        host, port, family = args.parse_host_port('127.0.0.1:22')
        self.assertEqual(host, '127.0.0.1')
        self.assertEqual(port, 22)
        self.assertEqual(family, socket.AF_INET)

    def test_ipv6(self):
        host, port, family = args.parse_host_port('[::1]:8000')
        self.assertEqual(host, '::1')
        self.assertEqual(port, 8000)
        self.assertEqual(family, socket.AF_INET6)

    def test_hostname(self):
        parsed = args.parse_host_port('localhost:1337')
        self.assertEqual(parsed[1], 1337)
        # Can't know about host and family for sure

    def test_invalid(self):
        with self.assertRaises(ValueError):
            args.parse_host_port('::1')
