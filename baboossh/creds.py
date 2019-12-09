import sqlite3
from baboossh.params import dbConn,Extensions


class Creds():
    def __init__(self,credsType,credsContent):
        self.credsType = credsType
        self.credsContent = credsContent
        self.obj = Extensions.getAuthMethod(credsType)(credsContent)
        self.id = None
        self.scope = True
        self.found = None
        c = dbConn.get().cursor()
        c.execute('SELECT id,scope,found FROM creds WHERE type=? AND identifier=?',(self.credsType, self.obj.getIdentifier()))
        savedCreds = c.fetchone()
        c.close()
        if savedCreds is not None:
            self.id = savedCreds[0]
            self.scope = savedCreds[1] != 0
            if savedCreds[2] is not None :
                from baboossh.endpoint import Endpoint
                self.found = Endpoint.find(savedCreds[2])

    def getId(self):
        return self.id

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
            #If we have an ID, the creds is already saved in the database : UPDATE
            c.execute('''UPDATE creds 
                SET
                    type = ?,
                    content = ?,
                    identifier = ?,
                    scope = ?,
                    found = ?
                WHERE id = ?''',
                (self.credsType, self.credsContent, self.obj.getIdentifier(), self.scope, self.found.getId() if self.found is not None else None, self.id))
        else:
            #The creds doesn't exists in database : INSERT
            c.execute('''INSERT INTO creds(type,content,identifier,scope,found)
                VALUES (?,?,?,?,?) ''',
                (self.credsType, self.credsContent, self.obj.getIdentifier(),self.scope, self.found.getId() if self.found is not None else None))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM creds WHERE type=? and identifier=?',(self.credsType,self.obj.getIdentifier()))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def delete(self):
        from baboossh.connection import Connection
        if self.id is None:
            return
        for connection in Connection.findByCreds(self):
            connection.delete()
        self.obj.delete()
        c = dbConn.get().cursor()
        c.execute('DELETE FROM creds WHERE id = ?',(self.id,))
        c.close()
        dbConn.get().commit()
        return


    def getKwargs(self):
        return self.obj.getKwargs()

    @classmethod
    def findAll(cls, scope=None):
        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT type,content FROM creds')
        else:
            req = c.execute('SELECT type,content FROM creds WHERE scope=?',(scope,))
        for row in req:
            ret.append(Creds(row[0],row[1]))
        return ret

    @classmethod
    def find(cls,credId):
        c = dbConn.get().cursor()
        c.execute('''SELECT type,content FROM creds WHERE id=?''',(credId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Creds(row[0],row[1])

    @classmethod
    def findByFound(cls, endpoint, scope=None):
        ret = []
        c = dbConn.get().cursor()
        if scope is None:
            req = c.execute('SELECT type,content FROM creds WHERE found=?',(endpoint.getId() if endpoint is not None else None,))
        else:
            req = c.execute('SELECT type,content FROM creds WHERE found=? AND scope=?',(endpoint.getId() if endpoint is not None else None,scope))
        for row in req:
            ret.append(Creds(row[0],row[1]))
        return ret

    def show(self):
        self.obj.show()

    def edit(self):
        self.obj.edit()
        self.credsContent = self.obj.serialize()
        self.save()

    def __str__(self):
        return "#"+str(self.getId())

    def getIdentifier(self):
        return self.obj.getIdentifier()

