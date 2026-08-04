from typing import TYPE_CHECKING, Protocol

from baboossh import Connection, Tunnel

if TYPE_CHECKING:
    class _Workspace(Protocol):
        tunnels: dict[int, Tunnel]

__all__ = ["TunnelsMixin"]


class TunnelsMixin:
    """`Workspace` methods for managing SOCKS `Tunnel` objects."""

    def tunnel_open(self: "_Workspace", target: str, port: int | None = None) -> bool:
        if port is not None and port in self.tunnels.keys():
            print("A tunnel is already opened at port "+str(port))
            return False
        connection = Connection.from_target(target)
        if connection is None:
            print("Connection not found.")
            return False
        try:
            tun = Tunnel(connection, port)
        except Exception as exc:
            print("Error opening tunnel: "+str(exc))
            return False
        self.tunnels[tun.port] = tun
        return True

    def tunnel_close(self: "_Workspace", port: int) -> None:
        if port not in self.tunnels.keys():
            print("No tunnel on port "+str(port))
            return
        tun = self.tunnels.pop(port)
        try:
            tun.close()
        except Exception as exc:
            print("Error closing tunnel: "+str(exc))
