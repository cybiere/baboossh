import sqlite3
from baboossh import dbConn,Extensions, Endpoint, User, Creds, Path, Host
from baboossh.exceptions import *
import fabric, paramiko, sys

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

class Connection():
    """A :class:`User` and :class:`Creds` to authenticate on an :class:`Endpoint`
    
    A connection represents the working association of those 3 objects to connect
    a target. It can be used to run payloads on a :class:`Host`, open a
    :class:`Tunnel` to it or use it as a pivot to reach new :class:`Endpoint`\ s

    Attributes:
        endpoint (:class:`Endpoint`): the `Connection`\ 's endpoint
        user (:class:`User`): the `Connection`\ 's user
        creds (:class:`Creds`): the `Connection`\ 's credentials
        id (int): the `Connection`\ 's id
    """


    def __init__(self,endpoint,user,cred):
        self.endpoint = endpoint
        self.user = user
        self.creds = cred
        self.id = None
        self.root = False
        if user is None or cred is None:
            return
        c = dbConn.get().cursor()
        c.execute('SELECT id,root FROM connections WHERE endpoint=? AND user=? AND cred=?',(self.endpoint.id,self.user.id,self.creds.id))
        savedConnection = c.fetchone()
        c.close()
        if savedConnection is not None:
            self.id = savedConnection[0]
            self.root = savedConnection[1] != 0

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
        """Save the `Connection` to the :class:`Workspace`\ 's database"""
        c = dbConn.get().cursor()
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
            c.execute('''INSERT INTO connections(endpoint,user,cred,root)
                VALUES (?,?,?,?) ''',
                (self.endpoint.id, self.user.id, self.creds.id, self.root ))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM connections WHERE endpoint=? AND user=? AND cred=?',(self.endpoint.id,self.user.id,self.creds.id))
            self.id  = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        """Delete the `Connection` from the :class:`Workspace`\ 's database"""
        if self.id is None:
            return
        c = dbConn.get().cursor()
        c.execute('DELETE FROM connections WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return


    @classmethod
    def find_one(cls,connection_id=None, endpoint=None, scope=None, gateway_to=None):
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
            return cls.find_one(endpoint=closest_host.closest_endpoint,scope=True)

        c = dbConn.get().cursor()
        if connection_id is not None:
            req = c.execute('SELECT endpoint,user,cred FROM connections WHERE id=?',(connection_id,))
        elif endpoint is not None:
            req = c.execute('SELECT endpoint,user,cred FROM connections WHERE endpoint=? ORDER BY root ASC',(endpoint.id,))
        else:
            c.close()
            return None
        if scope is None:
            row = c.fetchone()
            c.close()
            if row is None:
                return None
            return Connection(Endpoint.find_one(endpoint_id=row[0]),User.find_one(user_id=row[1]),Creds.find_one(creds_id=row[2]))
        for row in req:
            conn = Connection(Endpoint.find_one(endpoint_id=row[0]),User.find_one(user_id=row[1]),Creds.find_one(creds_id=row[2]))
            if scope == conn.scope:
               c.close()
               return conn
        c.close()
        return None


    @classmethod
    def find_all(cls,endpoint=None,user=None,creds=None,scope=None):
        ret = []
        c = dbConn.get().cursor()
        if endpoint is not None:
            req = c.execute('SELECT endpoint,user,cred FROM connections WHERE endpoint=?',(endpoint.id,))
        elif user is not None:
            req = c.execute('SELECT endpoint,user,cred FROM connections WHERE user=?',(user.id,))
        elif creds is not None:
            req = c.execute('SELECT endpoint,user,cred FROM connections WHERE cred=?',(creds.id,))
        else:
            req = c.execute('SELECT endpoint,user,cred FROM connections')
        
        for row in req:
            conn = Connection(Endpoint.find_one(endpoint_id=row[0]),User.find_one(user_id=row[1]),Creds.find_one(creds_id=row[2]))
            if scope is None or conn.scope == scope:
                ret.append(conn)
        c.close()
        return ret

    @classmethod
    def fromTarget(cls,arg):
        if '@' in arg and ':' in arg:
            auth,sep,endpoint = arg.partition('@')
            endpoint  = Endpoint.find_one(ip_port=endpoint)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            user,sep,cred = auth.partition(":")
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
            return Connection(endpoint,user,cred)
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

    def identify(self,socket):
        try:
            result = socket.run("hostname", hide='both')
            hostname = result.stdout.rstrip()
            result = socket.run("uname -a", hide='both')
            uname = result.stdout.rstrip()
            socket.run("cat /etc/issue", hide='both')
            issue = result.stdout.rstrip()
            socket.run("cat /etc/machine-id", hide='both')
            machineId = result.stdout.rstrip()
            socket.run("for i in `ls -l /sys/class/net/ | grep -v virtual | grep 'devices' | tr -s '[:blank:]' | cut -d ' ' -f 9 | sort`; do ip l show $i | grep ether | tr -s '[:blank:]' | cut -d ' ' -f 3; done", hide='both')
            macStr = result.stdout.rstrip()
            macs = macStr.split()
            newHost = Host(hostname,uname,issue,machineId,macs)
            e = self.endpoint
            if newHost.id is None:
                print("\t"+str(self)+" is a new host: "+hostname)
            else:
                print("\t"+str(self)+" is an existing host: "+hostname)
                if not newHost.scope:
                    e.scope = False
            newHost.save()
            e.host = newHost
            e.save()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True

    def touch(self,gateway="auto"):
        if gateway is not None:
            if gateway == "auto":
                gateway = Connection.find_one(gateway_to=self.endpoint)
                if gateway is not None:
                    gw = gateway.open(verbose=False)
                else:
                    gw = None
            else:
                gw = gateway.open(verbose=False)
        else:
            gw = None

        paramiko_args = {'look_for_keys':False,'allow_agent':False}

        print("Reaching \033[1;34m"+str(self.endpoint)+"\033[0m > ", end="")
        conn = fabric.Connection(host=self.endpoint.ip, port=self.endpoint.port, user="user", connect_kwargs=paramiko_args, gateway=gw, connect_timeout=3)
        try:
            conn.open()
        except paramiko.ssh_exception.NoValidConnectionsError:
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
        self.endpoint.distance = 1 if gw is None else gateway.endpoint.distance + 1
        self.endpoint.save()
        return True

    def open(self,gateway="auto",verbose=False,target=False):
        if gateway is not None:
            if gateway == "auto":
                gateway = Connection.find_one(gateway_to=self.endpoint)
                if gateway is not None:
                    gw = gateway.open(verbose=verbose)
                else:
                    gw = None
            else:
                gw = gateway.open(verbose=verbose)
        else:
            gw = None

        paramiko_args = {**self.creds.kwargs,'look_for_keys':False,'allow_agent':False}
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
                #TODO remove path
                pass
            return None
        except paramiko.ssh_exception.AuthenticationException:
            print("\033[1;31mKO\033[0m. Authentication failed.")
            return None

        print("\033[1;32mOK\033[0m")

        if gateway is None:
            pathSrc = None
        else:
            if gateway.endpoint.host is not None:
                pathSrc = gateway.endpoint.host
            else:
                raise NoHostError
        p = Path(pathSrc,self.endpoint)
        p.save()
        self.save()

        if self.endpoint.host is None:
            self.identify(conn)

        return conn

    def run(self,payload,wspaceFolder,stmt):
        c = self.open(target=True)
        if c is None:
            return False
        payload.run(c,self,wspaceFolder,stmt)
        c.close()
        return True

    def __str__(self):
        return str(self.user)+":"+str(self.creds)+"@"+str(self.endpoint)


