#!/usr/bin/env python3

import logging
import socket

from ctf_gameserver import checkerlib


class ExampleChecker(checkerlib.BaseChecker):

    def place_flag(self, tick):
        conn = connect(self.ip)
        flag = checkerlib.get_flag(tick)
        conn.sendall('SET {} {}\n'.format(tick, flag).encode('utf-8'))
        logging.info('Sent SET command: Flag %s', flag)

        try:
            resp = recv_line(conn)
            logging.info('Received response to SET command: %s', repr(resp))
        except UnicodeDecodeError:
            logging.warning('Received non-UTF-8 data: %s', repr(resp))
            return checkerlib.CheckResult.FAULTY
        if resp != 'OK':
            logging.warning('Received wrong response to SET command')
            return checkerlib.CheckResult.FAULTY

        conn.close()
        return checkerlib.CheckResult.OK

    def check_service(self):
        conn = connect(self.ip)
        conn.sendall(b'XXX\n')
        logging.info('Sent dummy command')

        try:
            recv_line(conn)
            logging.info('Received response to dummy command')
        except UnicodeDecodeError:
            logging.warning('Received non-UTF-8 data')
            return checkerlib.CheckResult.FAULTY

        conn.close()
        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        flag = checkerlib.get_flag(tick)

        conn = connect(self.ip)
        conn.sendall('GET {}\n'.format(tick).encode('utf-8'))
        logging.info('Sent GET command')

        try:
            resp = recv_line(conn)
            logging.info('Received response to GET command: %s', repr(resp))
        except UnicodeDecodeError:
            logging.warning('Received non-UTF-8 data: %s', repr(resp))
            return checkerlib.CheckResult.FAULTY
        if resp != flag:
            logging.warning('Received wrong response to GET command')
            return checkerlib.CheckResult.FLAG_NOT_FOUND

        conn.close()
        return checkerlib.CheckResult.OK


def connect(ip):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, 9999))
    return sock


def recv_line(conn):

    received = b''
    while not received.endswith(b'\n'):
        new = conn.recv(1024)
        if len(new) == 0:
            if not received.endswith(b'\n'):
                raise EOFError('Unexpected EOF')
            break
        received += new
    return received.decode('utf-8').rstrip()


if __name__ == '__main__':

    checkerlib.run_check(ExampleChecker)
