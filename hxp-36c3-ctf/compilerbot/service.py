#!/usr/bin/env python3

import base64
import subprocess
import socket
import threading

class NetcatClient:
    """ Python 'netcat like' module """

    def __init__(self, socket):
        self.buff = b""
        self.socket = socket

    @classmethod
    def from_socket(cls, socket):
        return cls(socket)

    @classmethod
    def from_ip_and_port(cls, ip, port):
        socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.connect((ip, port))
        return cls(socket)

    def read(self, length=1024):
        """ Read 1024 bytes off the socket """

        return self.socket.recv(length)

    def read_until(self, data):
        """ Read data into the buffer until we have data """

        while not data in self.buff:
            self.buff += self.socket.recv(1024)

        pos = self.buff.find(data)
        rval = self.buff[:pos + len(data)]
        self.buff = self.buff[pos + len(data):]

        return rval

    def write(self, data):
        self.socket.send(data)

    def close(self):
        self.socket.close()

class NetcatServer:
    """ Python 'netcat like' module """

    def __init__(self, ip, port):
        self.buff = b""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((ip, port))
        self.socket.listen(5)

    def get_connection(self):
        client_socket, addr = self.socket.accept()
        return NetcatClient.from_socket(client_socket)

    def close(self):
        self.socket.close()

def handle_connection(nc_client):
    print('Handling connection')
    nc_client.write(b'>')
    code = nc_client.read_until(b'\n')
    print('Received payload')
    code = base64.b64decode(code).decode()
    code = 'int main(void) {' + code.translate(str.maketrans('', '', '{#}')) + '}'

    result = subprocess.run(['/usr/bin/clang', '-x', 'c', '-std=c11', '-Wall',
                            '-Wextra', '-Werror', '-Wmain', '-Wfatal-errors',
                            '-o', '/dev/null', '-'], input=code.encode(),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=15.0)
    if result.returncode == 0 and result.stdout.strip() == b'':
        nc_client.write(b'OK')
    else:
        nc_client.write(b'Not OK')

nc = NetcatServer('0.0.0.0', 8011)
while True:
    nc_client = nc.get_connection()
    print('Got connection')
    t = threading.Thread(target=handle_connection, args=(nc_client, ))
    t.start()