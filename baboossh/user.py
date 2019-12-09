import sqlite3
from baboossh.params import dbConn


class User():
    def __init__(self,name):
        self.name = name
        self.id = None
        self.scope = True
        self.found = None
        c = dbConn.get().cursor()
        c.execute('SELECT id,scope,found FROM users WHERE username=?',(self.name,))
        savedUser = c.fetchone()
        c.close()
        if savedUser is not None:
            self.id = savedUser[0]
            self.scope = savedUser[1] != 0
            if savedUser[2] is not None :
                from baboossh.endpoint import Endpoint
                self.found = Endpoint.find(savedUser[2])

    def getId(self):
        return self.id

    def getName(self):
        return self.name

    def inScope(self):
        return self.scope

    def rescope(self):
        self.scope = True

    def unscope(self):
        self.scope = False

    def getFound(self):
        return self.found

    def setFound(self,found):
        self.found = found

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the user is already saved in the database : UPDATE
            c.execute('''UPDATE users 
                SET
                    username = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                (self.name, self.scope, self.found.getId() if self.found is not None else None, self.id))
        else:
            #The user doesn't exists in database : INSERT
            c.execute('''INSERT INTO users(username,scope,found)
                VALUES (?,?,?) ''',
                (self.name,self.scope, self.found.getId() if self.found is not None else None))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM users WHERE username=?',(self.name,))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        from baboossh.connection import Connection
        if self.id is None:
            return
        for connection in Connection.findByUser(self):
            connection.delete()
        c = dbConn.get().cursor()
        c.execute('DELETE FROM users WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return

    @classmethod
    def findAll(cls, scope=None):
        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT username FROM users')
        else:
            req = c.execute('SELECT username FROM users WHERE scope=?',(scope,))
        for row in req:
            ret.append(User(row[0]))
        return ret

    @classmethod
    def find(cls,userId):
        c = dbConn.get().cursor()
        c.execute('''SELECT username FROM users WHERE id=?''',(userId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return User(row[0])

    @classmethod
    def findByUsername(cls,name):
        c = dbConn.get().cursor()
        c.execute('''SELECT username FROM users WHERE username=?''',(name,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return User(row[0])

    @classmethod
    def findByFound(cls, endpoint, scope=True):
        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT username FROM users WHERE found=?',(endpoint.getId() if endpoint is not None else None,))
        else:
            req = c.execute('SELECT username FROM users WHERE found=? AND scope=?',(endpoint.getId() if endpoint is not None else None,scope))
        for row in req:
            ret.append(User(row[0]))
        return ret



    def __str__(self):
        return self.name

