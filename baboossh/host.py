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

    def getId(self):
        """Returns the `Host` id"""
        return self.id

    def getName(self):
        """Returns the `Host` name"""
        return self.name

    def getUname(self):
        """Returns the `Host` uname"""
        return self.uname

    def getIssue(self):
        """Returns the `Host` issue"""
        return self.issue

    def getMachineId(self):
        """Returns the `Host` machine-id"""
        return self.machineId

    def getMacs(self):
        """Returns the `Host` macs"""
        return self.macs

    def inScope(self):
        """Returns whether the `Host` is in scope

        A `Host` is in scope if all its :class:`Endpoint`\ s are in scope
        """

        for e in self.getEndpoints():
            if not e.inScope():
                return False
        return True

    def rescope(self):
        """Add the `Host` and all its :class:`Endpoint`\ s to scope"""
        for e in self.getEndpoints():
            e.rescope()
            e.save()

    def unscope(self):
        """Remove the `Host` and all its :class:`Endpoint`\ s from scope"""
        for e in self.getEndpoints():
            e.unscope()
            e.save()

    def getDistance(self):
        """Returns the `Host`\ 's number of hops from `"Local"`"""

        c = dbConn.get().cursor()
        c.execute('SELECT distance FROM endpoints WHERE host=? ORDER BY distance DESC',(self.id,))
        row = c.fetchone()
        c.close()
        return row[0];

    def getClosestEndpoint(self):
        """Returns the `Host`\ 's closest :class:`Endpoint`"""
        
        c = dbConn.get().cursor()
        c.execute('SELECT ip,port FROM endpoints WHERE host=? ORDER BY distance DESC',(self.id,))
        row = c.fetchone()
        c.close()
        from baboossh import Endpoint
        return Endpoint(row[0],row[1]);

    def getEndpoints(self):
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
        for path in Path.findBySrc(self):
            path.delete()
        for endpoint in self.getEndpoints():
            endpoint.setHost(None)
            endpoint.save()
        c = dbConn.get().cursor()
        c.execute('DELETE FROM hosts WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return

    @classmethod
    def findAll(cls,scope=None):
        """Returns a `List` of all `Host`\ s in the :class:`Workspace`

        Args:
            scope (bool): whether to return only `Host`\s in scope (`True`),
                out of scope (`False`) or both (`None`)

        Returns:
            the `List` of `Host`\ s
        """

        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT name,uname,issue,machineId,macs FROM hosts'):
            h = Host(row[0],row[1],row[2],row[3],json.loads(row[4]))
            if scope is None:
                ret.append(h)
            elif h.inScope() == scope:
                ret.append(h)
        c.close()
        return ret

    @classmethod
    def find(cls,hostId):
        """Find a `Host` by its id

        Args:
            hostId (int): the desired `Host`\ 's id

        Returns:
            A `Host` or `None`
        """

        c = dbConn.get().cursor()
        c.execute('''SELECT name,uname,issue,machineId,macs FROM hosts WHERE id=?''',(hostId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Host(row[0],row[1],row[2],row[3],json.loads(row[4]))

    @classmethod
    def findByName(cls,name):
        """Find `Host`\ s by name

        Args:
            name (int): the desired `Host`\ 's name

        Returns:
            A `List` of `Host`\ s with the name `name`
        """

        c = dbConn.get().cursor()
        hosts = []
        for row in c.execute('''SELECT id FROM hosts WHERE name=?''',(name,)):
            hosts.append(Host.find(row[0]))
        c.close()
        return hosts

    @classmethod
    def findAllNames(cls,scope=None):
        """Returns a `List` of all `Host`\ s' `names` in the :class:`Workspace`

        Args:
            scope (bool): whether to return only `Host`\s in scope (`True`),
                out of scope (`False`) or both (`None`)

        Returns:
            the `List` of `str` of the `Host`\ s' names
        """

        ret = []
        hosts = Host.findAll(scope=scope)
        for host in hosts:
            ret.append(host.getName())
        return ret

    @classmethod
    def getSearchFields(cls):
        """List available fields to perform a search on
        
        Returns:
            A list of `str` corresponding to the searchable attributes' names
        """

        return ['name','uname']

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

        if field not in cls.getSearchFields():
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
