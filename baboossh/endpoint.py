import ipaddress
import json
import hashlib
from baboossh import Db
from baboossh import Host
from baboossh.exceptions import *
from baboossh.utils import Unique

class Endpoint(metaclass=Unique):
    """A SSH endpoint

    An Endpoint is a couple of an IP address and a port on which a SSH server is
    (supposed) being run.

    Attributes:
        ip (str): The IP address of the Endpoint
        port (str): The port number of the Endpoint
        id (int): The endpoint id
        host (:class:`.Host`): The Endpoint's :class:`.Host`
        scope (bool): Whether the Endpoint is in scope or not
        reachable (bool): Whether the Endpoint was reached with `path find`
        distance (int): The number of hops to reach the Endpoint
        found (:class:`.Endpoint`): The Endpoint on which the current Endpoint was discovered
    """

    search_fields = ['ip', 'port']

    def __init__(self, ip, port):
        #check if ip is actually an IP
        ipaddress.ip_address(ip)
        if not isinstance(port, int) and not port.isdigit():
            raise ValueError("The port is not a positive integer")

        self.ip = ip
        self.__port = port
        self.host = None
        self.id = None
        self.scope = True
        self.reachable = None
        self.distance = None
        self.found = None
        c = Db.get().cursor()
        c.execute('SELECT id, host, reachable, distance, scope, found FROM endpoints WHERE ip=? AND port=?', (self.ip, self.port))
        savedEndpoint = c.fetchone()
        c.close()
        if savedEndpoint is not None:
            self.id = savedEndpoint[0]
            self.host = Host.find_one(host_id=savedEndpoint[1])
            if savedEndpoint[2] is None:
                self.reachable = None
            else:
                self.reachable = savedEndpoint[2] != 0
            if savedEndpoint[3] is not None:
                self.distance = savedEndpoint[3]
            self.scope = savedEndpoint[4] != 0
            if savedEndpoint[5] is not None :
                self.found = Endpoint.find_one(endpoint_id=savedEndpoint[5])
    
    @classmethod
    def get_id(cls, ip, port):
        return hashlib.sha256((ip+str(port)).encode()).hexdigest()

    @property
    def port(self):
        return int(self.__port)

    @port.setter
    def port(self, port):
        self.__port = int(port)

    @property
    def connection(self):
        from baboossh import Connection
        return Connection.find_one(endpoint=self)

    def save(self):
        """Save the Endpoint in database

        If the Endpoint object has an id it means it is already stored in database,
        so it is updated. Else it is inserted and the id is set in the object.

        """

        c = Db.get().cursor()
        if self.id is not None:
            #If we have an ID, the endpoint is already saved in the database : UPDATE
            c.execute('''UPDATE endpoints 
                SET
                    ip = ?,
                    port = ?,
                    host = ?,
                    reachable = ?,
                    distance = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                (self.ip, self.port, self.host.id if self.host is not None else None, self.reachable, self.distance, self.scope, self.found.id if self.found is not None else None, self.id))
        else:
            #The endpoint doesn't exists in database : INSERT
            c.execute('''INSERT INTO endpoints(ip, port, host, reachable, distance, scope, found)
                VALUES (?, ?, ?, ?, ?, ?, ?) ''',
                (self.ip, self.port, self.host.id if self.host is not None else None, self.reachable, self.distance, self.scope, self.found.id if self.found is not None else None))
            c.close()
            c = Db.get().cursor()
            c.execute('SELECT id FROM endpoints WHERE ip=? AND port=?', (self.ip, self.port))
            self.id  = c.fetchone()[0]
        c.close()
        Db.get().commit()

    def delete(self):
        """Delete an Endpoint from the :class:`.Workspace`"""

        from baboossh import Path
        from baboossh import Connection
        if self.id is None:
            return {}
        from baboossh.utils import unstore_targets_merge
        del_data = {}
        if self.host is not None:
            endpoints = self.host.endpoints
            if len(endpoints) == 1:
                unstore_targets_merge(del_data,self.host.delete())
        for connection in Connection.find_all(endpoint=self):
            unstore_targets_merge(del_data,connection.delete())
        for path in Path.find_all(dst=self):
            unstore_targets_merge(del_data,path.delete())
        c = Db.get().cursor()
        c.execute('DELETE FROM endpoints WHERE id = ?', (self.id, ))
        c.close()
        Db.get().commit()
        unstore_targets_merge(del_data,{"Endpoint":[type(self).get_id(self.ip, self.port)]})
        return del_data

    @classmethod
    def find_all(cls, scope=None, found=None):
        """Find all Endpoints matching the criteria

        Args:
            scope (bool): 
                List Endpoints in scope (`True`), out of scope (`False`), or both (`None`)
            found (:class:`Endpoint`):
                The `Endpoint` the endpoints were discovered on
    
        Returns:
            A list of all `Endpoint`\ s in the :class:`.Workspace`
        """

        ret = []
        c = Db.get().cursor()
        if found is None:
            if scope is None:
                req = c.execute('SELECT ip, port FROM endpoints')
            else:
                req = c.execute('SELECT ip, port FROM endpoints WHERE scope=?', (scope, ))
        else:
            if scope is None:
                req = c.execute('SELECT ip, port FROM endpoints WHERE found=?', (endpoint.id if endpoint is not None else None, ))
            else:
                req = c.execute('SELECT ip, port FROM endpoints WHERE scope=? and found=?', (scope, endpoint.id if endpoint is not None else None))
        for row in req:
            ret.append(Endpoint(row[0], row[1]))
        return ret

    @classmethod
    def find_one(cls, endpoint_id=None, ip_port=None):
        """Find an `Endpoint` by its id or it's IP address:Port

        Args:
            endpoint_id (int): the `Endpoint` id to search
            ip_port (str): The IP and port as "<ip>:<port>"

        Returns:
            A single `Endpoint` or `None`.
        """

        c = Db.get().cursor()

        if endpoint_id is not None:
            if endpoint_id == 0:
                c.close()
                return None
            c.execute('''SELECT ip, port FROM endpoints WHERE id=?''', (endpoint_id, ))
        elif ip_port is not None:
            ip, sep, port = ip_port.partition(":")
            if port == "":
                raise ValueError
            c.execute('''SELECT ip, port FROM endpoints WHERE ip=? and port=?''', (ip, port))
        else:
            c.close()
            return None

        row = c.fetchone()
        c.close()
        if row is None:
            return None
        return Endpoint(row[0], row[1])

    def __str__(self):
        return self.ip+":"+str(self.port)

    @classmethod
    def search(cls, field, val, show_all=False):
        """Search in the workspace for an `Endpoint`

        Args:
            field (str): the `Endpoint` attribute to search in
            val (str): the value to search for
            show_all (bool): whether to include out-of scope `Endpoint`\ s in search results

        Returns:
            A `List` of `Endpoint`\ s corresponding to the search.
        """

        if field not in cls.search_fields:
            raise ValueError
        ret = []
        print(field);
        c = Db.get().cursor()
        val = "%"+val+"%"
        if show_all:
            #Ok this sounds fugly, but there seems to be no way to set a column name in a parameter. The SQL injection risk is mitigated as field must be in allowed fields, but if you find something better I take it
            c.execute('SELECT ip, port FROM endpoints WHERE {} LIKE ?'.format(field), (val, ))
        else:
            c.execute('SELECT ip, port FROM endpoints WHERE scope=? and {} LIKE ?'.format(field), (True, val))
        for row in c:
            ret.append(Endpoint(row[0], row[1]))
        return ret
