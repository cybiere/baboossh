from typing import TYPE_CHECKING, Protocol

from baboossh import Connection, Creds, Endpoint, Host, Tag, User
from baboossh.exceptions import NoPathError

if TYPE_CHECKING:
    class _Workspace(Protocol):
        options: dict[str, object]
        workspace_folder: str
        def unstore(self, data: dict[str, list[str]]) -> None: ...
        def probe(self, targets: "list[Endpoint]", gateway: str = ...,
                verbose: bool = ..., find_new: bool = ...) -> None: ...

__all__ = ["ConnectionsMixin"]


class ConnectionsMixin:
    """`Workspace` methods for managing `Connection` objects, and enumerating targets."""

    def connection_close(self: "_Workspace", target: str) -> "bool | None":
        """Close a :class:`Connection` and any connection or tunnel using it

        Args:
            target (str): the `Connection` string
        """

        connection = Connection.from_target(target)
        if connection is None:
            print("Connection not found.")
            return False
        return connection.close()

    def connection_del(self: "_Workspace", target: str) -> bool:
        """Remove a :class:`Connection` from the workspace

        Args:
            target (str): the `Connection` string
        """

        connection = Connection.from_target(target)
        if connection is None:
            print("Connection not found.")
            return False
        self.unstore(connection.delete())
        return True

    def enum_probe(self: "_Workspace", target: str | None = None, again: bool = False) -> "list[Endpoint]":
        if target is not None:
            if target == "*":
                endpoints = Endpoint.find_all(scope=True)
            elif target[0] == "!":
                tag = Tag(target[1:])
                endpoints = tag.endpoints
            else:
                endpoint = Endpoint.find_one(ip_port=target)
                if endpoint is None:
                    raise ValueError("Supplied endpoint isn't in workspace")
                return [endpoint]
        elif self.options["endpoint"] is not None:
            option_endpoint = self.options["endpoint"]
            if isinstance(option_endpoint, Tag):
                return option_endpoint.endpoints
            if isinstance(option_endpoint, Endpoint):
                return [option_endpoint]
            raise ValueError("Invalid endpoint option")
        else:
            endpoints = Endpoint.find_all(scope=True)

        if not again:
            endpoints = [endpoint for endpoint in endpoints if not endpoint.reachable]

        return endpoints

    def enum_connect(self: "_Workspace", target: str | None = None, force: bool = False,
            unprobed: bool = False) -> "list[Connection]":
        if target is not None:
            if '@' not in target:
                host = Host.find_one(name=target)
                if host is not None:
                    conn = Connection.find_one(endpoint=host.closest_endpoint)
                    if conn is not None:
                        return [conn]
                raise ValueError("Supplied value doesn't match a known host or a connection string")

            auth, sep, endpoint_str = target.partition('@')
            if endpoint_str == "*":
                endpoints = Endpoint.find_all(scope=True)
            elif endpoint_str[0] == "!":
                tag = Tag(endpoint_str[1:])
                endpoints = tag.endpoints
            else:
                found_endpoint = Endpoint.find_one(ip_port=endpoint_str)
                if found_endpoint is None:
                    raise ValueError("Supplied endpoint isn't in workspace")
                endpoints = [found_endpoint]

            user_str, sep, cred_str = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            if user_str == "*":
                users = User.find_all(scope=True)
            else:
                found_user = User.find_one(name=user_str)
                if found_user is None:
                    raise ValueError("Supplied user isn't in workspace")
                users = [found_user]
            if cred_str == "*":
                creds = Creds.find_all(scope=True)
            else:
                if cred_str[0] == "#":
                    cred_str = cred_str[1:]
                found_cred = Creds.find_one(creds_id=cred_str)
                if found_cred is None:
                    raise ValueError("Supplied credentials aren't in workspace")
                creds = [found_cred]
            if len(endpoints)*len(users)*len(creds) == 1:
                return [Connection(endpoints[0], users[0], creds[0])]
        else:
            option_user = self.options["user"]
            if option_user is None:
                users = User.find_all(scope=True)
            elif isinstance(option_user, User):
                users = [option_user]
            else:
                raise ValueError("Invalid user option")
            option_endpoint = self.options["endpoint"]
            if isinstance(option_endpoint, Tag):
                endpoints = option_endpoint.endpoints
            elif option_endpoint is None:
                endpoints = Endpoint.find_all(scope=True)
            elif isinstance(option_endpoint, Endpoint):
                endpoints = [option_endpoint]
            else:
                raise ValueError("Invalid endpoint option")
            option_creds = self.options["creds"]
            if option_creds is None:
                creds = Creds.find_all(scope=True)
            elif isinstance(option_creds, Creds):
                creds = [option_creds]
            else:
                raise ValueError("Invalid creds option")
            if len(endpoints)*len(users)*len(creds) == 1:
                return [Connection(endpoints[0], users[0], creds[0])]

        ret = []
        for endpoint in endpoints:
            if not unprobed and not endpoint.reachable:
                continue
            for user in users:
                if len(creds) != 1:
                    working_connections = Connection.find_all(endpoint=endpoint, user=user)
                    if not force and working_connections:
                        print("Connection already found with user "+str(user)+" on endpoint "+str(endpoint)+", creds bruteforcing is disabled. Specify creds or use --force.")
                        continue
                for cred in creds:
                    conn = Connection(endpoint, user, cred)
                    if force:
                        ret.append(conn)
                    else:
                        if conn.id is None:
                            ret.append(conn)
        return ret

    def enum_run(self: "_Workspace", target: str | None = None) -> "list[Connection]":
        if target is not None:
            if '@' not in target:
                host = Host.find_one(name=target)
                if host is not None:
                    conn = Connection.find_one(endpoint=host.closest_endpoint)
                    if conn is not None:
                        return [conn]
                raise ValueError("Supplied value doesn't match a known host or a connection string")

            auth, sep, endpoint_str = target.partition('@')
            endpoint: "Endpoint | Tag | None"
            if endpoint_str == "*":
                endpoint = None
            elif endpoint_str[0] == "!":
                endpoint = Tag(endpoint_str[1:])
            else:
                endpoint = Endpoint.find_one(ip_port=endpoint_str)
                if endpoint is None:
                    raise ValueError("Supplied endpoint isn't in workspace")

            user_str, sep, cred_str = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            user: "User | None"
            if user_str == "*":
                user = None
            else:
                user = User.find_one(name=user_str)
                if user is None:
                    raise ValueError("Supplied user isn't in workspace")
            cred: "Creds | None"
            if cred_str == "*":
                cred = None
            else:
                if cred_str[0] == "#":
                    cred_str = cred_str[1:]
                cred = Creds.find_one(creds_id=cred_str)
                if cred is None:
                    raise ValueError("Supplied credentials aren't in workspace")
        else:
            option_user = self.options["user"]
            if not isinstance(option_user, User) and option_user is not None:
                raise ValueError("Invalid user option")
            user = option_user
            option_endpoint = self.options["endpoint"]
            if not isinstance(option_endpoint, (Endpoint, Tag)) and option_endpoint is not None:
                raise ValueError("Invalid endpoint option")
            endpoint = option_endpoint
            option_creds = self.options["creds"]
            if not isinstance(option_creds, Creds) and option_creds is not None:
                raise ValueError("Invalid creds option")
            cred = option_creds

        return Connection.find_all(endpoint=endpoint, user=user, creds=cred)


    def run(self: "_Workspace", targets: "list[Connection]", payload: object, stmt: object,
            verbose: bool = False) -> None:
        """Run a payload on a list of :class:`Connection`

        Args:
            targets ([:class:`Connection`]): the target list
            payload (:class:`Payload`): the payload to run
            stmt (`argparse.Namespace`): the command parameters to pass to the payload
        """

        for connection in targets:
            if not connection.endpoint.reachable:
                raise NoPathError

            connection.run(payload, self.workspace_folder, stmt, verbose=verbose)

    def connect(self: "_Workspace", targets: "list[Connection]", verbose: bool = False,
            probe_auto: bool = False) -> int:
        nb_working = 0
        for connection in targets:
            if not connection.endpoint.reachable:
                if probe_auto:
                    self.probe([connection.endpoint], verbose=verbose)
                    if not connection.endpoint.reachable:
                        print("\033[1;31mError\033[0m: could not find path to the target.")
                        continue
                else:
                    print("\033[1;31mError\033[0m: could not find path to the target.")
                    continue
            if connection.open(verbose=verbose, target=True):
                nb_working = nb_working + 1
        return nb_working
