#!/usr/bin/env python3

import socketserver


_STORE = {}


class RequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        client_data = self._recv_line()
        print('Received:', client_data)

        try:
            operation, client_data = client_data.split(' ', 1)
        except ValueError:
            response = 'INVALID'
        else:
            if operation == 'GET':
                key = client_data
                try:
                    response = _STORE[key]
                except KeyError:
                    response = 'NODATA'
            elif operation == 'SET':
                try:
                    key, value = client_data.split(' ', 1)
                except ValueError:
                    response = 'INVALID'
                else:
                    _STORE[key] = value
                    response = 'OK'
            else:
                response = 'INVALID'

        print('Response:', response)
        self.request.sendall(response.encode('utf-8') + b'\n')

    def _recv_line(self):
        received = b''
        while not received.endswith(b'\n'):
            new = self.request.recv(1024)
            if len(new) == 0:
                if not received.endswith(b'\n'):
                    raise EOFError('Unexpected EOF')
                break
            received += new
        return received.decode('utf-8').rstrip()


if __name__ == "__main__":

    with socketserver.TCPServer(('localhost', 9999), RequestHandler) as server:
        server.serve_forever()
