import sqlite3
from baboossh.params import dbConn
from baboossh.host import Host

class Endpoint():
    def __init__(self,ip,port):
        self.ip = ip
        self.port = port
        self.host = None
        self.id = None
        c = dbConn.get().cursor()
        c.execute('SELECT id,host FROM endpoints WHERE ip=? AND port=?',(self.ip,self.port))
        savedEndpoint = c.fetchone()
        c.close()
        if savedEndpoint is not None:
            self.id = savedEndpoint[0]
            self.host = Host.find(savedEndpoint[1])

    def getId(self):
        return self.id

    def getIp(self):
        return self.ip

    def getPort(self):
        return int(self.port)

    def getHost(self):
        return self.host

    def setHost(self,host):
        self.host = host

    def getConnection(self,working=True):
        c = dbConn.get().cursor()
        if working:
            c.execute('''SELECT id FROM connections WHERE endpoint=? AND working=? ORDER BY root DESC''',(self.getId(),1))
        else:
            c.execute('''SELECT id FROM connections WHERE endpoint=? ORDER BY root DESC''',(self.getId(),))
        ret = c.fetchone()
        c.close()
        if ret is None:
            return None

        from baboossh.connection import Connection
        return Connection.find(ret[0])

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the endpoint is already saved in the database : UPDATE
            c.execute('''UPDATE endpoints 
                SET
                    ip = ?,
                    port = ?,
                    host = ?
                WHERE id = ?''',
                (self.ip, self.port, self.host.getId() if self.host is not None else None, self.id))
        else:
            #The endpoint doesn't exists in database : INSERT
            c.execute('''INSERT INTO endpoints(ip,port,host)
                VALUES (?,?,?) ''',
                (self.ip,self.port,self.host.getId() if self.host is not None else None))
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
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT ip,port FROM endpoints'):
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

    def __str__(self):
        return self.ip+":"+str(self.port)


