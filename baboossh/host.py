import json
import hashlib
from typing import Self, TYPE_CHECKING
from baboossh import Db
from baboossh.exceptions import NoPathError
from baboossh.utils import Unique

if TYPE_CHECKING:
    from baboossh import Endpoint

__all__ = ["Host"]


class Host(metaclass=Unique):
    """A machine with one or several :class:`Endpoint`

    This is used to aggregate endpoints as a single machine can have several
    interfaces with SSH listening on them. In order to prevent unecessary pivots,
    :class:`Path` s are calculated using the `Host` as sources as it might be
    longer to reach a `Host` from one endpoint rather than the other.

    The aggregation is checked by :func:`Connection.identify`, which is run on
    every endpoint newly connected. If every `Host` attribute matches with an
    existing Host, the endpoint is considered to belong to it and is added.

    Attributes:
        name (str): the hostname of the Host as returned by the command `hostname`, or a random name if not available
        hostname (str): the output of the command `hostname`
        id (int): the id of the Host
        uname (str): the output of the command `uname -a` on the Host
        issue (str): the content of the file `/etc/issue` on the Host
        machine_id (str): the content of the file `/etc/machine-id` on the Host
        macs ([str, ...]): a list of the MAC addresses of the Host interfaces
    """

    search_fields = ['name', 'uname']

    def __init__(self, hostname: str, uname: str, issue: str, machine_id: str, macs: list[str]) -> None:
        self.hostname = hostname
        self.id = None
        self.uname = uname
        self.issue = issue
        self.machine_id = machine_id
        self.macs = macs
        cursor = Db.get().cursor()
        cursor.execute('SELECT id, name FROM hosts WHERE hostname=? AND uname=? AND issue=? AND machine_id=? AND macs=?', (self.hostname, self.uname, self.issue, self.machine_id, json.dumps(self.macs)))
        saved_host = cursor.fetchone()
        cursor.close()
        if saved_host is not None:
            self.id = saved_host[0]
            self.name = saved_host[1]
        else:
            if hostname != "":
                name = hostname.split(".")[0]
                if len(name) > 20:
                    name = name[:20]
                incr = 0
            else:
                name = "host"
                incr = 1

            found_name: str | None = None
            while found_name is None:
                fullname = name if incr == 0 else name+"_"+str(incr)
                cursor = Db.get().cursor()
                cursor.execute('SELECT id FROM hosts WHERE name=?', (fullname, ))
                if cursor.fetchone() is not None:
                    incr = incr + 1
                else:
                    found_name = fullname
                cursor.close()
            self.name = found_name


    @classmethod
    def get_id(cls, hostname: str, uname: str, issue: str, machine_id: str, macs: list[str]) -> str:
        return hashlib.sha256((hostname+uname+issue+machine_id+json.dumps(macs)).encode()).hexdigest()

    @property
    def scope(self) -> bool:
        """Returns whether the `Host` is in scope

        A `Host` is in scope if all its :class:`Endpoint` s are in scope
        """

        for endpoint in self.endpoints:
            if not endpoint.scope:
                return False
        return True

    @scope.setter
    def scope(self, scope: bool) -> None:
        for endpoint in self.endpoints:
            endpoint.scope = scope
            endpoint.save()

    @property
    def distance(self) -> int | None:
        """Returns the `Host` 's number of hops from `"Local"`, or `None` if the `Host` has no `Endpoint`"""

        cursor = Db.get().cursor()
        cursor.execute('SELECT distance FROM endpoints WHERE host=? ORDER BY distance ASC', (self.id, ))
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return row[0]

    @property
    def closest_endpoint(self) -> "Endpoint":
        """Returns the `Host` 's closest :class:`Endpoint`

        Raises:
            ValueError: if the `Host` has no `Endpoint`
        """

        cursor = Db.get().cursor()
        cursor.execute('SELECT ip, port FROM endpoints WHERE host=? ORDER BY distance ASC', (self.id, ))
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            raise ValueError(f"Host {self.name!r} has no endpoints")
        from baboossh import Endpoint
        return Endpoint(row[0], row[1])

    @property
    def endpoints(self) -> "list[Endpoint]":
        """Returns a `List` of the `Host` 's :class:`Endpoint` s"""
        from baboossh import Endpoint
        endpoints = []
        cursor = Db.get().cursor()
        for row in cursor.execute('SELECT ip, port FROM endpoints WHERE host=?', (self.id, )):
            endpoints.append(Endpoint(row[0], row[1]))
        cursor.close()
        return endpoints

    def save(self) -> None:
        """Saves the `Host` in the :class:`Workspace` 's database"""
        cursor = Db.get().cursor()
        if self.id is not None:
            #If we have an ID, the host is already saved in the database : UPDATE
            cursor.execute('''UPDATE hosts
                SET
                    name = ?,
                    hostname = ?,
                    uname = ?,
                    issue = ?,
                    machine_id = ?,
                    macs = ?
                WHERE id = ?''',
                           (self.name, self.hostname, self.uname, self.issue, self.machine_id, json.dumps(self.macs), self.id))
        else:
            #The host doesn't exists in database : INSERT
            cursor.execute('''INSERT INTO hosts(name, hostname, uname, issue, machine_id, macs)
                VALUES (?, ?, ?, ?, ?, ?) ''',
                           (self.name, self.hostname, self.uname, self.issue, self.machine_id, json.dumps(self.macs)))
            cursor.close()
            cursor = Db.get().cursor()
            cursor.execute('SELECT id FROM hosts WHERE name=?', (self.name, ))
            self.id = cursor.fetchone()[0]
        cursor.close()
        Db.get().commit()

    def delete(self) -> dict[str, list[str]]:
        """Removes the `Host` from the :class:`Workspace`

        Recursively removes all :class:`Path` s starting from this `Host`
        """

        from baboossh import Path
        if self.id is None:
            return {}
        from baboossh.utils import unstore_targets_merge
        del_data: dict[str, list[str]] = {}
        for path in Path.find_all(src=self):
            unstore_targets_merge(del_data, path.delete())
        for endpoint in self.endpoints:
            endpoint.host = None
            endpoint.save()
        cursor = Db.get().cursor()
        cursor.execute('DELETE FROM hosts WHERE id = ?', (self.id, ))
        cursor.close()
        Db.get().commit()
        unstore_targets_merge(del_data, {"Host":[type(self).get_id(self.hostname, self.uname, self.issue, self.machine_id, self.macs)]})
        return del_data

    @classmethod
    def find_all(cls, scope: bool | None = None) -> list[Self]:
        """Returns a `List` of all `Host` s in the :class:`Workspace` matching the criteria

        Args:
            scope (bool): whether to return only `Host`s in scope (`True`),
                out of scope (`False`) or both (`None`)

        Returns:
            the `List` of `Host` s
        """

        ret = []
        cursor = Db.get().cursor()

        req = cursor.execute('SELECT hostname, uname, issue, machine_id, macs FROM hosts')

        for row in req:
            host = cls(row[0], row[1], row[2], row[3], json.loads(row[4]))
            if scope is None:
                ret.append(host)
            elif host.scope == scope:
                ret.append(host)
        cursor.close()
        return ret

    @classmethod
    def find_one(cls, host_id: int | None = None, name: str | None = None, prev_hop_to: "Endpoint | None" = None) -> "Host | None":
        """Find a `Host` by its id

        Args:
            host_id (int): the desired `Host` 's id
            name (str): the `Host` 's name to match

        Returns:
            A `Host` or `None`
        """

        if prev_hop_to is not None:
            from baboossh import Path
            paths = Path.find_all(dst=prev_hop_to)
            closest: Host | None = None
            smallest_distance: int | None = None
            for path in paths:
                if path.src is None:
                    #Direct path found, we can stop here
                    return None
                distance = path.src.distance
                if closest is None:
                    #Always keep the first candidate as a fallback, even with an
                    #unknown (None) distance, so a lone pivot with no known distance
                    #is still usable
                    closest = path.src
                    smallest_distance = distance
                elif distance is not None and (smallest_distance is None or distance < smallest_distance):
                    closest = path.src
                    smallest_distance = distance
            if closest is None:
                raise NoPathError
            return closest

        cursor = Db.get().cursor()
        if host_id is not None:
            cursor.execute('''SELECT hostname, uname, issue, machine_id, macs FROM hosts WHERE id=?''', (host_id, ))
        elif name is not None:
            cursor.execute('''SELECT hostname, uname, issue, machine_id, macs FROM hosts WHERE name=?''', (name, ))
        else:
            cursor.close()
            return None

        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return cls(row[0], row[1], row[2], row[3], json.loads(row[4]))

    @classmethod
    def getNextId(cls) -> int:
        cursor = Db.get().cursor()
        cursor.execute('''SELECT MAX(id) FROM hosts''')
        row = cursor.fetchone()
        cursor.close()
        if row[0] is None:
            return 1
        return row[0] + 1;


    @classmethod
    def search(cls, field: str, val: str, show_all: bool = False) -> list[Self]:
        """Search in the workspace for a `Host`

        Args:
            field (str): the `Host` attribute to search in
            val (str): the value to search for
            show_all (bool): whether to include out-of scope `Host` s in search results

        Returns:
            A `List` of `Host` s corresponding to the search.
        """

        if field not in cls.search_fields:
            raise ValueError
        ret = []
        cursor = Db.get().cursor()
        val = "%"+val+"%"
        #Ok this sounds fugly, but there seems to be no way to set a column name in a parameter. The SQL injection risk is mitigated as field must be in allowed fields, but if you find something better I take it
        for row in cursor.execute('SELECT hostname, uname, issue, machine_id, macs FROM hosts WHERE {} LIKE ?'.format(field), (val, )):
            ret.append(cls(row[0], row[1], row[2], row[3], json.loads(row[4])))
        if not show_all:
            ret = [host for host in ret if host.scope]
        return ret

    def __str__(self) -> str:
        return self.name
