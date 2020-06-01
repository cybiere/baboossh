import json
import hashlib
from baboossh import Db
from baboossh.exceptions import NoPathError
from baboossh.utils import Unique


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
        name (str): the hostname of the Host as returned by the command `hostname`
        id (int): the id of the Host
        uname (str): the output of the command `uname -a` on the Host
        issue (str): the content of the file `/etc/issue` on the Host
        machine_id (str): the content of the file `/etc/machine-id` on the Host
        macs ([str, ...]): a list of the MAC addresses of the Host interfaces
    """

    search_fields = ['name', 'uname']

    def __init__(self, hostname, uname, issue, machine_id, macs):
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

            self.name = None
            while self.name is None:
                fullname = name if incr == 0 else name+"_"+str(incr)
                cursor = Db.get().cursor()
                cursor.execute('SELECT id FROM hosts WHERE name=?', (fullname, ))
                if cursor.fetchone() is not None:
                    incr = incr + 1
                else:
                    self.name = fullname
                cursor.close()


    @classmethod
    def get_id(cls, hostname, uname, issue, machine_id, macs):
        return hashlib.sha256((hostname+uname+issue+machine_id+json.dumps(macs)).encode()).hexdigest()

    @property
    def scope(self):
        """Returns whether the `Host` is in scope

        A `Host` is in scope if all its :class:`Endpoint` s are in scope
        """

        for endpoint in self.endpoints:
            if not endpoint.scope:
                return False
        return True

    @scope.setter
    def scope(self, scope):
        for endpoint in self.endpoints:
            endpoint.scope = scope
            endpoint.save()

    @property
    def distance(self):
        """Returns the `Host` 's number of hops from `"Local"`"""

        cursor = Db.get().cursor()
        cursor.execute('SELECT distance FROM endpoints WHERE host=? ORDER BY distance DESC', (self.id, ))
        row = cursor.fetchone()
        cursor.close()
        return row[0]

    @property
    def closest_endpoint(self):
        """Returns the `Host` 's closest :class:`Endpoint`"""

        cursor = Db.get().cursor()
        cursor.execute('SELECT ip, port FROM endpoints WHERE host=? ORDER BY distance DESC', (self.id, ))
        row = cursor.fetchone()
        cursor.close()
        from baboossh import Endpoint
        return Endpoint(row[0], row[1])

    @property
    def endpoints(self):
        """Returns a `List` of the `Host` 's :class:`Endpoint` s"""
        from baboossh import Endpoint
        endpoints = []
        cursor = Db.get().cursor()
        for row in cursor.execute('SELECT ip, port FROM endpoints WHERE host=?', (self.id, )):
            endpoints.append(Endpoint(row[0], row[1]))
        cursor.close()
        return endpoints

    def save(self):
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

    def delete(self):
        """Removes the `Host` from the :class:`Workspace`

        Recursively removes all :class:`Path` s starting from this `Host`
        """

        from baboossh import Path
        if self.id is None:
            return {}
        from baboossh.utils import unstore_targets_merge
        del_data = {}
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
    def find_all(cls, scope=None):
        """Returns a `List` of all `Host` s in the :class:`Workspace` matching the criteria

        Args:
            scope (bool): whether to return only `Host`s in scope (`True`),
                out of scope (`False`) or both (`None`)
            name (str): the `Host` s' name to match

        Returns:
            the `List` of `Host` s
        """

        ret = []
        cursor = Db.get().cursor()

        req = cursor.execute('SELECT hostname, uname, issue, machine_id, macs FROM hosts')

        for row in req:
            host = Host(row[0], row[1], row[2], row[3], json.loads(row[4]))
            if scope is None:
                ret.append(host)
            elif host.scope == scope:
                ret.append(host)
        cursor.close()
        return ret

    @classmethod
    def find_one(cls, host_id=None, name=None, prev_hop_to=None):
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
            smallest_distance = None
            closest = None
            for path in paths:
                if path.src is None:
                    #Direct path found, we can stop here
                    return None
                if closest is None:
                    closest = path.src
                    smallest_distance = path.src.distance
                    continue
                if path.src.distance < smallest_distance:
                    closest = path.src
                    smallest_distance = path.src.distance
                    continue
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
        return Host(row[0], row[1], row[2], row[3], json.loads(row[4]))

    @classmethod
    def search(cls, field, val, show_all=False):
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
            ret.append(Host(row[0], row[1], row[2], row[3], json.loads(row[4])))
        if not show_all:
            ret = [host for host in ret if host.scope]
        return ret

    def __str__(self):
        return self.name
