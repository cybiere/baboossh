import sqlite3
from baboossh import dbConn,Extensions


class Creds():
    """The credentials to authenticate with on servers.

    The Creds class is an interface to handle various :class:`Extension`\ s for
    different authentication methods. It provides a set of methods that are
    agnostic of the underlying method, and delegate dedicated work to the
    corresponding :class:`Extension`

    Attributes:
        credsType (str): the key of the corresponding authentication method
            extension
        credsContent (str): the credentials content as serialized by the method's
            extension class
        obj (Object): the credentials as an Object corresponding to its type
        id (int): the credentials id
        scope (bool): Whether the `Creds` is in scope or not
        found (:class:`.Endpoint`): The Endpoint on which the `Creds` was discovered
    """

    def __init__(self,credsType,credsContent):
        self.credsType = credsType
        self.credsContent = credsContent
        self.obj = Extensions.getAuthMethod(credsType)(credsContent)
        self.id = None
        self.scope = True
        self.found = None
        c = dbConn.get().cursor()
        c.execute('SELECT id,scope,found FROM creds WHERE type=? AND identifier=?',(self.credsType, self.obj.identifier))
        savedCreds = c.fetchone()
        c.close()
        if savedCreds is not None:
            self.id = savedCreds[0]
            self.scope = savedCreds[1] != 0
            if savedCreds[2] is not None :
                from baboossh import Endpoint
                self.found = Endpoint.find_one(endpoint_id=savedCreds[2])

    def save(self):
        """Save the `Creds` to the :class:`Workspace`\ 's database"""
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the creds is already saved in the database : UPDATE
            c.execute('''UPDATE creds 
                SET
                    type = ?,
                    content = ?,
                    identifier = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                (self.credsType, self.credsContent, self.obj.identifier, self.scope, self.found.id if self.found is not None else None, self.id))
        else:
            #The creds doesn't exists in database : INSERT
            c.execute('''INSERT INTO creds(type,content,identifier,scope,found)
                VALUES (?,?,?,?,?) ''',
                (self.credsType, self.credsContent, self.obj.identifier,self.scope, self.found.id if self.found is not None else None))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM creds WHERE type=? and identifier=?',(self.credsType,self.obj.identifier))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        """Delete a `Creds` from the :class:`.Workspace`"""
        from baboossh import Connection
        if self.id is None:
            return
        for connection in Connection.find_all(creds=self):
            connection.delete()
        self.obj.delete()
        c = dbConn.get().cursor()
        c.execute('DELETE FROM creds WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return

    @property
    def kwargs(self):
        """Return the `Creds` as a dict compatible with `asyncssh.connect`"""
        return self.obj.getKwargs()

    @classmethod
    def find_all(cls, scope=None, found=None):
        """Find all `Creds`

        Args:
            scope (bool): List `Creds` in scope (`True`), out of scope 
                (`False`), or both (`None`)
            found (:class:`Endpoint`):
                the `Endpoint` the `Creds` were discovered on
    
        Returns:
            A list of all `Creds` in the :class:`.Workspace`
        """

        ret = []
        c = dbConn.get().cursor()
        if found is None:
            if scope is None:
                req = c.execute('SELECT type,content FROM creds')
            else:
                req = c.execute('SELECT type,content FROM creds WHERE scope=?',(scope,))
        else:
            if scope is None:
                req = c.execute('SELECT type,content FROM creds WHERE found=?',(endpoint.id if endpoint is not None else None,))
            else:
                req = c.execute('SELECT type,content FROM creds WHERE found=? AND scope=?',(endpoint.id if endpoint is not None else None,scope))
        for row in req:
            ret.append(Creds(row[0],row[1]))
        return ret

    @classmethod
    def find_one(cls,creds_id):
        """Find a `Creds` by its id

        Args:
            creds_id (int): the `Creds` id to search

        Returns:
            A single `Creds` or `None`.
        """

        c = dbConn.get().cursor()
        c.execute('''SELECT type,content FROM creds WHERE id=?''',(creds_id,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Creds(row[0],row[1])

    def show(self):
        """Show the `Creds` object and its parameters"""
        self.obj.show()

    def edit(self):
        """Edit the `Creds` object parameters"""
        self.obj.edit()
        self.credsContent = self.obj.serialize()
        self.save()

    def __str__(self):
        return "#"+str(self.id)

