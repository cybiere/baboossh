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
    def find_all(cls,src=None,dst=None):
        """Find all Paths

        if src==None:
            srcId = 0
        else:
            srcId = src.id

        Args:
            src (:class:`.Host` or `None`): the Host to use as source, `"Local"` if `(int)0`
            dst (:class:`.Endpoint`): the Endpoint to use as destination

        Returns:
            A list of all `Path`\ s in the :class:`.Workspace`
        """

        if src is not None and src == 0:
            src_id = 0
        elif src is not None:
            src_id = src.id
        ret = []
        c = dbConn.get().cursor()
        if src is None:
            if dst is None:
                req = c.execute('SELECT src,dst FROM paths')
            else:
                req = c.execute('SELECT src,dst FROM paths WHERE dst=?',(dst.id, ))
        else:
            if dst is None:
                req = c.execute('SELECT src,dst FROM paths WHERE src=?',(src_id, ))
            else:
                req = c.execute('SELECT src,dst FROM paths WHERE src=? AND dst=?',(src_id, dst.id ))
        for row in req:
            ret.append(Path(Host.find_one(host_id=row[0]),Endpoint.find_one(endpoint_id=row[1])))
        c.close()
        return ret

    @classmethod
    def find_one(cls,path_id=None):
        """Find an path by its id

        Args:
            pathId (int): the path id to search

        Returns:
            A single `Path` or `None`.
        """

        if path_id is None:
            return None
        c = dbConn.get().cursor()
        c.execute('''SELECT src,dst FROM paths WHERE id=?''',(path_id,))
        row = c.fetchone()
        c.close()
        if row is None:
            return None
        return Path(Host.find_one(host_id=row[0]),Endpoint.find_one(endpoint_id=row[1]))
    
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

        paths = cls.find_all(dst=dst)
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
            previous_hop = cls.getPrevHop(dst)
        except NoPathException as exc:
            raise exc
        if prevHop == None:
            return [None]
        chain = cls.getPath(previous_hop.closest_endpoint,first=False)
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
                for p in cls.find_all(src=s):
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

