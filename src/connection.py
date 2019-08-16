import sqlite3
from fabric import Connection as FabConnection
from src.params import dbConn,Extensions
from src.host import Host
from src.endpoint import Endpoint
from src.user import User
from src.creds import Creds
from src.path import Path

class Connection():
    def __init__(self,endpoint,user,cred):
        self.host = None
        self.endpoint = endpoint
        self.user = user
        self.cred = cred
        self.id = None
        self.tested = False
        self.working = False
        self.root = False
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

    def initConnect(self):
        kwargs = {} #Add default values here
        authArgs = self.getCred().getKwargs()
        if Path.hasDirectPath(self.getEndpoint()):
            #Direct connect
            c = FabConnection(host=self.getEndpoint().getIp(),port=self.getEndpoint().getPort(),user=self.getUser().getName(),connect_kwargs={**kwargs, **authArgs})
        else:
            #Get previous hop
            prevHop = Path.getPath(None,self.getEndpoint())[-1].getSrc()
            gateway = Connection.findWorkingByEndpoint(prevHop)

            c = FabConnection(host=self.getEndpoint().getIp(),port=self.getEndpoint().getPort(),user=self.getUser().getName(),connect_kwargs={**kwargs, **authArgs},gateway=gateway.initConnect())
        print("Establishing connection to "+str(self.getUser())+"@"+str(self.getEndpoint())+" (with creds "+str(self.getCred())+")",end="...")
        self.setTested(True)
        try:
            c.open()
        except Exception as e:
            print("> "+str(e))
            self.setWorking(False)
            self.save()
            return None
        print("> \033[1;31;40mPWND\033[0m")
        self.setWorking(True)
        self.save()
        return c

    def connect(self):
        c = self.initConnect()
        if c == None:
            return False
        c.close()
        return True

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

    def run(self,payload,wspaceFolder):
        c = self.initConnect()
        if c == None:
            return False
        ret = payload.run(c,self,wspaceFolder)
        c.close()
        return True

    def toList(self):
        return str(self)

    def __str__(self):
        return str(self.user)+":"+str(self.cred)+"@"+str(self.endpoint)


