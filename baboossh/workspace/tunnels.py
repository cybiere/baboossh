from baboossh import Connection, Tunnel


class TunnelsMixin:
    """`Workspace` methods for managing SOCKS `Tunnel` objects."""

    def tunnel_open(self, target, port=None):
        if port is not None and port in self.tunnels.keys():
            print("A tunnel is already opened at port "+str(port))
            return False
        connection = Connection.from_target(target)
        try:
            tun = Tunnel(connection, port)
        except Exception as exc:
            print("Error opening tunnel: "+str(exc))
            return False
        self.tunnels[tun.port] = tun
        return True

    def tunnel_close(self, port):
        if port not in self.tunnels.keys():
            print("No tunnel on port "+str(port))
        tun = self.tunnels.pop(port)
        try:
            tun.close()
        except Exception as exc:
            print("Error closing tunnel: "+str(exc))
