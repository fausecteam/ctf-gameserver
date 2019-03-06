import asynchat
import asyncore
import socket
import logging
import datetime
import base64

import psycopg2

from ctf_gameserver.lib import flag

class FlagHandler(asynchat.async_chat):
    def __init__(self, sock, addr, dbconnection, secret,
                 conteststart, contestend, flagvalidity, tickduration):
        asynchat.async_chat.__init__(self, sock=sock)
        ipaddr, port = addr
        self.team = int(ipaddr.split('.')[2])
        self._addr = addr
        self.set_terminator(b"\n")
        self._logger = logging.getLogger("%13s %5d" % (ipaddr, port))
        self._cursor = None
        self._dbconnection = dbconnection
        self._secret = base64.b64decode(secret)
        self.buffer = b''
        self._logger.info("Accepted connection from Team %s", self.team)
        self._banner()
        self._conteststart = conteststart
        self._contestend = contestend
        self._flagvalidity = flagvalidity
        self._tickduration = tickduration

    def _reply(self, message):
        self._logger.debug("-> %s", message.decode('utf-8'))
        self.push(message + b"\n")

    def _get_tick(self, timestamp):
        tick = ((timestamp - self._conteststart.timestamp()) / self._tickduration) \
               - self._flagvalidity
        return int(tick + 0.2)

    def _handle_flag(self):
        if self.buffer == b'':
            self._reply(b"418 I'm a teapot!")
            return

        if self.buffer == b'666':
            self._reply(b"So this, then, was the kernel of the brute!")
            return

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if now < self._conteststart:
            self._reply(b"Contest didn't even start yet!")
            return

        if now > self._contestend:
            self._reply(b"Contest already over!")
            return

        try:
            curflag = self.buffer.decode('us-ascii')
        except UnicodeDecodeError as e:
            self._reply(u"Flags should be of the Format [-_a-zA-Z0-9]+"
                        .encode('utf-8'))
            return

        try:
            team, service, _, timestamp = flag.verify(curflag, self._secret)
        except flag.InvalidFlagFormat:
            self._reply(b"Flag not recognized")
            return
        except flag.InvalidFlagMAC:
            self._reply(b"No such Flag")
            return
        except flag.FlagExpired as e:
            self._reply((u"Flag expired since %.1f seconds" % e.args).encode('utf-8'))
            return

        if team == self.team:
            self._reply(b"Can't submit a flag for your own team")
            return

        try:
            result = self._store_capture(team, service, timestamp)
            if result:
                self._reply(u"Thank you for your submission!".encode('utf-8'))

        except psycopg2.DatabaseError as psqle:
            self._logger.exception("Error while inserting values into database")
            self._logger.warning("%s: %s", psqle.diag.severity, psqle.diag.message_primary)
            self._logger.info(psqle.diag.internal_query)
            self._reply(u"Something went wrong with your submission!".encode('utf-8'))


    def _store_capture(self, team, service, timestamp):
        with self._dbconnection:
            with self._dbconnection.cursor() as cursor:
                cursor.execute("""SELECT nop_team FROM registration_team WHERE user_id = %s""",
                               (team,))
                nopp, = cursor.fetchone()
                if nopp:
                    self._reply(u"Can not submit flags for the NOP team".encode("utf-8"))
                    return False

                tick = self._get_tick(timestamp)
                cursor.execute("""SELECT id FROM scoring_flag
                                  WHERE service_id = %s
                                    AND protecting_team_id = %s
                                    AND tick = %s""",
                               (service, team, tick))
                flag_id = cursor.fetchone()[0]

                cursor.execute("""SELECT count(*) FROM scoring_capture
                                  WHERE flag_id = %s
                                    AND capturing_team_id = %s""",
                               (flag_id, self.team))
                count = cursor.fetchone()[0]

                if count > 0:
                    self._reply(u"Flags should only be submitted once!".encode('utf-8'))
                    return False

                cursor.execute("""INSERT INTO scoring_capture
                                      (flag_id, capturing_team_id, timestamp, tick)
                                  VALUES
                                      (%s, %s, now(),
                                       (SELECT current_tick
                                        FROM scoring_gamecontrol))""",
                               (flag_id, self.team))
                return True


    def _banner(self):
        self.push(u"FAUSTCTF Flagserver\n"
                  u"One flag per line please!\n".encode('utf-8'))


    def collect_incoming_data(self, data):
        self.buffer = self.buffer + data


    def found_terminator(self):
        self._logger.debug("<- %s", self.buffer.decode('utf-8'))
        self._handle_flag()
        self.buffer = b''


class FlagServer(asyncore.dispatcher):
    def __init__(self, host, port, *args):
        asyncore.dispatcher.__init__(self)
        self.create_socket(family=socket.AF_INET)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        self._otherargs = args
        self._logger = logging.getLogger("server")

    def handle_accepted(self, sock, addr):
        self._logger.info('Incoming connection from %s', repr(addr))
        FlagHandler(sock, addr, *self._otherargs)
