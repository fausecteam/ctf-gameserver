import datetime
import unittest
from unittest import mock

from ctf_gameserver.submission.flagserver import FlagHandler
from ctf_gameserver.lib import flag

class UserInputTestCase(unittest.TestCase):
    def setUp(self):
        self._handler = FlagHandler(None, ("203.0.113.42", 1337), None,
                                    datetime.datetime.now(tz=datetime.timezone.utc),
                                    datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(minutes=10),
                                    None, None)

        
    def test_empty(self):
        self._handler.buffer = b""
        self.assertIsNone(self._handler._handle_flag())


    def test_nonascii(self):
        with mock.patch.object(self._handler, '_reply') as reply:
            self._handler.buffer = b'\xf3'
            self._handler._handle_flag()
            reply.assert_called_with(b"Flags should be of the Format [-_a-zA-Z0-9]+")

        with mock.patch.object(self._handler, '_reply') as reply:
            self._handler.buffer = u'ümläut'.encode('utf-8')
            self._handler._handle_flag()
            reply.assert_called_with(b"Flags should be of the Format [-_a-zA-Z0-9]+")
            

    def test_out_of_contest(self):
        with mock.patch.object(self._handler, '_reply') as reply:
            with mock.patch.object(self._handler, '_conteststart',
                                   new=datetime.datetime.now(tz=datetime.timezone.utc) +
                                       datetime.timedelta(minutes=10)) as start:
                self._handler.buffer = b'SOMETHING'
                self._handler._handle_flag()
                reply.assert_called_with(b"Contest didn't even start yet!")

            with mock.patch.object(self._handler, '_contestend',
                                   new=datetime.datetime.now(tz=datetime.timezone.utc) -
                                       datetime.timedelta(minutes=10)) as start:
                self._handler.buffer = b'SOMETHING'
                self._handler._handle_flag()
                reply.assert_called_with(b"Contest already over!")


    def test_not_against_self(self):
        with mock.patch.object(self._handler, '_reply') as reply:
            testflag = flag.generate(113, 12)
            self._handler.buffer = testflag.encode('us-ascii')
            self._handler._handle_flag()
            reply.assert_called_with(b"Can't submit a flag for your own team")
            
