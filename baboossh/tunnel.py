import select
import socket
import struct
from socketserver import StreamRequestHandler, ThreadingTCPServer
import threading

class SocksProxy(StreamRequestHandler):
    SOCKS_VERSION = 5

    def handle(self):
        # greeting header
        # read and unpack 2 bytes from a client
        header = self.connection.recv(2)
        version, nmethods = struct.unpack("!BB", header)

        # socks 5
        if version != self.SOCKS_VERSION:
            print("SOCKS version mismatch. Please use socks5")
            return
        assert nmethods > 0

        # get available methods
        methods = self.get_available_methods(nmethods)

        # accept only NO AUTH auth
        if 0 not in set(methods):
            # close connection
            self.server.close_request(self.request)
            return

        # send welcome message
        self.connection.sendall(struct.pack("!BB", self.SOCKS_VERSION, 0))

        # request
        version, cmd, _, address_type = struct.unpack("!BBBB", self.connection.recv(4))
        assert version == self.SOCKS_VERSION

        if address_type == 1:  # IPv4
            address = socket.inet_ntoa(self.connection.recv(4))
        elif address_type == 3:  # Domain name
            domain_length = ord(self.connection.recv(1)[0])
            address = self.connection.recv(domain_length)

        port = struct.unpack('!H', self.connection.recv(2))[0]

        # reply
        try:
            if cmd == 1:  # CONNECT
                remote = self.server.output.transport.open_channel(
                    kind="direct-tcpip",
                    dest_addr=(address, port),
                    src_addr=("", 0)
                )
            else:
                self.server.close_request(self.request)

            addr = struct.unpack("!I", socket.inet_aton(address))[0]
            port = int(port)
            reply = struct.pack("!BBBBIH", self.SOCKS_VERSION, 0, 0, address_type,
                                addr, port)

        except Exception as err:
            print(err)
            # return connection refused error
            reply = self.generate_failed_reply(address_type, 5)

        self.connection.sendall(reply)

        # establish data exchange
        if reply[1] == 0 and cmd == 1:
            self.exchange_loop(self.connection, remote)

        self.server.close_request(self.request)

    def get_available_methods(self, n):
        methods = []
        for i in range(n):
            methods.append(ord(self.connection.recv(1)))
        return methods

    def generate_failed_reply(self, address_type, error_number):
        return struct.pack("!BBBBIH", self.SOCKS_VERSION, error_number, 0, address_type, 0, 0)

    def exchange_loop(self, client, remote):
        while True:
            # wait until client or remote is available for read
            r, w, e = select.select([client, remote], [], [])

            if client in r:
                data = client.recv(4096)
                if remote.send(data) <= 0:
                    break

            if remote in r:
                data = remote.recv(4096)
                if client.send(data) <= 0:
                    break

class Tunnel():
    """Open SOCKS tunnel to a :class:`Host`

    Each tunnel is opened in distinct thread so that BabooSSH is still usable
    while the tunnel is open.

    Attributes:
        connection (:class:`.Connection`): the tunnel exit
        port (int): the tunnel entrance (local) port. Uses a random port if
            none is provided.
    """

    def __init__(self, connection, port=None):
        self.connection = connection
        if port is None:
            port = 0
        self.connection.open()
        self.connection.used_by_tunnels.append(self)
        self.server = ThreadingTCPServer(('127.0.0.1', port), SocksProxy)
        self.server.output = self.connection.conn
        ip, newport = self.server.server_address
        self.port = newport
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        print("Tunnel to "+str(self.connection)+" open on port "+str(self.port))

    def close(self):
        """Close a previously opened port"""
        try:
            self.connection.used_by_tunnels.remove(self)
        except:
            pass
        self.server.shutdown()
        print("Tunnel port "+str(self.port)+" closed")

    def __str__(self):
        return str(self.port)+"->"+str(self.connection)
