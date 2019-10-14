import sqlite3
from src.params import dbConn
from src.endpoint import Endpoint
from src.host import Host

class Path():
    def __init__(self,src,dst):
        if str(src) == str(dst):
            raise ValueError("Can't create path to self")
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
            ret.append(Path(Host.find(row[0]),Endpoint.find(row[1])))
        c.close()
        return ret

    @classmethod
    def find(cls,pathId):
        c = dbConn.get().cursor()
        c.execute('''SELECT src,dst FROM paths WHERE id=?''',(pathId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Path(Host.find(row[0]),Endpoint.find(row[1]))

    @classmethod
    def findByDst(cls,dst):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT src,dst FROM paths WHERE dst=?',(dst.getId(), )):
            ret.append(Path(Host.find(row[0]),Endpoint.find(row[1])))
        c.close()
        return ret

    @classmethod
    def hasDirectPath(cls,dst):
        c = dbConn.get().cursor()
        c.execute('''SELECT id FROM paths WHERE src=0 and dst=?''',(dst.getId(),))
        row = c.fetchone()
        c.close()
        return row is not None

    @classmethod
    def getAdjacencyList(cls):
        adj = {}
        adj[0] = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT dst FROM paths WHERE src=0'):
            adj[0].append(row[0])
        c.close()

        for endpoint in Endpoint.findAllWorking():
            adj[endpoint.getId()] = []
            c = dbConn.get().cursor()
            for row in c.execute('SELECT dst FROM paths WHERE src=?',(endpoint.getHost().getId(), )):
                adj[endpoint.getId()].append(row[0])
            c.close()
        return adj

    @classmethod
    def easyPath(cls,srcId,dstId):
        adj = cls.getAdjacencyList()
        queue = [[srcId]]
        done = []
        while len(queue) > 0:
            road = queue.pop(0)
            head = road[-1]
            if head not in adj.keys():
                done.append(head)
            if head in done:
                continue
            if dstId in adj[head]:
                road.append(dstId)
                return road
            for nextHop in adj[head]:
                newRoad = road.copy()
                newRoad.append(nextHop)
                queue.append(newRoad)
            done.append(head)
        return []

    @classmethod
    def getPath(cls,src,dst):
        if src == None:
            srcId = 0
        else:
            srcId = src.getId()
        dstId = dst.getId()
        chainId = cls.easyPath(srcId,dstId)
        if len(chainId) == 0:
            return None
        chain = []
        for i in range(0,len(chainId)-1):
            chain.append(Path(Host.find(chainId[i]),Endpoint.find(chainId[i+1])))
        return chain

    def __str__(self):
        if self.src is not None:
            src = str(self.src)
        else:
            src = "local"
        if self.dst.getHost() is not None:
            dst = str(self.dst.getHost())
        else:
            dst = str(dst)
        return src+" -> "+dst

