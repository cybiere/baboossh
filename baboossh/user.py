from baboossh import dbConn

class User():

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
        cursor = dbConn.get().cursor()
        cursor.execute('SELECT id, scope, found FROM users WHERE username=?', (self.name, ))
        saved_user = cursor.fetchone()
        cursor.close()
        if saved_user is not None:
            self.id = saved_user[0]
            self.scope = saved_user[1] != 0
            if saved_user[2] is not None:
                from baboossh import Endpoint
                self.found = Endpoint.find(saved_user[2])

    def save(self):
        """Save the user in database

        If the User object has an id it means it is already stored in database,
        so it is updated. Else it is inserted and the id is set in the object.

        """
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the user is already saved in the database : UPDATE
            c.execute('''UPDATE users 
                SET
                    username = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                (self.name, self.scope, self.found.id if self.found is not None else None, self.id))
        else:
            #The user doesn't exists in database : INSERT
            c.execute('''INSERT INTO users(username, scope, found)
                VALUES (?, ?, ?) ''',
                (self.name, self.scope, self.found.id if self.found is not None else None))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM users WHERE username=?', (self.name, ))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        """Delete a User from the :class:`.Workspace`"""

        from baboossh import Connection
        if self.id is None:
            return
        for connection in Connection.findByUser(self):
            connection.delete()
        c = dbConn.get().cursor()
        c.execute('DELETE FROM users WHERE id = ?', (self.id, ))
        c.close()
        dbConn.get().commit()
        return

    @classmethod
    def findAll(cls, scope=None):
        """Find all Users

        Args:
            scope (bool): List Users in scope (`True`), out of scope (`False`), or both (`None`)
    
        Returns:
            A list of all `User`\ s in the :class:`.Workspace`
        """

        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT username FROM users')
        else:
            req = c.execute('SELECT username FROM users WHERE scope=?', (scope, ))
        for row in req:
            ret.append(User(row[0]))
        return ret

    @classmethod
    def find(cls, userId):
        """Find a user by its id

        Args:
            userId (int): the user id to search

        Returns:
            A single `User` or `None`.
        """

        c = dbConn.get().cursor()
        c.execute('''SELECT username FROM users WHERE id=?''', (userId, ))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return User(row[0])

    @classmethod
    def findByUsername(cls, name: str):
        """Find a user by its username

        Args:
            name (str): the username to search
        
        Returns:
            A single `User` or `None`.
        """ 
        
        c = dbConn.get().cursor()
        c.execute('''SELECT username FROM users WHERE username=?''', (name, ))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return User(row[0])

    @classmethod
    def findByFound(cls, endpoint, scope=True):
        """Find users found on an `Endpoint`

        When a user is found by `gather` payload, the endpoint he was found on is
        saved. This functions finds and returns users discovered on a given endpoint.

        Args:
            endpoint (:class:`.Endpoint`):
                the `Endpoint` the users were discovered on
            scope (bool):
                look only for user in scope (`True`), out of scope (`False`) or vboth (`None`)

        Returns:
            A list of `User`\ s found on given endpoint.
        """

        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT username FROM users WHERE found=?', (endpoint.id if endpoint is not None else None, ))
        else:
            req = c.execute('SELECT username FROM users WHERE found=? AND scope=?', (endpoint.id if endpoint is not None else None, scope))
        for row in req:
            ret.append(User(row[0]))
        return ret

    def __str__(self):
        return self.name

