import sqlite3
from baboossh.params import dbConn,Extensions
from baboossh.endpoint import Endpoint
from baboossh.user import User
from baboossh.creds import Creds
from baboossh.path import Path
from baboossh.host import Host
import asyncio, asyncssh, sys

class Connection():
    def __init__(self,endpoint,user,cred,brute=False):
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
        c.execute('SELECT id,tested,working,root FROM connections WHERE endpoint=? AND user=? AND cred=?',(self.endpoint.getId(),self.user.getId(),self.cred.getId()))
        savedConnection = c.fetchone()
        c.close()
        if savedConnection is not None:
            self.id = savedConnection[0]
            self.tested = savedConnection[1] != 0
            self.working = savedConnection[2] != 0
            self.root = savedConnection[3] != 0

    def getId(self):
        return self.id

    def getUser(self):
        return self.user

    def getEndpoint(self):
        return self.endpoint

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
                    endpoint= ?,
                    user = ?,
                    cred = ?,
                    tested = ?,
                    working = ?,
                    root = ?
                WHERE id = ?''',
                (self.endpoint.getId(), self.user.getId(), self.cred.getId(), self.tested,self.working,self.root, self.id))
        else:
            #The endpoint doesn't exists in database : INSERT
            c.execute('''INSERT INTO connections(endpoint,user,cred,tested,working,root)
                VALUES (?,?,?,?,?,?) ''',
                (self.endpoint.getId(), self.user.getId(), self.cred.getId(), self.tested , self.working , self.root ))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM connections WHERE endpoint=? AND user=? AND cred=?',(self.endpoint.getId(),self.user.getId(),self.cred.getId()))
            self.id  = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        if self.id is None:
            return
        c = dbConn.get().cursor()
        c.execute('DELETE FROM connections WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return


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
    def findByEndpoint(cls,endpoint):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT user,cred FROM connections WHERE endpoint=?',(endpoint.getId(),)):
            ret.append(Connection(endpoint,User.find(row[0]),Creds.find(row[1])))
        c.close()
        return ret

    @classmethod
    def findByUser(cls,user):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT endpoint,cred FROM connections WHERE user=?',(user.getId(),)):
            ret.append(Connection(Endpoint.find(row[0]),user,Creds.find(row[1])))
        c.close()
        return ret

    @classmethod
    def findByCreds(cls,creds):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT endpoint,user FROM connections WHERE cred=?',(creds.getId(),)):
            ret.append(Connection(Endpoint.find(row[0]),User.find(row[1]),creds))
        c.close()
        return ret

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
            if newHost.getId() is None:
                print("> New host: "+hostname)
            else:
                print("> Existing host: "+hostname)
            newHost.save()
            e = self.getEndpoint()
            e.setHost(newHost)
            e.save()
        except Exception as e:
            print("Error : "+str(e))
            return False
        return True

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

    def initConnect(self,gw=None,verbose=False):
        addLocalPath = False
        if gw is None:
            if not Path.hasDirectPath(self.getEndpoint()):
                paths = Path.getPath(None,self.getEndpoint())
                if paths is None:
                    print("> No path to "+str(self.getEndpoint())+", trying direct...",end="")
                    sys.stdout.flush()
                    gw = None
                    addLocalPath = True
                else:
                    prevHop = paths[-1].getSrc().getClosestEndpoint()
                    gateway = Connection.findWorkingByEndpoint(prevHop)
                    gw = gateway.initConnect(verbose=verbose)
        elif gw == "local":
            gw = None
        if verbose:
            print("> "+str(self)+"...",end="")
            sys.stdout.flush()
        try:
            c = asyncio.get_event_loop().run_until_complete(self.async_openConnection(gw))
        except:
            raise
        if addLocalPath:
            newPath = Path(src=None,dst=self.getEndpoint())
            newPath.save()
        return c

    def connect(self,gw=None,silent=False,verbose=False):
        if self.brute:
            silent=True
        if not silent:
            print("Establishing connection to \033[1;34;40m"+str(self)+"\033[0m",end="...")
            sys.stdout.flush()
        try:
            addLocalPath = False
            c = self.initConnect(gw,verbose)
        except asyncio.TimeoutError:
            return None
        else:
            self.setTested(True)
            self.setWorking(c is not None)
            if not self.brute:
                self.save()
        if c is not None:
            if not silent:
                print("> \033[1;32;40mOK\033[0m")
        return c

    def testConnect(self,gw=None,verbose=False,silent=False):
        c = self.connect(gw=gw,verbose=verbose,silent=silent)
        if c is None:
            return False
        if self.getEndpoint().getHost() is None:
            print("\tUnknown host, identifying...",end="")
            sys.stdout.flush()
            asyncio.get_event_loop().run_until_complete(self.identify(c))
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


