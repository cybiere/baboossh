import sqlite3
import collections
from baboossh.exceptions import *
from baboossh import dbConn, Endpoint, Host

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
        c.execute('SELECT id FROM paths WHERE src=? AND dst=?',(self.src.id if self.src is not None else 0,self.dst.id))
        savedPath = c.fetchone()
        c.close()
        if savedPath is not None:
            self.id = savedPath[0]

    @property
    def scope(self):
        if not self.dst.scope:
            return False
        if self.src is None:
            return True
        return self.src.scope

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
                (self.src.id if self.src is not None else 0,self.dst.id, self.id))
        else:
            c.execute('''INSERT INTO paths(src,dst)
                VALUES (?,?) ''',
                (self.src.id if self.src is not None else 0,self.dst.id))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM paths WHERE src=? AND dst=?',(self.src.id if self.src is not None else 0,self.dst.id))
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
        for row in c.execute('SELECT src,dst FROM paths WHERE dst=?',(dst.id, )):
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
            srcId = src.id
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
        c.execute('''SELECT id FROM paths WHERE src=0 and dst=?''',(dst.id,))
        row = c.fetchone()
        c.close()
        return row is not None

    @classmethod
    def getPrevHop(cls,dst):
        """Returns the closest :class:`Host` which can reach an :class:`Endpoint`

        Args:
            dst (:class:`Endpoint`): the destination `Endpoint`

        Returns:
            The closest :class:`Host` which can reach the :class:`Endpoint`, or `None` if it is reachable from `"Local"`.

        Raises:
            NoPathException: if no path cloud be found to `dst`
        """

        paths = cls.findByDst(dst)
        smallestDistance = None
        closest = None
        for path in paths:
            if path.src is None:
                #Direct path found, we can stop here
                return None
            if closest is None:
                closest = path.src
                smallestDistance = path.src.distance
                continue
            if path.src.distance < smallestDistance:
                closest = path.src
                smallestDistance = path.src.distance
                continue
        if closest is None:
            raise NoPathException
        return closest

    @classmethod
    def getPath(cls,dst,first=True):
        """Get the chain of paths from `"Local"` to an `Endpoint`

        Args:
            dst (:class:`Endpoint`): the destination `Endpoint`

        Returns:
            A `List` of :class:`Hosts` forming a chain from `"Local"` to dst

        Raises:
            NoPathException: if no path could be found to `dst`
        """
        
        try:
            prevHop = cls.getPrevHop(dst)
        except NoPathException as exc:
            raise exc
        if prevHop == None:
            return [None]
        chain = cls.getPath(prevHop.getClosestEndpoint(),first=False)
        if first:
            chain.append(dst)
            return chain
        else:
            chain.append(dst.host)
            return chain
    
    @classmethod
    def getHostsOrderedClosest(cls):
        """Get a List of :class:`Host`\ s ordered by their distance to `"Local"`

        Lists the Hosts ordered by the number of pivots to reach them from
        `"Local"`

        Returns:
            An ordered `List` of :class:`Host`
        """

        ret = []
        done = []
        queue = collections.deque([None])
        try:
            while True:
                s = queue.popleft()
                for p in cls.findBySrc(s):
                    e = p.dst
                    h = e.host
                    if h is not None:
                        if h.id not in done:
                            done.append(h.id)
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
        if self.dst.host is not None:
            dst = str(self.dst.host)
        else:
            dst = str(self.dst)
        return src+" -> "+dst

