import sqlite3
from src.params import dbConn,Extensions
from src.host import Host
from src.endpoint import Endpoint
from src.user import User
from src.creds import Creds
from src.path import Path
import asyncio, asyncssh, sys

class Connection():
    def __init__(self,endpoint,user,cred,brute=False):
        self.host = None
        self.endpoint = endpoint
        self.user = user
        self.cred = cred
        self.id = None
        self.tested = False
        self.working = False
        self.root = False
        self.brute = brute
        if brute:
            return
        c = dbConn.get().cursor()
        c.execute('SELECT id,tested,working,root,host FROM connections WHERE endpoint=? AND user=? AND cred=?',(self.endpoint.getId(),self.user.getId(),self.cred.getId()))
        savedEndpoint = c.fetchone()
        c.close()
        if savedEndpoint is not None:
            self.id = savedEndpoint[0]
            self.tested = savedEndpoint[1] != 0
            self.working = savedEndpoint[2] != 0
            self.root = savedEndpoint[3] != 0
            self.host = Host.find(savedEndpoint[4]) if savedEndpoint[4] is not None else None

    def getId(self):
        return self.id

    def getUser(self):
        return self.user

    def getEndpoint(self):
        return self.endpoint

    def getHost(self):
        return self.host

    def getCred(self):
        return self.cred

    def setTested(self, tested):
        self.tested = tested == True

    def isTested(self):
        return self.tested == True

    def setWorking(self, working):
        self.working = working == True

    def isWorking(self):
        return self.working == True

    def setRoot(self, root):
        self.root = root == True

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the endpoint is already saved in the database : UPDATE
            c.execute('''UPDATE connections 
                SET
                    host = ?,
                    endpoint= ?,
                    user = ?,
                    cred = ?,
                    tested = ?,
                    working = ?,
                    root = ?
                WHERE id = ?''',
                (self.host.getId() if self.host is not None else None, self.endpoint.getId(), self.user.getId(), self.cred.getId(), 1 if self.tested else 0, 1 if self.working else 0, 1 if self.root else 0, self.id))
        else:
            #The endpoint doesn't exists in database : INSERT
            c.execute('''INSERT INTO connections(host,endpoint,user,cred,tested,working,root)
                VALUES (?,?,?,?,?,?,?) ''',
                (self.host.getId() if self.host is not None else None, self.endpoint.getId(), self.user.getId(), self.cred.getId(), 1 if self.tested else 0, 1 if self.working else 0, 1 if self.root else 0))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM connections WHERE endpoint=? AND user=? AND cred=?',(self.endpoint.getId(),self.user.getId(),self.cred.getId()))
            self.id  = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    @classmethod
    def findByWorking(cls,working):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT endpoint,user,cred FROM connections WHERE working=?',(1 if working else 0,)):
            ret.append(Connection(Endpoint.find(row[0]),User.find(row[1]),Creds.find(row[2])))
        return ret

    @classmethod
    def find(cls,connectionId):
        c = dbConn.get().cursor()
        c.execute('SELECT endpoint,user,cred FROM connections WHERE id=?',(connectionId,))
        row = c.fetchone()
        c.close()
        if row is None:
            return None
        return Connection(Endpoint.find(row[0]),User.find(row[1]),Creds.find(row[2]))

    @classmethod
    def findWorkingByEndpoint(cls,endpoint):
        c = dbConn.get().cursor()
        c.execute('SELECT user,cred FROM connections WHERE working=1 AND endpoint=? ORDER BY root ASC',(endpoint.getId(),))
        row = c.fetchone()
        c.close()
        if row is None:
            return None
        return Connection(endpoint,User.find(row[0]),Creds.find(row[1]))

    @classmethod
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT id FROM connections'):
            ret.append(cls.find(row[0]))
        return ret

    @classmethod
    def findTested(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT id FROM connections where tested=?',(True,)):
            ret.append(cls.find(row[0]))
        return ret

    @classmethod
    def findWorking(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT id FROM connections where working=?',(True,)):
            ret.append(cls.find(row[0]))
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
            user = User.findByUsername(user)
            if user is None:
                raise ValueError("Supplied user isn't in workspace")
            if cred[0] == "#":
                cred = cred[1:]
            cred = Creds.find(cred)
            if cred is None:
                raise ValueError("Supplied credentials aren't in workspace")
            return Connection(endpoint,user,cred)
        else:    
            endpoint = Endpoint.findByIpPort(arg)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            connection = endpoint.getConnection()
            if connection == None:
                raise ValueError("No working connection for supplied endpoint")
            return connection
        return None
    
    async def async_openConnection(self,gw=None):
        authArgs = self.getCred().getKwargs()
        try:
            conn = await asyncio.wait_for(asyncssh.connect(self.getEndpoint().getIp(), port=self.getEndpoint().getPort(), tunnel=gw, known_hosts=None, username=self.getUser().getName(),**authArgs), timeout=5)
        except asyncio.TimeoutError:
            print("> \033[1;31;40mTimeout\033[0m")
            raise
        except Exception as e:
            if not self.brute:
                print("Error occured: "+str(e))
            return None
        return conn

    
    def initConnect(self,gw=None,retry=True,verbose=False):
        if gw is None:
            if not Path.hasDirectPath(self.getEndpoint()):
                prevHop = Path.getPath(None,self.getEndpoint())[-1].getSrc()
                gateway = Connection.findWorkingByEndpoint(prevHop)
                gw = gateway.initConnect(verbose=verbose)
        if verbose:
            print("> "+str(self)+"...",end="")
            sys.stdout.flush()
        return asyncio.get_event_loop().run_until_complete(self.async_openConnection(gw))

    def connect(self,gw=None,silent=False,verbose=False):
        if self.brute:
            silent=True
        if not silent:
            print("Establishing connection to \033[1;34;40m"+str(self)+"\033[0m",end="...")
            sys.stdout.flush()
        try:
            c = self.initConnect(gw,verbose=verbose)
        except asyncio.TimeoutError:
            return None
        else:
            self.setTested(True)
            self.setWorking(c is not None)
            if not self.brute:
                self.save()
        if c is not None and not silent:
            print("> \033[1;32;40mOK\033[0m")
        return c

    def testConnect(self,gw=None,verbose=False):
        c = self.connect(gw=gw,verbose=verbose)
        if c is None:
            return False
        c.close()
        return True

    async def async_run(self,c,payload,wspaceFolder,stmt):
        return await payload.run(c,self,wspaceFolder,stmt)

    def run(self,payload,wspaceFolder,stmt,gw=None):
        c = self.connect(gw)
        if c is None:
            return False
        asyncio.get_event_loop().run_until_complete(self.async_run(c,payload,wspaceFolder,stmt))
        c.close()
        return True

    def __str__(self):
        return str(self.user)+":"+str(self.cred)+"@"+str(self.endpoint)


