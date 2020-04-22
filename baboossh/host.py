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
        return self.id

    def getName(self):
        return self.name

    def getUname(self):
        return self.uname

    def getIssue(self):
        return self.issue

    def getMachineId(self):
        return self.machineId

    def getMacs(self):
        return self.macs

    def inScope(self):
        for e in self.getEndpoints():
            if not e.inScope():
                return False
        return True

    def rescope(self):
        for e in self.getEndpoints():
            e.rescope()
            e.save()

    def unscope(self):
        for e in self.getEndpoints():
            e.unscope()
            e.save()

    def getClosestEndpoint(self):
        from baboossh import Path
        endpoints = self.getEndpoints()
        shortestLen = None
        shortest = None
        for endpoint in endpoints:
            if Path.hasDirectPath(endpoint):
                return endpoint
            chain = Path.getPath(None,endpoint)
            if shortestLen is None or len(chain) < shortestLen:
                shortest = endpoint
                shortestLen = len(chain)
        return shortest

    def getEndpoints(self):
        from baboossh import Endpoint
        endpoints = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT ip,port FROM endpoints WHERE host=?',(self.id,)):
            endpoints.append(Endpoint(row[0],row[1]))
        c.close()
        return endpoints

    def save(self):
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
        c = dbConn.get().cursor()
        c.execute('''SELECT name,uname,issue,machineId,macs FROM hosts WHERE id=?''',(hostId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Host(row[0],row[1],row[2],row[3],json.loads(row[4]))

    @classmethod
    def findByName(cls,name):
        c = dbConn.get().cursor()
        hosts = []
        for row in c.execute('''SELECT id FROM hosts WHERE name=?''',(name,)):
            hosts.append(Host.find(row[0]))
        c.close()
        return hosts

    @classmethod
    def findAllNames(cls,scope=None):
        ret = []
        hosts = Host.findAll(scope=scope)
        for host in hosts:
            ret.append(host.getName())
        return ret

    @classmethod
    def getSearchFields(cls):
        return ['name','uname']

    @classmethod
    def search(cls,field,val,showAll=False):
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

