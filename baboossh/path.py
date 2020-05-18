import hashlib
from baboossh.exceptions import NoPathError
from baboossh import Db, Endpoint, Host
from baboossh.utils import Unique

class Path(metaclass=Unique):
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

    def __init__(self, src, dst):
        if str(src) == str(dst):
            raise ValueError("Can't create path to self")
        self.src = src
        self.dst = dst
        self.id = None
        cursor = Db.get().cursor()
        cursor.execute('SELECT id FROM paths WHERE src=? AND dst=?', (self.src.id if self.src is not None else 0, self.dst.id))
        saved_path = cursor.fetchone()
        cursor.close()
        if saved_path is not None:
            self.id = saved_path[0]

    @classmethod
    def get_id(cls, src, dst):
        return hashlib.sha256((str(src)+str(dst)).encode()).hexdigest()

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

        cursor = Db.get().cursor()
        if self.id is not None:
            cursor.execute('''UPDATE paths
                SET
                    src = ?,
                    dst = ?
                WHERE id = ?''',
                           (self.src.id if self.src is not None else 0, self.dst.id, self.id))
        else:
            cursor.execute('''INSERT INTO paths(src, dst)
                VALUES (?, ?) ''',
                           (self.src.id if self.src is not None else 0, self.dst.id))
            cursor.close()
            cursor = Db.get().cursor()
            cursor.execute('SELECT id FROM paths WHERE src=? AND dst=?', (self.src.id if self.src is not None else 0, self.dst.id))
            self.id = cursor.fetchone()[0]
        cursor.close()
        Db.get().commit()

    def delete(self):
        """Delete an Path from the :class:`.Workspace`"""

        if self.id is None:
            return {}
        cursor = Db.get().cursor()
        cursor.execute('DELETE FROM paths WHERE id = ?', (self.id, ))
        cursor.close()
        Db.get().commit()
        return {"Path":[type(self).get_id(self.src, self.dst)]}

    @classmethod
    def find_all(cls, src=None, dst=None):
        """Find all Paths

        Args:
            src (:class:`.Host` or `None`): the Host to use as source, `"Local"` if `(int)0`
            dst (:class:`.Endpoint`): the Endpoint to use as destination

        Returns:
            A list of all `Path` s in the :class:`.Workspace`
        """

        if src is not None and src == 0:
            src_id = 0
        elif src is not None:
            src_id = src.id
        ret = []
        cursor = Db.get().cursor()
        if src is None:
            if dst is None:
                req = cursor.execute('SELECT src, dst FROM paths')
            else:
                req = cursor.execute('SELECT src, dst FROM paths WHERE dst=?', (dst.id, ))
        else:
            if dst is None:
                req = cursor.execute('SELECT src, dst FROM paths WHERE src=?', (src_id, ))
            else:
                req = cursor.execute('SELECT src, dst FROM paths WHERE src=? AND dst=?', (src_id, dst.id))
        for row in req:
            ret.append(Path(Host.find_one(host_id=row[0]), Endpoint.find_one(endpoint_id=row[1])))
        cursor.close()
        return ret

    @classmethod
    def find_one(cls, path_id=None):
        """Find an path by its id

        Args:
            pathId (int): the path id to search

        Returns:
            A single `Path` or `None`.
        """

        if path_id is None:
            return None
        cursor = Db.get().cursor()
        cursor.execute('''SELECT src, dst FROM paths WHERE id=?''', (path_id, ))
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return Path(Host.find_one(host_id=row[0]), Endpoint.find_one(endpoint_id=row[1]))

    @classmethod
    def direct(cls, dst):
        """Check if there is a direct Path from `"Local"` to an Endpoint

        Args:
            dst (:class:`.Endpoint`): the Endpoint to use as destination

        Returns:
            `True` if there is a `Path` from `"Local"` to dst, `False` otherwise
        """

        cursor = Db.get().cursor()
        cursor.execute('''SELECT id FROM paths WHERE src=0 and dst=?''', (dst.id, ))
        row = cursor.fetchone()
        cursor.close()
        return row is not None

    @classmethod
    def get(cls, dst, first=True):
        """Get the chain of paths from `"Local"` to an `Endpoint`

        Args:
            dst (:class:`Endpoint`): the destination `Endpoint`

        Returns:
            A `List` of :class:`Hosts` forming a chain from `"Local"` to dst

        Raises:
            NoPathError: if no path could be found to `dst`
        """

        try:
            previous_hop = Host.find_one(prev_hop_to=dst)
        except NoPathError as exc:
            raise exc
        if previous_hop is None:
            return [None, dst.host]
        chain = cls.get(previous_hop.closest_endpoint, first=False)
        if first:
            chain.append(dst)
            return chain
        chain.append(dst.host)
        return chain

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
