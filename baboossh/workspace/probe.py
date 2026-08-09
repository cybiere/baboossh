from typing import TYPE_CHECKING, Protocol

from baboossh import Connection, Endpoint, Host, Path
from baboossh.exceptions import ConnectionClosedError, NoPathError

if TYPE_CHECKING:
    class _Workspace(Protocol):
        def path_del(self, src: "Host | None", dst: Endpoint) -> bool: ...

__all__ = ["ProbeMixin"]


class ProbeMixin:
    """`Workspace` methods for probing endpoints and establishing paths."""

    def probe(self: "_Workspace", targets: "list[Endpoint]", gateway: str = "auto",
            verbose: bool = False, find_new: bool = False) -> None:
        for endpoint in targets:
            print("Probing \033[1;34m"+str(endpoint)+"\033[0m > ", end="", flush=True)
            if verbose:
                print("")

            conn = Connection(endpoint, None, None)
            working = False
            host: "Host | None" = None
            if not find_new and endpoint.reachable and str(gateway) == "auto":
                if verbose:
                    print("\nEndpoint is supposed to be reachable, trying...")
                working = conn.probe(verbose=verbose)
                host = Host.find_one(prev_hop_to=endpoint)
            if not working and str(gateway) != "auto":
                if verbose:
                    print("\nA gateway was given, trying...")
                if gateway == "local":
                    gateway_conn = None
                    host = None
                else:
                    host = Host.find_one(name=gateway)
                    if host is None:
                        print("\nError: unknown gateway host "+str(gateway))
                        return
                    gateway_conn = Connection.find_one(endpoint=host.closest_endpoint)
                try:
                    working = conn.probe(gateway=gateway_conn, verbose=verbose)
                except ConnectionClosedError as exc:
                    print("\nError: "+str(exc))
                    return
            if not working and not find_new:
                try:
                    Path.get(endpoint)
                except NoPathError:
                    pass
                else:
                    if verbose:
                        print("\nThere is an existing path to the Endpoint, trying...")
                    working = conn.probe(verbose=verbose)
                    host = Host.find_one(prev_hop_to=endpoint)
                    if not working and host is not None:
                        self.path_del(host, endpoint)
            if not working:
                if verbose:
                    print("\nTrying to reach directly from local...")
                host = None
                working = conn.probe(gateway=None, verbose=verbose)
            if not working:
                if verbose:
                    print("\nTrying from every Host from closest to furthest...")
                def sort_key(candidate: "Host") -> float:
                    candidate_distance = candidate.distance
                    return candidate_distance if candidate_distance is not None else float("inf")
                hosts = Host.find_all(scope=True)
                hosts.sort(key=sort_key)
                working = False
                for host in hosts:
                    gateway_endpoint = host.closest_endpoint
                    loop_gateway = Connection.find_one(endpoint=gateway_endpoint)
                    working = conn.probe(gateway=loop_gateway, verbose=verbose)
                    if working:
                        break

            if working:
                path = Path(host, endpoint)
                path.save()
                if host is None:
                    print("\033[1;32mOK\033[0m: reached directly from \033[1;34mlocal\033[0m.")
                else:
                    print("\033[1;32mOK\033[0m: reached using \033[1;34m"+str(host)+"\033[0m as gateway")
            else:
                print("\033[1;31mKO\033[0m: could not reach the endpoint.")
            if verbose:
                print("########################\n")
