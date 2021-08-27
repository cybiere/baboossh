import hashlib
import paramiko
import fabric
from baboossh import Db, Endpoint, User, Creds, Path, Host, Tag
from baboossh.exceptions import *
from baboossh.utils import Unique
import socket

try:
    from invoke.vendor.six import string_types
except ImportError:
    from six import string_types

def monkey_open_gateway(self):
    """
    This is a monkey patch of fabric.Connection.open_gateway which simply
    forwards the timeout to the call on open_channel
    """

    if isinstance(self.gateway, string_types):
        ssh_conf = SSHConfig()
        dummy = "Host {}\n    ProxyCommand {}"
        ssh_conf.parse(StringIO(dummy.format(self.host, self.gateway)))
        return ProxyCommand(ssh_conf.lookup(self.host)["proxycommand"])
    self.gateway.open()
    return self.gateway.transport.open_channel(
        kind="direct-tcpip",
        dest_addr=(self.host, int(self.port)),
        src_addr=("", 0),
        timeout=self.connect_timeout
    )

fabric.Connection.open_gateway = monkey_open_gateway

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


    def __init__(self, endpoint, user, cred):
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
        self.conn = None
        self.used_by_connections = []
        self.used_by_tunnels = []
        if user is None or cred is None:
            return
        cursor = Db.get().cursor()
        cursor.execute('SELECT id, root FROM connections WHERE endpoint=? AND user=? AND cred=?', (self.endpoint.id, self.user.id, self.creds.id))
        saved_connection = cursor.fetchone()
        cursor.close()
        if saved_connection is not None:
            self.id = saved_connection[0]
            self.root = saved_connection[1] != 0

    @classmethod
    def get_id(cls, endpoint, user, cred):
        """Generate an ID for unicity
        
        Args: See __init__

        Returns:
            A str corresponding to the Connection hash
        """
        return hashlib.sha256((str(endpoint)+str(user)+str(cred)).encode()).hexdigest()

    @property
    def scope(self):
        """Returns whether the `Connection` is in scope

        The `Connection` is in scope if its :class:`User`, its :class:`Creds`
        AND it :class:`Endpoint` are all in scope
        """

        return self.user.scope and self.endpoint.scope and self.creds.scope

    @property
    def distance(self):
        """Returns the number of hops between `"Local"` and the :class:`Endpoint`"""
        return self.endpoint.distance

    def save(self):
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

    def delete(self):
        """Delete the `Connection` from the :class:`Workspace`'s database"""

        if self.id is None:
            return {}
        cursor = Db.get().cursor()
        cursor.execute('DELETE FROM connections WHERE id = ?', (self.id, ))
        cursor.close()
        Db.get().commit()
        return {"Connection":[type(self).get_id(self.endpoint, self.user, self.creds)]}


    @classmethod
    def find_one(cls, connection_id=None, endpoint=None, scope=None, gateway_to=None):
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
            return Connection(Endpoint.find_one(endpoint_id=row[0]), User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
        for row in req:
            conn = Connection(Endpoint.find_one(endpoint_id=row[0]), User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
            if scope == conn.scope:
                cursor.close()
                return conn
        cursor.close()
        return None


    @classmethod
    def find_all(cls, endpoint=None, user=None, creds=None, scope=None):
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


        ret = []
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
            conn = Connection(Endpoint.find_one(endpoint_id=row[0]), User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
            if scope is None or conn.scope == scope:
                ret.append(conn)
        cursor.close()
        return ret

    @classmethod
    def from_target(cls, arg):
        if '@' in arg and ':' in arg:
            auth, sep, endpoint = arg.partition('@')
            endpoint = Endpoint.find_one(ip_port=endpoint)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            user, sep, cred = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            user = User.find_one(name=user)
            if user is None:
                raise ValueError("Supplied user isn't in workspace")
            if cred[0] == "#":
                cred = cred[1:]
            cred = Creds.find_one(creds_id=cred)
            if cred is None:
                raise ValueError("Supplied credentials aren't in workspace")
            return Connection(endpoint, user, cred)

        if ':' not in arg:
            arg = arg+':22'
        endpoint = Endpoint.find_one(ip_port=arg)
        if endpoint is None:
            raise ValueError("Supplied endpoint isn't in workspace")
        connection = cls.find_one(endpoint=endpoint)
        if connection is None:
            raise ValueError("No working connection for supplied endpoint")
        return connection

    def identify(self, socket):
        """Indentify the host"""
        try:
            result = socket.run("hostname", hide='both', warn = True)
            hostname = result.stdout.rstrip()
            result = socket.run("uname -a", hide='both', warn = True)
            uname = result.stdout.rstrip()
            result = socket.run("cat /etc/issue", hide='both', warn = True)
            issue = result.stdout.rstrip()
            result = socket.run("cat /etc/machine-id", hide='both', warn = True)
            machine_id = result.stdout.rstrip()
            result = socket.run("for i in `ls -l /sys/class/net/ | grep -v virtual | grep 'devices' | tr -s '[:blank:]' | cut -d ' ' -f 9 | sort`; do ip l show $i | grep ether | tr -s '[:blank:]' | cut -d ' ' -f 3; done", hide='both', warn = True)
            mac_str = result.stdout.rstrip()
            macs = mac_str.split()
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
            print("Error : "+str(exc))
            return False
        return True

    def probe(self, gateway="auto", verbose=True):
        if verbose:
            print("Reaching \033[1;34m"+str(self.endpoint)+"\033[0m > ", end="", flush=True)
        if gateway is not None:
            if gateway == "auto":
                gateway = Connection.find_one(gateway_to=self.endpoint)
                if gateway is not None:
                    if not gateway.open(verbose=False):
                        raise ConnectionClosedError("Could not open gateway "+str(gateway))
                    gw = gateway.conn
                else:
                    gw = None
            else:
                if not gateway.open(verbose=False):
                    raise ConnectionClosedError("Could not open gateway "+str(gateway))
                gw = gateway.conn
        else:
            gw = None

        paramiko_args = {'look_for_keys':False, 'allow_agent':False}

        conn = fabric.Connection(host=self.endpoint.ip, port=self.endpoint.port, user="user", connect_kwargs=paramiko_args, gateway=gw, connect_timeout=3)
        try:
            conn.open()
        except paramiko.ssh_exception.NoValidConnectionsError:
            if verbose:
                print("\033[1;31mKO\033[0m.")
            return False
        except paramiko.ssh_exception.ChannelException:
            if verbose:
                print("\033[1;31mKO\033[0m.")
            return False
        except paramiko.ssh_exception.SSHException as exc:
            if "Timeout" in str(exc) or "Error reading SSH protocol banner" in str(exc):
                if verbose:
                    print("\033[1;31mKO\033[0m.")
                return False
            if "No existing session" in str(exc):
                if verbose:
                    print("\033[1;31mKO\033[0m. No matching cipher")
                return False
            if "No authentication methods available" in str(exc):
                pass
            else:
                raise exc
        except socket.timeout:
            if verbose:
                print("\033[1;31mKO\033[0m.")
            return False

        if conn is not None:
            conn.close()

        if verbose:
            print("\033[1;32mOK\033[0m")

        self.endpoint.reachable = True
        new_distance = 1 if gw is None else gateway.endpoint.distance + 1
        if self.endpoint.distance is None or self.endpoint.distance > new_distance:
            self.endpoint.distance = new_distance
        self.endpoint.save()
        return True

    def open(self, verbose=False, target=False):
        if self.conn is not None:
            if target:
                print("Connection to \033[1;34m"+str(self)+"\033[0m already open. > \033[1;32mOK\033[0m")
            return True

        hostname = ""
        if self.endpoint.host is not None:
            hostname = " ("+str(self.endpoint.host)+")"
        if target:
            print("Connecting to \033[1;34m"+str(self)+"\033[0m"+hostname+" > ", end="", flush=True)

        gateway = Connection.find_one(gateway_to=self.endpoint)
        if gateway is not None:
            if not gateway.open(verbose=verbose):
                raise ConnectionClosedError("Could not open gateway "+str(gateway))
            gw = gateway.conn
        else:
            gw = None

        try:
            paramiko_args = {**self.creds.kwargs, 'look_for_keys':False, 'allow_agent':False}
        except ValueError as exc:
            if target:
                print("\033[1;31mKO\033[0m. "+str(exc))
            return False
        conn = fabric.Connection(host=self.endpoint.ip, port=self.endpoint.port, user=self.user.name, connect_kwargs=paramiko_args, gateway=gw, connect_timeout=3)
        try:
            conn.open()
        except paramiko.ssh_exception.NoValidConnectionsError:
            if target:
                print("\033[1;31mKO\033[0m. Could not reach destination.")
            if gw is not None:
                #TODO remove path
                pass
            return False
        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException) as exc:
            if isinstance(exc, paramiko.ssh_exception.AuthenticationException) or "encountered" in str(exc):
                if target:
                    print("\033[1;31mKO\033[0m. Authentication failed.")
                return False
            raise exc
        except socket.timeout:
            if verbose:
                print("\033[1;31mKO\033[0m. Could not open socket to "+str(self.endpoint))
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
                raise NoHostError
        path = Path(path_src, self.endpoint)
        path.save()
        self.save()

        if target:
            if self.endpoint.host is None:
                self.identify(conn)

        self.conn = conn

        return True

    def run(self, payload, current_workspace_directory, stmt, verbose=False):
        if not self.open(target=True, verbose=verbose):
            return False
        payload.run(self, current_workspace_directory, stmt)
        return True

    def close(self):
        if self.conn is None:
            return
        nb_tunnels = len(self.used_by_tunnels)
        if nb_tunnels != 0:
            print(str(nb_tunnels)+" tunnel(s) are open using this connection, please close tunnels first.")
            return
        for connection in self.used_by_connections:
            connection.close()
        self.conn.close()
        self.conn = None
        print("Closed "+str(self))

    def __str__(self):
        return str(self.user)+":"+str(self.creds)+"@"+str(self.endpoint)
