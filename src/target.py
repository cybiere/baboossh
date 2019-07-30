import sqlite3
from src.params import dbConn
from src.host import Host

class Target():
    def __init__(self,ip,port):
        self.ip = ip
        self.port = port
        self.host = None
        self.id = None
        c = dbConn.get().cursor()
        c.execute('SELECT id,host FROM targets WHERE ip=? AND port=?',(self.ip,self.port))
        savedTarget = c.fetchone()
        c.close()
        if savedTarget is not None:
            self.id = savedTarget[0]
            self.host = Host.find(savedTarget[1])

    def getId(self):
        return self.id

    def getIp(self):
        return self.ip

    def getPort(self):
        return int(self.port)

    def getHost(self):
        return self.host

    def getConnection(self,working=True):
        c = dbConn.get().cursor()
        if working:
            c.execute('''SELECT id FROM connections WHERE target=? AND working=? ORDER BY root DESC''',(self.getId(),1))
        else:
            c.execute('''SELECT id FROM connections WHERE target=? ORDER BY root DESC''',(self.getId(),))
        ret = c.fetchone()
        c.close()
        if ret is None:
            return None

        from src.connection import Connection
        return Connection.find(ret[0])

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the target is already saved in the database : UPDATE
            c.execute('''UPDATE targets 
                SET
                    ip = ?,
                    port = ?
                    host = ?
                WHERE id = ?''',
                (self.ip, self.port, self.host.getId() if self.host is not None else None, self.id))
        else:
            #The target doesn't exists in database : INSERT
            c.execute('''INSERT INTO targets(ip,port,host)
                VALUES (?,?,?) ''',
                (self.ip,self.port,self.host.getId() if self.host is not None else None))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM targets WHERE ip=? AND port=?',(self.ip,self.port))
            self.id  = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def toList(self):
        connection = self.getConnection()
        if connection is None:
            return str(self.ip)+":"+str(self.port)
        return str(self.ip)+":"+str(self.port)+"\tConnect with "+str(connection)

    @classmethod
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT ip,port FROM targets'):
            ret.append(Target(row[0],row[1]))
        return ret

    @classmethod
    def findByIpPort(cls,endpoint):
        ip,sep,port = endpoint.partition(":")
        if port == "":
            raise ValueError
        c = dbConn.get().cursor()
        c.execute('''SELECT id FROM targets WHERE ip=? and port=?''',(ip,port))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Target(ip,port)

    @classmethod
    def find(cls,targetId):
        c = dbConn.get().cursor()
        c.execute('''SELECT ip,port FROM targets WHERE id=?''',(targetId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Target(row[0],row[1])

    def __str__(self):
        return self.ip+":"+self.port


