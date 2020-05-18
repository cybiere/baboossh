import sqlite3
import hashlib
import fabric, paramiko, sys
from baboossh import Db, Extensions, Endpoint, User, Creds, Path, Host
from baboossh.exceptions import *
from baboossh.utils import Unique

try:
    from invoke.vendor.six import string_types
except ImportError:
    from six import string_types

def monkey_open_gateway(self):
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
    """


    def __init__(self, endpoint, user, cred):
        self.endpoint = endpoint
        self.user = user
        self.creds = cred
        self.id = None
        self.root = False
        self.conn = None
        self.gateway = None
        if user is None or cred is None:
            return
        c = Db.get().cursor()
        c.execute('SELECT id, root FROM connections WHERE endpoint=? AND user=? AND cred=?', (self.endpoint.id, self.user.id, self.creds.id))
        savedConnection = c.fetchone()
        c.close()
        if savedConnection is not None:
            self.id = savedConnection[0]
            self.root = savedConnection[1] != 0

    @classmethod
    def get_id(cls, endpoint, user, cred):
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
        if self.user is None or self.creds is None:
            return
        """Save the `Connection` to the :class:`Workspace` 's database"""
        c = Db.get().cursor()
        if self.id is not None:
            #If we have an ID, the endpoint is already saved in the database : UPDATE
            c.execute('''UPDATE connections 
                SET
                    endpoint= ?,
                    user = ?,
                    cred = ?,
                    root = ?
                WHERE id = ?''',
                (self.endpoint.id, self.user.id, self.creds.id, self.root, self.id))
        else:
            #The endpoint doesn't exists in database : INSERT
            c.execute('''INSERT INTO connections(endpoint, user, cred, root)
                VALUES (?, ?, ?, ?) ''',
                (self.endpoint.id, self.user.id, self.creds.id, self.root ))
            c.close()
            c = Db.get().cursor()
            c.execute('SELECT id FROM connections WHERE endpoint=? AND user=? AND cred=?', (self.endpoint.id, self.user.id, self.creds.id))
            self.id  = c.fetchone()[0]
        c.close()
        Db.get().commit()

    def delete(self):
        """Delete the `Connection` from the :class:`Workspace` 's database"""
        if self.id is None:
            return
        c = Db.get().cursor()
        c.execute('DELETE FROM connections WHERE id = ?', (self.id, ))
        c.close()
        Db.get().commit()
        return {"Connection":[type(self).get_id(self.endpoint, self.user, self.creds)]}


    @classmethod
    def find_one(cls, connection_id=None, endpoint=None, scope=None, gateway_to=None):
        """Find a `Connection` by its id or endpoint

        Args:
            connection_id (int): the `Connection` id to search
            endpoint (:class:`Endpoint`): the `Connection` endpoint to search
            gateway_to (:class:`Endpoint`): the `Connection` to use as a gateway to the endpoint

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

        c = Db.get().cursor()
        if connection_id is not None:
            req = c.execute('SELECT endpoint, user, cred FROM connections WHERE id=?', (connection_id, ))
        elif endpoint is not None:
            req = c.execute('SELECT endpoint, user, cred FROM connections WHERE endpoint=? ORDER BY root ASC', (endpoint.id, ))
        else:
            c.close()
            return None
        if scope is None:
            row = c.fetchone()
            c.close()
            if row is None:
                return None
            return Connection(Endpoint.find_one(endpoint_id=row[0]), User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
        for row in req:
            conn = Connection(Endpoint.find_one(endpoint_id=row[0]), User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
            if scope == conn.scope:
               c.close()
               return conn
        c.close()
        return None


    @classmethod
    def find_all(cls, endpoint=None, user=None, creds=None, scope=None):
        ret = []
        c = Db.get().cursor()

        query = 'SELECT endpoint, user, cred FROM connections'
        params = []
        first = True
        if endpoint is not None:
            if first:
                query = query + ' WHERE '
                first = False
            else:
                query = query + ' AND '
            query = query + 'endpoint=?'
            params.append(endpoint.id)
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

        req = c.execute(query, tuple(params))
        
        for row in req:
            conn = Connection(Endpoint.find_one(endpoint_id=row[0]), User.find_one(user_id=row[1]), Creds.find_one(creds_id=row[2]))
            if scope is None or conn.scope == scope:
                ret.append(conn)
        c.close()
        return ret

    @classmethod
    def fromTarget(cls, arg):
        if '@' in arg and ':' in arg:
            auth, sep, endpoint = arg.partition('@')
            endpoint  = Endpoint.find_one(ip_port=endpoint)
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
        else:    
            if ':' not in arg:
                arg = arg+':22'
            endpoint = Endpoint.find_one(ip_port=arg)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            connection = cls.find_one(endpoint=endpoint)
            if connection == None:
                raise ValueError("No working connection for supplied endpoint")
            return connection
        return None

    def identify(self, socket):
        try:
            result = socket.run("hostname", hide='both')
            hostname = result.stdout.rstrip()
            result = socket.run("uname -a", hide='both')
            uname = result.stdout.rstrip()
            result = socket.run("cat /etc/issue", hide='both')
            issue = result.stdout.rstrip()
            result = socket.run("cat /etc/machine-id", hide='both')
            machineId = result.stdout.rstrip()
            result = socket.run("for i in `ls -l /sys/class/net/ | grep -v virtual | grep 'devices' | tr -s '[:blank:]' | cut -d ' ' -f 9 | sort`; do ip l show $i | grep ether | tr -s '[:blank:]' | cut -d ' ' -f 3; done", hide='both')
            macStr = result.stdout.rstrip()
            macs = macStr.split()
            new_host = Host(hostname, uname, issue, machineId, macs)
            if new_host.id is None:
                print("\t"+str(self)+" is a new host: " + new_host.name)
            else:
                print("\t"+str(self)+" is an existing host: " + new_host.name)
                if not new_host.scope:
                    self.endpoint.scope = False
            new_host.save()
            self.endpoint.host = new_host
            self.endpoint.save()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True

    def probe(self, gateway="auto"):
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

        print("Reaching \033[1;34m"+str(self.endpoint)+"\033[0m > ", end="")
        conn = fabric.Connection(host=self.endpoint.ip, port=self.endpoint.port, user="user", connect_kwargs=paramiko_args, gateway=gw, connect_timeout=3)
        try:
            conn.open()
        except paramiko.ssh_exception.NoValidConnectionsError:
            print("\033[1;31mKO\033[0m.")
            if gw is not None:
                gw.close()
            return False
        except paramiko.ssh_exception.ChannelException:
            print("\033[1;31mKO\033[0m.")
            if gw is not None:
                gw.close()
            return False
        except paramiko.ssh_exception.SSHException as e:
            if "Timeout" in str(e):
                print("\033[1;31mKO\033[0m.")
                if gw is not None:
                    gw.close()
                return False
            elif "No authentication methods available" in str(e):
                pass
            else:
                raise e
        if conn is not None:
            conn.close()
        if gw is not None:
            gw.close()

        print("\033[1;32mOK\033[0m")
        self.endpoint.reachable=True
        new_distance = 1 if gw is None else gateway.endpoint.distance + 1
        if self.endpoint.distance is None or self.endpoint.distance > new_distance:
            self.endpoint.distance = new_distance
        self.endpoint.save()
        return True

    def open(self, gateway="auto", verbose=False, target=False):
        if gateway is not None:
            if gateway == "auto":
                gateway = Connection.find_one(gateway_to=self.endpoint)
                if gateway is not None:
                    if not gateway.open(verbose=verbose):
                        raise ConnectionClosedError("Could not open gateway "+str(gateway))
                    gw = gateway.conn
                else:
                    gw = None
            else:
                if not gateway.open(verbose=verbose):
                    raise ConnectionClosedError("Could not open gateway "+str(gateway))
                gw = gateway.conn
        else:
            gw = None

        paramiko_args = {**self.creds.kwargs, 'look_for_keys':False, 'allow_agent':False}
        hostname = ""
        if self.endpoint.host is not None:
            hostname = " ("+str(self.endpoint.host)+")"
        print("Connecting to \033[1;34m"+str(self)+"\033[0m"+hostname+" > ", end="")
        conn = fabric.Connection(host=self.endpoint.ip, port=self.endpoint.port, user=self.user.name, connect_kwargs=paramiko_args, gateway=gw, connect_timeout=3)
        try:
            conn.open()
        except paramiko.ssh_exception.NoValidConnectionsError:
            print("\033[1;31mKO\033[0m. Could not reach destination.")
            if gw is not None:
                gateway.close()
                #TODO remove path
                pass
            return False
        except (paramiko.ssh_exception.AuthenticationException,paramiko.ssh_exception.SSHException) as e:
            if isinstance(e,paramiko.ssh_exception.AuthenticationException) or "encountered" in str(e):
                print("\033[1;31mKO\033[0m. Authentication failed.")
                return False
            else:
                raise e

        print("\033[1;32mOK\033[0m")

        if gateway is None:
            pathSrc = None
        else:
            if gateway.endpoint.host is not None:
                pathSrc = gateway.endpoint.host
            else:
                raise NoHostError
        p = Path(pathSrc, self.endpoint)
        p.save()
        self.save()

        if self.endpoint.host is None:
            self.identify(conn)

        self.gateway = gateway
        self.conn = conn

        return True

    def run(self, payload, wspaceFolder, stmt):
        opens = False
        if self.conn is None:
            if not self.open(target=True):
                return False
            opens = True
        payload.run(self, wspaceFolder, stmt)
        if opens:
            self.close()
        return True

    def close(self):
        if self.conn is not None:
            self.conn.close()
        print("Closed "+str(self))
        if self.gateway is not None:
            self.gateway.close()

    def __str__(self):
        return str(self.user)+":"+str(self.creds)+"@"+str(self.endpoint)


