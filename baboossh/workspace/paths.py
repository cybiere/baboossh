from baboossh import Endpoint, Host, Path
from baboossh.exceptions import NoPathError


class PathsMixin:
    """`Workspace` methods for managing `Path` objects."""

    def path_find_existing(self, dst, as_ip=False):
        if dst in [host.name for host in Host.find_all()]:
            host = Host.find_one(name=dst)
            dst = host.closest_endpoint
        else:
            try:
                dst = Endpoint.find_one(ip_port=dst)
            except ValueError:
                print("Please specify a valid endpoint in the IP:PORT form")
                return
        if dst is None:
            print("The endpoint provided doesn't exist in this workspace")
            return
        if Path.direct(dst):
            print("The destination should be reachable from the host")
            return
        try:
            chain = Path.get(dst)
        except NoPathError:
            print("No path could be found to the destination")
            return
        if chain[0] is None:
            chain[0] = "local"
        if as_ip:
            print(" > ".join(str(link.closest_endpoint) \
                    if isinstance(link, Host) else str(link) for link in chain))
        else:
            print(" > ".join(str(link) for link in chain))

    def path_del(self, src, dst):
        if str(src).lower() != "local":
            if src not in [host.name for host in Host.find_all()]:
                print("Not a known Host name.")
                return False
            src = Host.find_one(name=src)
            if src is None:
                print("The source Host provided doesn't exist in this workspace")
                return False
        else:
            src = None
        try:
            dst = Endpoint.find_one(ip_port=dst)
        except ValueError:
            print("Please specify valid destination endpoint in the IP:PORT form")
            return False
        if dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return False
        path = Path(src, dst)
        if path.id is None:
            print("The specified Path doesn't exist in this workspace.")
            return False
        self.unstore(path.delete())
        return True

    def path_add(self, src, dst):
        if src.lower() != "local":
            if src not in [host.name for host in Host.find_all()]:
                print("Not a known Host name.")
                return
            src = Host.find_one(name=src)
            if src is None:
                print("The source Host provided doesn't exist in this workspace")
                return
        else:
            src = None
        try:
            dst = Endpoint.find_one(ip_port=dst)
        except ValueError:
            print("Please specify valid destination endpoint in the IP:PORT form")
            return
        if dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return
        path = Path(src, dst)
        path.save()
        print("Path saved")
