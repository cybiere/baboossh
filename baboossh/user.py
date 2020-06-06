import hashlib
from baboossh import Db
from baboossh.utils import Unique

class User(metaclass=Unique):

    """A username to authenticate with on servers.

    Attributes:
        name (str): the username
        id (int): the User's id
        scope (bool): whether the User is in the scope or not
        found (:class:`.Endpoint`): the endpoint the user was discovered on
    """

    def __init__(self, name):
        self.name = name
        self.id = None
        self.scope = True
        self.found = None
        cursor = Db.get().cursor()
        cursor.execute('SELECT id, scope, found FROM users WHERE username=?', (self.name, ))
        saved_user = cursor.fetchone()
        cursor.close()
        if saved_user is not None:
            self.id = saved_user[0]
            self.scope = saved_user[1] != 0
            if saved_user[2] is not None:
                from baboossh import Endpoint
                self.found = Endpoint.find_one(endpoint_id=saved_user[2])

    @classmethod
    def get_id(cls, name):
        return hashlib.sha256(name.encode()).hexdigest()

    def save(self):
        """Save the user in database

        If the User object has an id it means it is already stored in database,
        so it is updated. Else it is inserted and the id is set in the object.

        """
        cursor = Db.get().cursor()
        if self.id is not None:
            #If we have an ID, the user is already saved in the database : UPDATE
            cursor.execute('''UPDATE users
                SET
                    username = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                           (self.name, self.scope, self.found.id if self.found is not None else None, self.id))
        else:
            #The user doesn't exists in database : INSERT
            cursor.execute('''INSERT INTO users(username, scope, found)
                VALUES (?, ?, ?) ''',
                           (self.name, self.scope, self.found.id if self.found is not None else None))
            cursor.close()
            cursor = Db.get().cursor()
            cursor.execute('SELECT id FROM users WHERE username=?', (self.name, ))
            self.id = cursor.fetchone()[0]
        cursor.close()
        Db.get().commit()

    def delete(self):
        """Delete a User from the :class:`.Workspace`"""

        from baboossh import Connection
        if self.id is None:
            return {}
        from baboossh.utils import unstore_targets_merge
        del_data = {}
        for connection in Connection.find_all(user=self):
            unstore_targets_merge(del_data, connection.delete())
        cursor = Db.get().cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (self.id, ))
        cursor.close()
        Db.get().commit()
        unstore_targets_merge(del_data, {"User":[type(self).get_id(self.name)]})
        return del_data

    @classmethod
    def find_all(cls, scope=None, found=None):
        """Find all Users corresponding to criteria

        Args:
            scope (bool):
                List Users in scope (`True`), out of scope (`False`), or both (`None`)
            found (:class:`.Endpoint`):
                the `Endpoint` the users were discovered on

        Returns:
            A list of all `User` s in the :class:`.Workspace` matching the criteria
        """

        ret = []
        cursor = Db.get().cursor()
        if found is None:
            if scope is None:
                req = cursor.execute('SELECT username FROM users')
            else:
                req = cursor.execute('SELECT username FROM users WHERE scope=?', (scope, ))
        else:
            if scope is None:
                req = cursor.execute('SELECT username FROM users WHERE found=?', (found.id if found is not None else None, ))
            else:
                req = cursor.execute('SELECT username FROM users WHERE found=? AND scope=?', (found.id if found is not None else None, scope))
        for row in req:
            ret.append(User(row[0]))
        cursor.close()
        return ret

    @classmethod
    def find_one(cls, user_id=None, name=None):
        """Find a user matching the criteria

        Args:
            user_id (int): the user id to search
            name (str): the username to search

        Returns:
            A single `User` or `None`.
        """

        cursor = Db.get().cursor()
        if user_id is not None:
            cursor.execute('''SELECT username FROM users WHERE id=?''', (user_id, ))
        elif name is not None:
            cursor.execute('''SELECT username FROM users WHERE username=?''', (name, ))
        else:
            cursor.close()
            return None
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return User(row[0])

    def __str__(self):
        return self.name
