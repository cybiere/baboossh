import sqlite3
from baboossh import dbConn, Endpoint, Host
from collections import deque

class Path():
    """Indicates an endpoint is reachable from a host

    A path is created when an :class:`.Endpoint` can be reached from a :class:`.Host`,
    either by being on the same network or by not having filtering between both.
    This is used to pivot through compromised hosts to reach endpoints which could
    not be accessed from the user's position in the network (`"Local"`)

    This class provides various functions to get paths to Endpoints through
    several pivots, or to discover new paths to the host.

    Attributes:
        src (:class:`.Host` or `None`): the starting Host of the path. if `None`,
            the path starts at `"Local"`, the user current's position in the network.
        dst (:class:`.Endpoint`): the destination Endpoint of the path
        id (int): The path id
    """

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

    def inScope(self):
        if not self.dst.inScope():
            return False
        if self.src is None:
            return True
        return self.src.inScope()

    def getSrc(self):
        return self.src

    def getDst(self):
        return self.dst

    def save(self):
        """Save the Path in database

        If the Path object has an id it means it is already stored in database,
        so it is updated. Else it is inserted and the id is set in the object.

        """

        c = dbConn.get().cursor()
        if self.id is not None:
            c.execute('''UPDATE paths 
                SET
                    src = ?,
                    dst = ?
                WHERE id = ?''',
                (self.src.getId() if self.src is not None else 0,self.dst.getId(), self.id))
        else:
            c.execute('''INSERT INTO paths(src,dst)
                VALUES (?,?) ''',
                (self.src.getId() if self.src is not None else 0,self.dst.getId()))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM paths WHERE src=? AND dst=?',(self.src.getId() if self.src is not None else 0,self.dst.getId()))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        """Delete an Path from the :class:`.Workspace`"""

        if self.id is None:
            return
        c = dbConn.get().cursor()
        c.execute('DELETE FROM paths WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return

    @classmethod
    def findAll(cls):
        """Find all Paths

        Returns:
            A list of all `Path`\ s in the :class:`.Workspace`
        """

        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT src,dst FROM paths'):
            ret.append(Path(Host.find(row[0]),Endpoint.find(row[1])))
        c.close()
        return ret

    @classmethod
    def find(cls,pathId):
        """Find an path by its id

        Args:
            pathId (int): the path id to search

        Returns:
            A single `Path` or `None`.
        """

        c = dbConn.get().cursor()
        c.execute('''SELECT src,dst FROM paths WHERE id=?''',(pathId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Path(Host.find(row[0]),Endpoint.find(row[1]))
    
    @classmethod
    def findByDst(cls,dst):
        """Find all paths to an :class:`.Endpoint`

        Args:
            dst (:class:`.Endpoint`): the Endpoint to use as destination

        Returns:
            A list of `Path`\ s to provided Endpoint
        """

        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT src,dst FROM paths WHERE dst=?',(dst.getId(), )):
            ret.append(Path(Host.find(row[0]),Endpoint.find(row[1])))
        c.close()
        return ret

    @classmethod
    def findBySrc(cls,src):
        """Find all paths from a :class:`.Host`

        Args:
            src (:class:`.Host` or `None`): the Host to use as source, `"Local"` if `None`

        Returns:
            A list of `Path`\ s from provided Host
        """

        if src==None:
            srcId = 0
        else:
            srcId = src.getId()
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT dst FROM paths WHERE src=?',(srcId, )):
            ret.append(Path(src,Endpoint.find(row[0])))
        c.close()
        return ret

    @classmethod
    def hasDirectPath(cls,dst):
        """Check if there is a Path from `"Local"` to an Endpoint

        Args:
            dst (:class:`.Endpoint`): the Endpoint to use as destination

        Returns:
            `True` if there is a `Path` from `"Local"` to dst, `False` otherwise
        """

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

        for endpoint in Endpoint.findAllWithWorkingConn():
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
            if chainId[i] == 0:
                srcHost = None
            else:
                srcEndpoint=Endpoint.find(chainId[i])
                srcHost=srcEndpoint.getHost()
            chain.append(Path(srcHost,Endpoint.find(chainId[i+1])))
        return chain
    
    @classmethod
    def getHostsOrderedClosest(cls):
        ret = []
        done = []
        queue = deque([None])
        try:
            while True:
                s = queue.popleft()
                for p in cls.findBySrc(s):
                    e = p.getDst()
                    h = e.getHost()
                    if h is not None:
                        if h.getId() not in done:
                            done.append(h.getId())
                            ret.append(h)
                            queue.append(h)
        except IndexError:
            #Queue is empty
            pass
        return ret

    def __str__(self):
        if self.src is not None:
            src = str(self.src)
        else:
            src = "local"
        if self.dst.getHost() is not None:
            dst = str(self.dst.getHost())
        else:
            dst = str(self.dst)
        return src+" -> "+dst

