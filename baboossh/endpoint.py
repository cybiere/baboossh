from baboossh.params import dbConn
from baboossh.host import Host
import asyncio, asyncssh, sys
import json

class Endpoint():
    def __init__(self,ip,port):
        self.ip = ip
        self.port = port
        self.host = None
        self.id = None
        self.scope = True
        self.scanned = False
        self.reachable = None
        self.found = None
        self.auth = []
        c = dbConn.get().cursor()
        c.execute('SELECT id,host,scanned,reachable,auth,scope,found FROM endpoints WHERE ip=? AND port=?',(self.ip,self.port))
        savedEndpoint = c.fetchone()
        c.close()
        if savedEndpoint is not None:
            self.id = savedEndpoint[0]
            self.host = Host.find(savedEndpoint[1])
            self.scanned = savedEndpoint[2] != 0
            if savedEndpoint[3] is None:
                self.reachable = None
            else:
                self.reachable = savedEndpoint[3] != 0
            if savedEndpoint[4] is not None :
                self.auth = json.loads(savedEndpoint[4])
            self.scope = savedEndpoint[5] != 0
            if savedEndpoint[6] is not None :
                self.found = Endpoint.find(savedEndpoint[6])

    def getId(self):
        return self.id

    def inScope(self):
        return self.scope

    def rescope(self):
        self.scope = True

    def unscope(self):
        self.scope = False

    def getIp(self):
        return self.ip

    def getPort(self):
        return int(self.port)

    def getHost(self):
        return self.host

    def setHost(self,host):
        self.host = host

    def isScanned(self):
        return self.scanned

    def setScanned(self,scanned):
        self.scanned = scanned

    def isReachable(self):
        return self.reachable

    def setReachable(self,reachable):
        self.reachable = reachable

    def getAuth(self):
        return self.auth

    def hasAuth(self,auth):
        return auth in self.auth

    def addAuth(self,auth):
        if auth not in self.auth:
            self.auth.append(auth)

    def getFound(self):
        return self.found

    def setFound(self,found):
        self.found = found

    def getConnection(self,working=True,scope=True):
        from baboossh.connection import Connection
        c = dbConn.get().cursor()
        if working:
            req = c.execute('''SELECT id FROM connections WHERE endpoint=? AND working=? ORDER BY root DESC''',(self.getId(),1))
        else:
            req = c.execute('''SELECT id FROM connections WHERE endpoint=? ORDER BY root DESC''',(self.getId(),))
        for row in req:
            connection = Connection.find(row[0])
            if scope is None:
                c.close()
                return connection
            elif scope == connection.inScope():
                c.close()
                return connection
        c.close()
        return None


    def save(self):
        c = dbConn.get().cursor()
        if not self.auth:
            jauth = None
        else:
            jauth = json.dumps(self.auth)
        if self.id is not None:
            #If we have an ID, the endpoint is already saved in the database : UPDATE
            c.execute('''UPDATE endpoints 
                SET
                    ip = ?,
                    port = ?,
                    host = ?,
                    scanned = ?,
                    reachable = ?,
                    auth = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                (self.ip, self.port, self.host.getId() if self.host is not None else None, self.scanned, self.reachable, jauth, self.scope, self.found.getId() if self.found is not None else None, self.id))
        else:
            #The endpoint doesn't exists in database : INSERT
            c.execute('''INSERT INTO endpoints(ip,port,host,scanned,reachable,auth,scope,found)
                VALUES (?,?,?,?,?,?,?,?) ''',
                (self.ip,self.port,self.host.getId() if self.host is not None else None, self.scanned, self.reachable, jauth, self.scope, self.found.getId() if self.found is not None else None))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM endpoints WHERE ip=? AND port=?',(self.ip,self.port))
            self.id  = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        from baboossh.path import Path
        from baboossh.connection import Connection
        if self.id is None:
            return
        if self.host is not None:
            endpoints = self.host.getEndpoints()
            if len(endpoints) == 1:
                self.host.delete()
        for connection in Connection.findByEndpoint(self):
            connection.delete()
        for path in Path.findByDst(self):
            path.delete()
        c = dbConn.get().cursor()
        c.execute('DELETE FROM endpoints WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return

    @classmethod
    def findAll(cls,scope=None):
        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT ip,port FROM endpoints')
        else:
            req = c.execute('SELECT ip,port FROM endpoints WHERE scope=?',(scope,))
        for row in req:
            ret.append(Endpoint(row[0],row[1]))
        return ret

    @classmethod
    def findAllWorking(cls):
        endpointsId = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT endpoint FROM connections WHERE working=?',(True,)):
            endpointsId.append(row[0])
        endpointsId = set(endpointsId)
        ret = []
        for endpointId in endpointsId:
            ret.append(cls.find(endpointId))
        return ret

    @classmethod
    def findByIpPort(cls,endpoint):
        ip,sep,port = endpoint.partition(":")
        if port == "":
            raise ValueError
        c = dbConn.get().cursor()
        c.execute('''SELECT id FROM endpoints WHERE ip=? and port=?''',(ip,port))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Endpoint(ip,port)

    @classmethod
    def find(cls,endpointId):
        if endpointId == 0:
            return None
        c = dbConn.get().cursor()
        c.execute('''SELECT ip,port FROM endpoints WHERE id=?''',(endpointId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Endpoint(row[0],row[1])

    @classmethod
    def findByFound(cls,endpoint,scope=None):
        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT ip,port FROM endpoints WHERE found=?',(endpoint.getId() if endpoint is not None else None,))
        else:
            req = c.execute('SELECT ip,port FROM endpoints WHERE scope=? and found=?',(scope,endpoint.getId() if endpoint is not None else None))
        for row in req:
            ret.append(Endpoint(row[0],row[1]))
        return ret

    def __str__(self):
        return self.ip+":"+str(self.port)

    def findGatewayConnection(self):
        from baboossh.path import Path
        from baboossh.connection import Connection
        if not Path.hasDirectPath(self):
            paths = Path.getPath(None,self)
            if paths is None:
                return None
            else:
                prevHop = paths[-1].getSrc().getClosestEndpoint()
                return Connection.findWorkingByEndpoint(prevHop)
        return None


    async def asyncScan(self,gw,silent):

        #This inner class access the endpoint through the "endpoint" var as "self" keywork is changed
        endpoint = self
        class ScanSSHClient(asyncssh.SSHClient):
            def connection_made(self, conn):
                endpoint.setReachable(True)
        
            def auth_banner_received(self, msg, lang):
                print(msg)
        
            def public_key_auth_requested(self):
                endpoint.addAuth("privkey")
                return None
        
            def password_auth_requested(self):
                endpoint.addAuth("password")
                return None
        
            def kbdint_auth_requested(self):
                endpoint.addAuth("kbdint")
                return None
        
            def auth_completed(self):
                pass

        self.setScanned(True)
        try:
            conn, client = await asyncio.wait_for(asyncssh.create_connection(ScanSSHClient, self.getIp(), port=self.getPort(),tunnel=gw,known_hosts=None,username="user"), timeout=3.0)
        except asyncssh.Error as e:
            #Permission denied => expected behaviour
            if e.code == 14:
                pass
            else:
                print("asyncssh Error: "+str(e))
                return False
        except asyncio.TimeoutError:
            self.setReachable(False)
            self.save()
            if not silent:
                print("Timeout")
            return False
        try:
            conn.close()
        except:
            pass
        if not silent:
            print("Done")
        self.save()
        return True

    def scan(self,gateway="auto",silent=False):
        if gateway == "auto":
            gateway = self.findGatewayConnection()
        if gateway is not None:
            gw = gateway.initConnect()
        else:
            gw = None
        done = asyncio.get_event_loop().run_until_complete(self.asyncScan(gw,silent))
        try:
            gw.close()
        except:
            pass

        if gateway is None:
            gwHost = None
        else:
            gwHost = gateway.getEndpoint().getHost()
            if gwHost is None:
                return done
        from baboossh.path import Path
        p = Path(gwHost,self)
        if done:
            p.save()
        else:
            if p.getId() is not None:
                p.delete()
        return done 



