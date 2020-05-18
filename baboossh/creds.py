import hashlib
from baboossh import Db, Extensions
from baboossh.utils import Unique


class Creds(metaclass=Unique):
    """The credentials to authenticate with on servers.

    The Creds class is an interface to handle various :class:`Extension` s for
    different authentication methods. It provides a set of methods that are
    agnostic of the underlying method, and delegate dedicated work to the
    corresponding :class:`Extension`

    Attributes:
        creds_type (str): the key of the corresponding authentication method
            extension
        creds_content (str): the credentials content as serialized by the method's
            extension class
        obj (Object): the credentials as an Object corresponding to its type
        id (int): the credentials id
        scope (bool): Whether the `Creds` is in scope or not
        found (:class:`.Endpoint`): The Endpoint on which the `Creds` was discovered
    """

    def __init__(self, creds_type, creds_content):
        self.creds_type = creds_type
        self.creds_content = creds_content
        self.obj = Extensions.auths[creds_type](creds_content)
        self.id = None
        self.scope = True
        self.found = None
        cursor = Db.get().cursor()
        cursor.execute('SELECT id, scope, found FROM creds WHERE type=? AND identifier=?', (self.creds_type, self.obj.identifier))
        saved_creds = cursor.fetchone()
        cursor.close()
        if saved_creds is not None:
            self.id = saved_creds[0]
            self.scope = saved_creds[1] != 0
            if saved_creds[2] is not None:
                from baboossh import Endpoint
                self.found = Endpoint.find_one(endpoint_id=saved_creds[2])

    @classmethod
    def get_id(cls, creds_type, creds_content):
        obj = Extensions.auths[creds_type](creds_content)
        return hashlib.sha256((creds_type+obj.identifier).encode()).hexdigest()

    def save(self):
        """Save the `Creds` to the :class:`Workspace` 's database"""
        cursor = Db.get().cursor()
        if self.id is not None:
            #If we have an ID, the creds is already saved in the database : UPDATE
            cursor.execute('''UPDATE creds
                SET
                    type = ?,
                    content = ?,
                    identifier = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                           (self.creds_type, self.creds_content, self.obj.identifier, self.scope, self.found.id if self.found is not None else None, self.id))
        else:
            #The creds doesn't exists in database : INSERT
            cursor.execute('''INSERT INTO creds(type, content, identifier, scope, found)
                VALUES (?, ?, ?, ?, ?) ''',
                           (self.creds_type, self.creds_content, self.obj.identifier, self.scope, self.found.id if self.found is not None else None))
            cursor.close()
            cursor = Db.get().cursor()
            cursor.execute('SELECT id FROM creds WHERE type=? and identifier=?', (self.creds_type, self.obj.identifier))
            self.id = cursor.fetchone()[0]
        cursor.close()
        Db.get().commit()

    def delete(self):
        """Delete a `Creds` from the :class:`.Workspace`"""
        from baboossh import Connection
        if self.id is None:
            return {}
        from baboossh.utils import unstore_targets_merge
        del_data = {}
        for connection in Connection.find_all(creds=self):
            unstore_targets_merge(del_data, connection.delete())
        self.obj.delete()
        cursor = Db.get().cursor()
        cursor.execute('DELETE FROM creds WHERE id = ?', (self.id, ))
        cursor.close()
        Db.get().commit()
        unstore_targets_merge(del_data, {"Creds":[type(self).get_id(self.creds_type, self.creds_content)]})
        return del_data

    @property
    def kwargs(self):
        """Return the `Creds` as a dict compatible with `fabric.Connection`"""
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
        cursor = Db.get().cursor()
        if found is None:
            if scope is None:
                req = cursor.execute('SELECT type, content FROM creds')
            else:
                req = cursor.execute('SELECT type, content FROM creds WHERE scope=?', (scope, ))
        else:
            if scope is None:
                req = cursor.execute('SELECT type, content FROM creds WHERE found=?', (found.id, ))
            else:
                req = cursor.execute('SELECT type, content FROM creds WHERE found=? AND scope=?', (found.id, scope))
        for row in req:
            ret.append(Creds(row[0], row[1]))
        return ret

    @classmethod
    def find_one(cls, creds_id):
        """Find a `Creds` by its id

        Args:
            creds_id (int): the `Creds` id to search

        Returns:
            A single `Creds` or `None`.
        """

        cursor = Db.get().cursor()
        cursor.execute('''SELECT type, content FROM creds WHERE id=?''', (creds_id, ))
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return Creds(row[0], row[1])

    def show(self):
        """Show the `Creds` object and its parameters"""
        self.obj.show()

    def edit(self):
        """Edit the `Creds` object parameters"""
        self.obj.edit()
        self.creds_content = self.obj.serialize()
        self.save()

    def __str__(self):
        return "#"+str(self.id)
