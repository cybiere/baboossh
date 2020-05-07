import sqlite3
from baboossh import dbConn,Extensions, Endpoint, User, Creds, Path, Host
from baboossh.exceptions import *
import asyncio, asyncssh, sys

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
            except NoPathException as exc:
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
    
    async def identify(self,socket):
        try:
            result = await asyncio.wait_for(socket.run("hostname"), timeout=3.0)
            hostname = result.stdout.rstrip()
            result = await asyncio.wait_for(socket.run("uname -a"), timeout=3.0)
            uname = result.stdout.rstrip()
            result = await asyncio.wait_for(socket.run("cat /etc/issue"), timeout=3.0)
            issue = result.stdout.rstrip()
            result = await asyncio.wait_for(socket.run("cat /etc/machine-id"), timeout=3.0)
            machineId = result.stdout.rstrip()
            result = await asyncio.wait_for(socket.run("for i in `ls -l /sys/class/net/ | grep -v virtual | grep 'devices' | tr -s '[:blank:]' | cut -d ' ' -f 9 | sort`; do ip l show $i | grep ether | tr -s '[:blank:]' | cut -d ' ' -f 3; done"), timeout=3.0)
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

    async def async_openConnection(self,gw=None,verbose=True,target=False):
        if target:
            verbose=True
        authArgs = self.creds.kwargs
        hostname = ""
        if self.endpoint.host is not None:
            hostname = " ("+str(self.endpoint.host)+")"
        try:
            conn = await asyncio.wait_for(asyncssh.connect(self.endpoint.ip, port=self.endpoint.port, tunnel=gw, known_hosts=None, username=self.user.name,**authArgs), timeout=5)
        except Exception as e:
            if verbose:
                if e.__class__.__name__ == 'TimeoutError':
                    print("Connecting to \033[1;34m"+str(self)+"\033[0m"+hostname+" > \033[1;31mKO\033[0m. Timeout: could not reach destination")
                    raise e
                print("Connecting to \033[1;34m"+str(self)+"\033[0m"+hostname+" > \033[1;31mKO\033[0m. Error was: "+str(e))
            return None
        if verbose:
            print("Connecting to \033[1;34m"+str(self)+"\033[0m"+hostname+" > \033[1;32mOK\033[0m")
        return conn

    def initConnect(self,gateway="auto",verbose=False,target=False):
        if gateway is not None:
            if isinstance(gateway,asyncssh.SSHClientConnection):
                gw=gateway
            elif gateway == "auto":
                gateway = Connection.find_one(gateway_to=self.endpoint)
                if gateway is not None:
                    gw = gateway.initConnect(verbose=verbose)
                else:
                    gw = None
            else:
                gw = gateway.initConnect(verbose=verbose)
        else:
            gw = None
        try:
            c = asyncio.get_event_loop().run_until_complete(self.async_openConnection(gw,verbose=verbose,target=target))
        except:
            raise
        if c is not None:
            if not isinstance(gateway,asyncssh.SSHClientConnection):
                if gateway is None:
                    pathSrc = None
                else:
                    if gateway.endpoint.host is not None:
                        pathSrc = gateway.endpoint.host
                p = Path(pathSrc,self.endpoint)
                p.save()
        return c

    def connect(self,gateway="auto",verbose=False,target=False):
        try:
            c = self.initConnect(gateway,verbose,target=target)
        except asyncio.TimeoutError:
            raise
        else:
            if c is not None:
                self.save()
        return c

    def testConnect(self,gateway="auto",verbose=False):
        c = self.connect(gateway=gateway,verbose=verbose,target=True)
        if c is None:
            return False
        if self.endpoint.host is None:
            asyncio.get_event_loop().run_until_complete(self.identify(c))
        c.close()
        return True

    async def async_run(self,c,payload,wspaceFolder,stmt):
        return await payload.run(c,self,wspaceFolder,stmt)

    def run(self,payload,wspaceFolder,stmt):
        c = self.connect(target=True)
        if c is None:
            return False
        asyncio.get_event_loop().run_until_complete(self.async_run(c,payload,wspaceFolder,stmt))
        c.close()
        return True

    def __str__(self):
        return str(self.user)+":"+str(self.creds)+"@"+str(self.endpoint)


