import hashlib
import socket
from typing import Literal, Self
import paramiko
from baboossh import Db, Endpoint, User, Creds, Path, Host, Tag, Tunnel
from baboossh.exceptions import *
from baboossh.utils import Unique
import select

__all__ = ["Connection"]

DIRECT_TIMEOUT = 3
RELAY_TIMEOUT = 8

class Connection(metaclass=Unique):
    """A :class:`User` and :class:`Creds` to authenticate on an :class:`Endpoint`

    A connection represents the working association of those 3 objects to connect
    a target. It can be used to run payloads on a :class:`Host`, open a
    :class:`Tunnel` to it or use it as a pivot to reach new :class:`Endpoint` s

    Attributes:
        endpoint (:class:`Endpoint`): the `Connection` 's endpoint
        user (:class:`User`): the `Connection` 's user
        creds (:class:`Creds`): the `Connection` 's credentials
        id (int): the `Connection` 's id
        used_by_connections ([Connection,...]): a list of :class:`Connection`
            using the current one as a pivot. Used for recursive connection
            closure.
        used_by_tunnels ([Tunnel,...]): a list of :class:`Tunnel`
            using the current connection as a pivot. Used for recursive connection
            closure.
    """


    def __init__(self, endpoint: Endpoint, user: "User | None", cred: "Creds | None") -> None:
        """Create the object and fetches info from database if it has been saved.
        
        Args:
            endpoint (:class:`Endpoint`): The Connection's endpoint
            user (:class:`User`): The Connection's user
            cred (:class:`Creds`): The Connection's credentials
        """

        self.endpoint = endpoint
        self.user = user
        self.creds = cred
        self.id = None
        self.root = False
        self.sock: socket.socket | paramiko.Channel | None = None
        self.transport: paramiko.Transport | None = None
        self.used_by_connections: list[Self] = []
        self.used_by_tunnels: list[Tunnel] = []
        if user is None or cred is None:
            return
        cursor = Db.get().cursor()
        cursor.execute('SELECT id, root FROM connections WHERE endpoint=? AND user=? AND cred=?', (self.endpoint.id, user.id, cred.id))
        saved_connection = cursor.fetchone()
        cursor.close()
        if saved_connection is not None:
            self.id = saved_connection[0]
            self.root = saved_connection[1] != 0

    @classmethod
    def get_id(cls, endpoint: Endpoint, user: "User | None", cred: "Creds | None") -> str:
        """Generate an ID for unicity

        Args: See __init__

        Returns:
            A str corresponding to the Connection hash
        """
        return hashlib.sha256((str(endpoint)+str(user)+str(cred)).encode()).hexdigest()

    @property
    def scope(self) -> bool:
        """Returns whether the `Connection` is in scope

        The `Connection` is in scope if its :class:`User`, its :class:`Creds`
        AND it :class:`Endpoint` are all in scope
        """

        if self.user is None or self.creds is None:
            return False
        return self.user.scope and self.endpoint.scope and self.creds.scope

    @property
    def distance(self) -> int | None:
        """Returns the number of hops between `"Local"` and the :class:`Endpoint`"""
        return self.endpoint.distance

    def save(self) -> None:
        """Save the `Connection` to the :class:`Workspace`'s database"""

        if self.user is None or self.creds is None:
            return
        cursor = Db.get().cursor()
        if self.id is not None:
            #If we have an ID, the endpoint is already saved in the database : UPDATE
            cursor.execute('''UPDATE connections
                SET
                    endpoint= ?,
                    user = ?,
                    cred = ?,
                    root = ?
                WHERE id = ?''',
                           (self.endpoint.id, self.user.id, self.creds.id, self.root, self.id))
        else:
            #The endpoint doesn't exists in database : INSERT
            cursor.execute('''INSERT INTO connections(endpoint, user, cred, root)
                VALUES (?, ?, ?, ?) ''',
                           (self.endpoint.id, self.user.id, self.creds.id, self.root))
            cursor.close()
            cursor = Db.get().cursor()
            cursor.execute('SELECT id FROM connections WHERE endpoint=? AND user=? AND cred=?', (self.endpoint.id, self.user.id, self.creds.id))
            self.id = cursor.fetchone()[0]
        cursor.close()
        Db.get().commit()

    def delete(self) -> dict[str, list[str]]:
        """Delete the `Connection` from the :class:`Workspace`'s database"""

        if self.id is None:
            return {}
        cursor = Db.get().cursor()
        cursor.execute('DELETE FROM connections WHERE id = ?', (self.id, ))
        cursor.close()
        Db.get().commit()
        return {"Connection":[type(self).get_id(self.endpoint, self.user, self.creds)]}


    @classmethod
    def find_one(cls, connection_id: int | None = None, endpoint: "Endpoint | None" = None, scope: bool | None = None, gateway_to: "Endpoint | None" = None) -> Self | None:
        """Find a `Connection` by its id, endpoint or if it can be used as a gateway to an :class:`Endpoint`

        Args:
            connection_id (int): the `Connection` id to search
            endpoint (:class:`Endpoint`): the `Connection` endpoint to search
            gateway_to (:class:`Endpoint`): the Endpoint to which you want to find a gateway
            scope (bool): whether to include only in scope Connections (`True`), out of scope Connections (`False`) or both (`None`)

        Returns:
            A single `Connection` or `None`.
        """

        if gateway_to is not None:
            if gateway_to.distance is not None and gateway_to.distance == 0:
                return None
            try:
                closest_host = Host.find_one(prev_hop_to=gateway_to)
            except NoPathError as exc:
                raise exc
            if closest_host is None:
                return None
            return cls.find_one(endpoint=closest_host.closest_endpoint, scope=True)

        cursor = Db.get().cursor()
        if connection_id is not None:
            req = cursor.execute('SELECT endpoint, user, cred FROM connections WHERE id=?', (connection_id, ))
        elif endpoint is not None:
            req = cursor.execute('SELECT endpoint, user, cred FROM connections WHERE endpoint=? ORDER BY root ASC', (endpoint.id, ))
        else:
            cursor.close()
            return None
        if scope is None:
            row = cursor.fetchone()
            cursor.close()
            if row is None:
                return None
            row_endpoint = Endpoint.find_one(endpoint_id=row[0])
            assert row_endpoint is not None
            return cls(row_endpoint, User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
        for row in req:
            row_endpoint = Endpoint.find_one(endpoint_id=row[0])
            assert row_endpoint is not None
            conn = cls(row_endpoint, User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
            if scope == conn.scope:
                cursor.close()
                return conn
        cursor.close()
        return None


    @classmethod
    def find_all(cls, endpoint: "Endpoint | Tag | None" = None, user: "User | None" = None, creds: "Creds | None" = None, scope: bool | None = None) -> list[Self]:
        """Find all `Connection` matching the criteria

        If two or more arguments are specified, the returned Connections must match each ("AND")

        Args:
            endpoint (:class:`Endpoint` or :class:`Tag`): the `Connection` endpoint to search or a :class:`Tag` of endpoints to search
            user (:class:`User`): the `Connection` user to search
            creds (:class:`Creds`): the `Connection` creds to search
            scope (bool): whether to include only in scope Connections (`True`), out of scope Connections (`False`) or both (`None`)

        Returns:
            A list of matching `Connection`.
        """


        ret: list[Self] = []
        cursor = Db.get().cursor()

        query = 'SELECT endpoint, user, cred FROM connections'
        params = []
        first = True
        if endpoint is not None and not isinstance(endpoint, Tag):
            if first:
                query = query + ' WHERE '
                first = False
            else:
                query = query + ' AND '
            query = query + 'endpoint=?'
            params.append(endpoint.id)
        elif endpoint is not None and isinstance(endpoint, Tag):
            if first:
                query = query + ' WHERE ('
                first = False
            else:
                query = query + ' AND ('
            first_endpoint = True
            for end in endpoint.endpoints:
                if end is None:
                    continue
                if not first_endpoint:
                    query = query + ' OR '
                else:
                    first_endpoint = False
                query = query + 'endpoint=?'
                params.append(end.id)
            query = query + ' )'
        if user is not None:
            if first:
                query = query + ' WHERE '
                first = False
            else:
                query = query + ' AND '
            query = query + 'user=?'
            params.append(user.id)
        if creds is not None:
            if first:
                query = query + ' WHERE '
                first = False
            else:
                query = query + ' AND '
            query = query + 'cred=?'
            params.append(creds.id)

        req = cursor.execute(query, tuple(params))

        for row in req:
            row_endpoint = Endpoint.find_one(endpoint_id=row[0])
            assert row_endpoint is not None
            conn = cls(row_endpoint, User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
            if scope is None or conn.scope == scope:
                ret.append(conn)
        cursor.close()
        return ret

    @classmethod
    def from_target(cls, arg: str) -> Self | None:
        if '@' in arg and ':' in arg:
            auth, sep, endpoint_str = arg.partition('@')
            endpoint = Endpoint.find_one(ip_port=endpoint_str)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            user_str, sep, cred_str = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            user = User.find_one(name=user_str)
            if user is None:
                raise ValueError("Supplied user isn't in workspace")
            if cred_str[0] == "#":
                cred_str = cred_str[1:]
            cred = Creds.find_one(creds_id=cred_str)
            if cred is None:
                raise ValueError("Supplied credentials aren't in workspace")
            return cls(endpoint, user, cred)
        if ':' not in arg:
            host = Host.find_one(name=arg)
            if host is not None:
                return cls.find_one(endpoint=host.closest_endpoint)
            arg = arg+':22'
        endpoint = Endpoint.find_one(ip_port=arg)
        if endpoint is None:
            raise ValueError("Supplied endpoint isn't in workspace")
        connection = cls.find_one(endpoint=endpoint)
        if connection is None:
            raise ValueError("No working connection for supplied endpoint")
        return connection
    
    def identify(self) -> bool:
        """Identify the host"""
        assert self.transport is not None
        try:
            serverKey = self.transport.get_remote_server_key()
            print(serverKey.asbytes())
            c,result = self.exec_command("hostname")
            if c != 0:
                print("\t>Unable to get hostname. You can change the host name later using \"host edit\".")
                hostname = ""
            else:
                hostname = result.rstrip()
            c,result = self.exec_command("uname -a")
            uname = result.rstrip()
            c,result = self.exec_command("cat /etc/issue")
            issue = result.rstrip()
            c,result = self.exec_command("cat /etc/machine-id")
            machine_id = result.rstrip()
            c,result = self.exec_command("for i in `ls -l /sys/class/net/ | grep -v virtual | grep 'devices' | tr -s '[:blank:]' | cut -d ' ' -f 9 | sort`; do ip l show $i | grep ether | tr -s '[:blank:]' | cut -d ' ' -f 3; done")
            mac_str = result.rstrip()
            macs = mac_str.split()
        except Exception as exc:
            print("Error trying to identify: "+str(exc))
            return False
        try:
            new_host = Host(hostname, uname, issue, machine_id, macs)
            if new_host.id is None:
                print("\t"+str(self)+" is a new host: " + new_host.name)
            else:
                print("\t"+str(self)+" is an existing host: " + new_host.name)
                if not new_host.scope:
                    self.endpoint.scope = False
            new_host.save()
            self.endpoint.host = new_host
            self.endpoint.save()
        except Exception as exc:
            print("Error creating host : "+str(exc))
            return False
        return True

    def open_transport(self, gateway: "Literal['auto'] | Connection | None" = "auto") -> "tuple[socket.socket | paramiko.Channel, paramiko.Transport, Connection | None]":
        #TODO check verbosity levels
        if gateway == "auto":
            gateway = Connection.find_one(gateway_to=self.endpoint)
        if gateway is not None:
            if not gateway.open(verbose=False):
                raise ConnectionClosedError("Could not open gateway "+str(gateway))
            assert gateway.transport is not None
            sock = gateway.transport.open_channel('direct-tcpip', (self.endpoint.ip, self.endpoint.port), ('', 0), timeout=RELAY_TIMEOUT);
        else:
            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.settimeout(DIRECT_TIMEOUT)
            sock.connect((self.endpoint.ip,self.endpoint.port))

        transport = paramiko.Transport(sock)
        try:
            transport.start_client()
        except Exception:
            sock.close()
            raise
        return (sock,transport, gateway)

    def probe(self, gateway: "Literal['auto'] | Connection | None" = "auto", verbose: bool = True) -> bool:
        if gateway is not None:
            if gateway == "auto":
                gateway = Connection.find_one(gateway_to=self.endpoint)
        try:
            sock, transport, gateway = self.open_transport(gateway=gateway);
        except (TimeoutError, OSError, ConnectionRefusedError, ConnectionClosedError, paramiko.SSHException) as err:
            return False
        self.endpoint.reachable = True
        if gateway is None:
            new_distance: int | None = 1
        elif gateway.endpoint.distance is not None:
            new_distance = gateway.endpoint.distance + 1
        else:
            new_distance = None
        if new_distance is not None and (self.endpoint.distance is None or self.endpoint.distance > new_distance):
            self.endpoint.distance = new_distance
        self.endpoint.save()
        transport.close()
        sock.close()
        return True

    def exec_command(self, command: str) -> tuple[int, str]:
        if self.transport is None:
            raise ConnectionClosedError("Connection is closed, cannot execute command")
        try:
            chan = self.transport.open_session()
            chan.get_pty()
            chan.exec_command(command)
            output = ""
            while True:
                if chan.recv_ready():
                    output = output+chan.recv(1024).decode("utf-8")
                    continue
                if chan.exit_status_ready():
                    while chan.recv_ready():
                        output = output+chan.recv(1024).decode("utf-8")
                    break
                select.select([chan], [], [], 0.1)
            return_code = chan.recv_exit_status()
        except Exception as e:
            raise
        return (return_code,output)


    def open(self, verbose: bool = False, target: bool = False) -> bool:
        if self.transport is not None:
            if not self.transport.is_active():
                print("Connection to \033[1;34m"+str(self)+"\033[0m went inactive, Closing... ", end="", flush=True)
                self.close()
            else:
                if target:
                    print("Connection to \033[1;34m"+str(self)+"\033[0m already open. > \033[1;32mOK\033[0m")
                return True

        if target:
            print("Connecting to \033[1;34m"+str(self)+"\033[0m... ", end="", flush=True)
        try:
            sock, transport, gateway = self.open_transport();
        except (TimeoutError, OSError, ConnectionRefusedError) as err:
            if target:
                print("\033[1;31mKO\033[0m. Could not reach destination.")
            return False
        except ConnectionClosedError as err:
            if target:
                print("\033[1;31mKO\033[0m.")
                print(err, "- Please try probe-ing another path")
            return False
        except paramiko.SSHException as err:
            if target:
                print("\033[1;31mKO\033[0m. Network error: "+str(err))
            return False

        assert self.user is not None and self.creds is not None
        try:
            self.creds.auth(username=self.user.name, transport=transport)
        except paramiko.BadAuthenticationType:
            if target:
                print("\033[1;31mKO\033[0m. Authentication method not allowed.")
            return False
        except paramiko.AuthenticationException:
            if target:
                print("\033[1;31mKO\033[0m. Authentication failed.")
            return False
        except paramiko.SSHException as err:
            if target:
                print("\033[1;31mKO\033[0m. Network error: "+str(err))
            return False

        if target:
            print("\033[1;32mOK\033[0m")
        elif verbose:
            print("\033[2;3m"+str(self)+"\033[22;23m > ", end="", flush=True)
        
        if gateway is None:
            path_src = None
        else:
            gateway.used_by_connections.append(self)
            if gateway.endpoint.host is not None:
                path_src = gateway.endpoint.host
            else:
                raise NoHostError("Gateway "+str(gateway)+" has no identified Host")
        path = Path(path_src, self.endpoint)
        path.save()
        self.save()

        self.transport = transport
        self.sock = sock

        if target:
            if self.endpoint.host is None:
                self.identify()
                pass
        return True

    def run(self, payload, current_workspace_directory: str, stmt, verbose: bool = False) -> bool:
        if not self.open(target=True, verbose=verbose):
            return False
        payload.run(self, current_workspace_directory, stmt)
        return True

    def close(self) -> None:
        if self.transport is None:
            return
        nb_tunnels = len(self.used_by_tunnels)
        if nb_tunnels != 0:
            print(str(nb_tunnels)+" tunnel(s) are open using this connection, please close tunnels first.")
            return
        for connection in self.used_by_connections:
            connection.close()
        self.transport.close()
        self.transport = None
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        print("Closed "+str(self))

    def __str__(self) -> str:
        return str(self.user)+":"+str(self.creds)+"@"+str(self.endpoint)
