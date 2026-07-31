from baboossh import Connection, Creds, Endpoint, Host, Tag, User
from baboossh.exceptions import NoPathError


class ConnectionsMixin:
    """`Workspace` methods for managing `Connection` objects, and enumerating targets."""

    def connection_close(self, target):
        """Close a :class:`Connection` and any connection or tunnel using it

        Args:
            target (str): the `Connection` string
        """

        connection = Connection.from_target(target)
        if connection is None:
            print("Connection not found.")
            return False
        return connection.close()

    def connection_del(self, target):
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

    def enum_probe(self, target=None, again=False):
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
            if isinstance(self.options["endpoint"], Tag):
                return self.options["endpoint"].endpoints
            return [self.options["endpoint"]]
        else:
            endpoints = Endpoint.find_all(scope=True)

        if not again:
            endpoints = [endpoint for endpoint in endpoints if not endpoint.reachable]

        return endpoints

    def enum_connect(self, target=None, force=False, unprobed=False):
        if target is not None:
            if '@' not in target:
                host = Host.find_one(name=target)
                if host is not None:
                    conn = Connection.find_one(endpoint=host.closest_endpoint)
                    if conn is not None:
                        return [conn]
                raise ValueError("Supplied value doesn't match a known host or a connection string")

            auth, sep, endpoint = target.partition('@')
            if endpoint == "*":
                endpoints = Endpoint.find_all(scope=True)
            elif endpoint[0] == "!":
                tag = Tag(endpoint[1:])
                endpoints = tag.endpoints
            else:
                endpoint = Endpoint.find_one(ip_port=endpoint)
                if endpoint is None:
                    raise ValueError("Supplied endpoint isn't in workspace")
                endpoints = [endpoint]

            user, sep, cred = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            if user == "*":
                users = User.find_all(scope=True)
            else:
                user = User.find_one(name=user)
                if user is None:
                    raise ValueError("Supplied user isn't in workspace")
                users = [user]
            if cred == "*":
                creds = Creds.find_all(scope=True)
            else:
                if cred[0] == "#":
                    cred = cred[1:]
                cred = Creds.find_one(creds_id=cred)
                if cred is None:
                    raise ValueError("Supplied credentials aren't in workspace")
                creds = [cred]
            if len(endpoints)*len(users)*len(creds) == 1:
                return [Connection(endpoints[0], users[0], creds[0])]
        else:
            user = self.options["user"]
            if user is None:
                users = User.find_all(scope=True)
            else:
                users = [user]
            endpoint = self.options["endpoint"]
            if isinstance(endpoint, Tag):
                endpoints = endpoint.endpoints
            elif endpoint is None:
                endpoints = Endpoint.find_all(scope=True)
            else:
                endpoints = [endpoint]
            cred = self.options["creds"]
            if cred is None:
                creds = Creds.find_all(scope=True)
            else:
                creds = [cred]
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

    def enum_run(self, target=None):
        if target is not None:
            if '@' not in target:
                host = Host.find_one(name=target)
                if host is not None:
                    conn = Connection.find_one(endpoint=host.closest_endpoint)
                    if conn is not None:
                        return [conn]
                raise ValueError("Supplied value doesn't match a known host or a connection string")

            auth, sep, endpoint = target.partition('@')
            if endpoint == "*":
                endpoint = None
            elif endpoint[0] == "!":
                tag = Tag(endpoint[1:])
                endpoints = tag.endpoints
            else:
                endpoint = Endpoint.find_one(ip_port=endpoint)
                if endpoint is None:
                    raise ValueError("Supplied endpoint isn't in workspace")

            user, sep, cred = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            if user == "*":
                user = None
            else:
                user = User.find_one(name=user)
                if user is None:
                    raise ValueError("Supplied user isn't in workspace")
            if cred == "*":
                cred = None
            else:
                if cred[0] == "#":
                    cred = cred[1:]
                cred = Creds.find_one(creds_id=cred)
                if cred is None:
                    raise ValueError("Supplied credentials aren't in workspace")
        else:
            user = self.options["user"]
            endpoint = self.options["endpoint"]
            cred = self.options["creds"]

        return Connection.find_all(endpoint=endpoint, user=user, creds=cred)


    def run(self, targets, payload, stmt, verbose=False):
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

    def connect(self, targets, verbose=False, probe_auto=False):
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
