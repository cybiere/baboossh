import sqlite3
from src.params import dbConn
from src.host import Host
from src.endpoint import Endpoint
from src.user import User
from src.creds import Creds

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

    def setWorking(self, working):
        self.working = working == True

    def setRoot(self, root):
        self.root = root == True

    def isWorking(self):
        return self.working == True

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
    def find(cls,connectionId):
        c = dbConn.get().cursor()
        c.execute('SELECT endpoint,user,cred FROM connections WHERE id=?',(connectionId,))
        row = c.fetchone()
        c.close()
        if row is None:
            return None
        return Connection(Endpoint.find(row[0]),User.find(row[1]),Creds.find(row[2]))



    def __str__(self):
        return str(self.user)+":"+str(self.cred)+"@"+str(self.endpoint)


