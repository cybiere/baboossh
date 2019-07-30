import sqlite3
from src.params import dbConn
from src.host import Host

class Target():
    def __init__(self,ip,port,host):
        self.ip = ip
        self.port = port
        self.host = host
        self.id = None
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM targets WHERE ip=? AND port=?',(self.ip,self.port))
        savedTarget = c.fetchone()
        c.close()
        if savedTarget is not None:
            self.id = savedTarget[0]

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
            c.execute('''SELECT id,host,user,cred FROM connections WHERE target=? AND working=? ORDER BY root DESC''',(self.getId(),1))
        else:
            c.execute('''SELECT id,host,user,cred FROM connections WHERE target=? ORDER BY root DESC''',(self.getId(),))
        ret = c.fetchone()
        if ret is None:
            return None

        c.execute('''SELECT name FROM hosts WHERE id=?''',(ret[1],))
        host = Host(c.fetchone()[0])

        from src.user import User
        c.execute('''SELECT username FROM users WHERE id=?''',(ret[2],))
        user = User(c.fetchone()[0])
        from src.creds import Creds
        c.execute('''SELECT type,content FROM creds WHERE id=?''',(ret[3],))
        credRet = c.fetchone()
        cred = Creds(credRet[0],credRet[1])
        c.close()

        from src.connection import Connection
        return Connection(host,self,user,cred)

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
                (self.ip, self.port, self.host.getId(), self.id))
        else:
            #The target doesn't exists in database : INSERT
            c.execute('''INSERT INTO targets(ip,port,host)
                VALUES (?,?,?) ''',
                (self.ip,self.port,self.host.getId()))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM targets WHERE ip=? AND port=?',(self.ip,self.port))
            self.id  = c.fetchone()[0]
            self.host.registerTarget(self)
        c.close()
        dbConn.get().commit()

    def toList(self):
        connection = self.getConnection()
        if connection is None:
            print(str(self.ip)+":"+str(self.port))
        else:
            print(str(self.ip)+":"+str(self.port)+"\tConnect with "+str(connection))


    def __str__(self):
        return self.ip+":"+self.port


