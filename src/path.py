import sqlite3
from src.params import dbConn
from src.endpoint import Endpoint

class Path():
    def __init__(self,src,dst):
        self.src = src
        self.dst = dst
        self.id = None
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM paths WHERE src=? AND dst=?',(self.src.getId() if self.src is not None else 0,self.dst.getId()))
        savedPath = c.fetchone()
        c.close()
        if savedPath is not None:
            self.id = savedPath[0]

    def getId(self):
        return self.id

    def getSrc(self):
        return self.src

    def getDst(self):
        return self.dst

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the user is already saved in the database : UPDATE
            c.execute('''UPDATE paths 
                SET
                    src = ?,
                    dst = ?
                WHERE id = ?''',
                (self.src.getId() if self.src is not None else 0,self.dst.getId(), self.id))
        else:
            #The user doesn't exists in database : INSERT
            c.execute('''INSERT INTO paths(src,dst)
                VALUES (?,?) ''',
                (self.src.getId() if self.src is not None else 0,self.dst.getId()))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM paths WHERE src=? AND dst=?',(self.src.getId() if self.src is not None else 0,self.dst.getId()))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    @classmethod
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT src,dst FROM paths'):
            ret.append(Path(Endpoint.find(row[0]),Endpoint.find(row[1])))
        return ret

    @classmethod
    def find(cls,pathId):
        c = dbConn.get().cursor()
        c.execute('''SELECT src,dst FROM paths WHERE id=?''',(pathId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Path(Endpoint.find(row[0]),Endpoint.find(row[1]))

    @classmethod
    def findByDst(cls,dst):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT src,dst FROM paths WHERE dst=?',(dst.getId(), )):
            ret.append(Path(Endpoint.find(row[0]),Endpoint.find(row[1])))
        return ret

    @classmethod
    def hasDirectPath(cls,dst):
        c = dbConn.get().cursor()
        c.execute('''SELECT id FROM paths WHERE src=0 and dst=?''',(dst.getId(),))
        row = c.fetchone()
        c.close()
        return row is not None


    def toList(self):
        return str(self)

    def __str__(self):
        if self.src is not None:
            src = str(self.src)
        else:
            src = "local"
        return src+" -> "+str(self.dst)

