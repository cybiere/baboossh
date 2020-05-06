import sqlite3
import json
from baboossh import dbConn


class Host():
    """A machine with one or several :class:`Endpoint`

    This is used to aggregate endpoints as a single machine can have several
    interfaces with SSH listening on them. In order to prevent unecessary pivots,
    :class:`Path`\ s are calculated using the `Host` as sources as it might be
    longer to reach a `Host` from one endpoint rather than the other.

    The aggregation is checked by :func:`Connection.identify`, which is run on
    every endpoint newly connected. If every `Host` attribute matches with an
    existing Host, the endpoint is considered to belong to it and is added.

    Attributes:
        name (str): the hostname of the Host as returned by the command `hostname`
        id (int): the id of the Host
        uname (str): the output of the command `uname -a` on the Host
        issue (str): the content of the file `/etc/issue` on the Host
        machineId (str): the content of the file `/etc/machine-id` on the Host
        macs ([str,...]): a list of the MAC addresses of the Host interfaces
    """

    search_fields = ['name','uname']

    def __init__(self,name,uname,issue,machineId,macs):
        self.name = name
        self.id = None
        self.uname = uname
        self.issue = issue
        self.machineId = machineId
        self.macs = macs
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM hosts WHERE name=? AND uname=? AND issue=? AND machineid=? AND macs=?',(self.name,self.uname,self.issue,self.machineId,json.dumps(self.macs)))
        savedHost = c.fetchone()
        c.close()
        if savedHost is not None:
            self.id = savedHost[0]

    @property
    def scope(self):
        """Returns whether the `Host` is in scope

        A `Host` is in scope if all its :class:`Endpoint`\ s are in scope
        """

        for e in self.endpoints:
            if not e.scope:
                return False
        return True

    @scope.setter
    def scope(self,scope):
        for e in self.endpoints:
            e.scope = scope
            e.save()

    @property
    def distance(self):
        """Returns the `Host`\ 's number of hops from `"Local"`"""

        c = dbConn.get().cursor()
        c.execute('SELECT distance FROM endpoints WHERE host=? ORDER BY distance DESC',(self.id,))
        row = c.fetchone()
        c.close()
        return row[0];

    @property
    def closest_endpoint(self):
        """Returns the `Host`\ 's closest :class:`Endpoint`"""
        
        c = dbConn.get().cursor()
        c.execute('SELECT ip,port FROM endpoints WHERE host=? ORDER BY distance DESC',(self.id,))
        row = c.fetchone()
        c.close()
        from baboossh import Endpoint
        return Endpoint(row[0],row[1]);

    @property
    def endpoints(self):
        """Returns a `List` of the `Host`\ 's :class:`Endpoint`\ s"""
        from baboossh import Endpoint
        endpoints = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT ip,port FROM endpoints WHERE host=?',(self.id,)):
            endpoints.append(Endpoint(row[0],row[1]))
        c.close()
        return endpoints

    def save(self):
        """Saves the `Host` in the :class:`Workspace`\ 's database"""
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the host is already saved in the database : UPDATE
            c.execute('''UPDATE hosts 
                SET
                    name = ?,
                    uname = ?,
                    issue = ?,
                    machineid = ?,
                    macs = ?
                WHERE id = ?''',
                (self.name, self.uname, self.issue, self.machineId, json.dumps(self.macs), self.id))
        else:
            #The host doesn't exists in database : INSERT
            c.execute('''INSERT INTO hosts(name,uname,issue,machineid,macs)
                VALUES (?,?,?,?,?) ''',
                (self.name,self.uname,self.issue,self.machineId,json.dumps(self.macs)))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM hosts WHERE name=? AND uname=? AND issue=? AND machineid=? AND macs=?',(self.name,self.uname,self.issue,self.machineId,json.dumps(self.macs)))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        """Removes the `Host` from the :class:`Workspace`

        Recursively removes all :class:`Path`\ s starting from this `Host`
        """

        from baboossh import Path
        if self.id is None:
            return
        for path in Path.find_all(src=self):
            path.delete()
        for endpoint in self.endpoints:
            endpoint.host = None
            endpoint.save()
        c = dbConn.get().cursor()
        c.execute('DELETE FROM hosts WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return

    @classmethod
    def find_all(cls,scope=None,name=None):
        """Returns a `List` of all `Host`\ s in the :class:`Workspace` matching the criteria

        Args:
            scope (bool): whether to return only `Host`\s in scope (`True`),
                out of scope (`False`) or both (`None`)
            name (str): the `Host`\ s' name to match

        Returns:
            the `List` of `Host`\ s
        """

        ret = []
        c = dbConn.get().cursor()
        if name is None:
            req = c.execute('SELECT name,uname,issue,machineId,macs FROM hosts')
        else:
            req = c.execute('''SELECT name,uname,issue,machineId,macs FROM hosts WHERE name=?''',(name,))
        for row in req:
            h = Host(row[0],row[1],row[2],row[3],json.loads(row[4]))
            if scope is None:
                ret.append(h)
            elif h.scope == scope:
                ret.append(h)
        c.close()
        return ret

    @classmethod
    def find_one(cls,host_id=None,name=None):
        """Find a `Host` by its id

        Args:
            host_id (int): the desired `Host`\ 's id
            name (str): the `Host`\ 's name to match

        Returns:
            A `Host` or `None`
        """

        c = dbConn.get().cursor()
        if host_id is not None:
            c.execute('''SELECT name,uname,issue,machineId,macs FROM hosts WHERE id=?''',(host_id,))
        elif name is not None:
            c.execute('''SELECT name,uname,issue,machineId,macs FROM hosts WHERE name=?''',(name,))
        else:
            c.close()
            return None

        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Host(row[0],row[1],row[2],row[3],json.loads(row[4]))

    @classmethod
    def search(cls,field,val,showAll=False):
        """Search in the workspace for a `Host`

        Args:
            field (str): the `Host` attribute to search in
            val (str): the value to search for
            showAll (bool): whether to include out-of scope `Host`\ s in search results

        Returns:
            A `List` of `Host`\ s corresponding to the search.
        """

        if field not in cls.search_fields:
            raise ValueError
        ret = []
        print(field);
        c = dbConn.get().cursor()
        val = "%"+val+"%"
        #Ok this sounds fugly, but there seems to be no way to set a column name in a parameter. The SQL injection risk is mitigated as field must be in allowed fields, but if you find something better I take it
        c.execute('SELECT name,uname,issue,machineId,macs FROM hosts WHERE {} LIKE ?'.format(field),(val,))
        for row in c:
            ret.append(Host(row[0],row[1],row[2],row[3],json.loads(row[4])))
        return ret

    def __str__(self):
        return self.name
