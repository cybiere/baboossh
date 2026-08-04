from typing import TYPE_CHECKING, Protocol

from baboossh import Endpoint, Host, Path
from baboossh.exceptions import NoPathError

if TYPE_CHECKING:
    class _Workspace(Protocol):
        def unstore(self, data: dict[str, list[str]]) -> None: ...

__all__ = ["PathsMixin"]


class PathsMixin:
    """`Workspace` methods for managing `Path` objects."""

    def path_find_existing(self, dst: str, as_ip: bool = False) -> None:
        found_dst: "Endpoint | None"
        if dst in [host.name for host in Host.find_all()]:
            host = Host.find_one(name=dst)
            if host is None:
                print("The host provided doesn't exist in this workspace")
                return
            found_dst = host.closest_endpoint
        else:
            try:
                found_dst = Endpoint.find_one(ip_port=dst)
            except ValueError:
                print("Please specify a valid endpoint in the IP:PORT form")
                return
        if found_dst is None:
            print("The endpoint provided doesn't exist in this workspace")
            return
        if Path.direct(found_dst):
            print("The destination should be reachable from the host")
            return
        try:
            chain = Path.get(found_dst)
        except NoPathError:
            print("No path could be found to the destination")
            return
        if as_ip:
            labels = ["local" if link is None else
                    (str(link.closest_endpoint) if isinstance(link, Host) else str(link))
                    for link in chain]
        else:
            labels = ["local" if link is None else str(link) for link in chain]
        print(" > ".join(labels))

    def path_del(self: "_Workspace", src: str, dst: str) -> bool:
        found_src: "Host | None"
        if str(src).lower() != "local":
            if src not in [host.name for host in Host.find_all()]:
                print("Not a known Host name.")
                return False
            found_src = Host.find_one(name=src)
            if found_src is None:
                print("The source Host provided doesn't exist in this workspace")
                return False
        else:
            found_src = None
        try:
            found_dst = Endpoint.find_one(ip_port=dst)
        except ValueError:
            print("Please specify valid destination endpoint in the IP:PORT form")
            return False
        if found_dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return False
        path = Path(found_src, found_dst)
        if path.id is None:
            print("The specified Path doesn't exist in this workspace.")
            return False
        self.unstore(path.delete())
        return True

    def path_add(self, src: str, dst: str) -> None:
        found_src: "Host | None"
        if src.lower() != "local":
            if src not in [host.name for host in Host.find_all()]:
                print("Not a known Host name.")
                return
            found_src = Host.find_one(name=src)
            if found_src is None:
                print("The source Host provided doesn't exist in this workspace")
                return
        else:
            found_src = None
        try:
            found_dst = Endpoint.find_one(ip_port=dst)
        except ValueError:
            print("Please specify valid destination endpoint in the IP:PORT form")
            return
        if found_dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return
        path = Path(found_src, found_dst)
        path.save()
        print("Path saved")
