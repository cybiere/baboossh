import sqlite3
from baboossh import dbConn,Extensions, Endpoint, User, Creds, Path, Host
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
    def find(cls,connectionId):
        """Find a `Connection` by its id

        Args:
            connectionId (int): the `Connection` id to search

        Returns:
            A single `Connection` or `None`.
        """

        c = dbConn.get().cursor()
        c.execute('SELECT endpoint,user,cred FROM connections WHERE id=?',(connectionId,))
        row = c.fetchone()
        c.close()
        if row is None:
            return None
        return Connection(Endpoint.find(row[0]),User.find_one(user_id=row[1]),Creds.find(row[2]))

    @classmethod
    def findByEndpoint(cls,endpoint):
        """Find all `Connection`\ s to an :class:`Endpoint`

        Args:
            endpoint (:class:`Endpoint`): the `Endpoint` to find `Connection`\ s for

        Returns:
            A `List` of corresponding `Connection`\ s
        """

        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT user,cred FROM connections WHERE endpoint=?',(endpoint.id,)):
            ret.append(Connection(endpoint,User.find_one(user_id=row[0]),Creds.find(row[1])))
        c.close()
        return ret

    @classmethod
    def findByUser(cls,user):
        """Find all `Connection`\ s using a :class:`User`

        Args:
            user (:class:`User`): the `User` to find `Connection`\ s for

        Returns:
            A `List` of corresponding `Connection`\ s
        """

        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT endpoint,cred FROM connections WHERE user=?',(user.id,)):
            ret.append(Connection(Endpoint.find(row[0]),user,Creds.find(row[1])))
        c.close()
        return ret

    @classmethod
    def findByCreds(cls,creds):
        """Find all `Connection`\ s using a :class:`Creds`

        Args:
            creds (:class:`Creds`): the `Creds` to find `Connection`\ s for

        Returns:
            A `List` of corresponding `Connection`\ s
        """

        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT endpoint,user FROM connections WHERE cred=?',(creds.id,)):
            ret.append(Connection(Endpoint.find(row[0]),User.find_one(user_id=row[1]),creds))
        c.close()
        return ret

    @classmethod
    def findWorkingByEndpoint(cls,endpoint):
        c = dbConn.get().cursor()
        c.execute('SELECT user,cred FROM connections WHERE endpoint=? ORDER BY root ASC',(endpoint.id,))
        row = c.fetchone()
        c.close()
        if row is None:
            return None
        return Connection(endpoint,User.find_one(user_id=row[0]),Creds.find(row[1]))

    @classmethod
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT id FROM connections'):
            ret.append(cls.find(row[0]))
        c.close()
        return ret

    @classmethod
    def fromTarget(cls,arg):
        if '@' in arg and ':' in arg:
            auth,sep,endpoint = arg.partition('@')
            endpoint  = Endpoint.findByIpPort(endpoint)
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
            cred = Creds.find(cred)
            if cred is None:
                raise ValueError("Supplied credentials aren't in workspace")
            return Connection(endpoint,user,cred)
        else:    
            if ':' not in arg:
                arg = arg+':22'
            endpoint = Endpoint.findByIpPort(arg)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            connection = endpoint.getConnection()
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
                gateway = self.endpoint.getGatewayConnection()
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


