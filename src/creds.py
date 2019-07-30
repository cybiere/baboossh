import sqlite3
from src.params import dbConn,Extensions


class Creds():
    def __init__(self,credsType,credsContent,wspace):
        self.credsType = credsType
        self.credsContent = credsContent
        self.wspace = wspace
        self.obj = Extensions.authMethods(credsType)(credsContent)
        self.id = None
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM creds WHERE type=? AND content=?',(self.credsType, self.credsContent))
        savedCreds = c.fetchone()
        c.close()
        if savedCreds is not None:
            self.id = savedCreds[0]

    def getId(self):
        return self.id

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the creds is already saved in the database : UPDATE
            c.execute('''UPDATE creds 
                SET
                    type = ?,
                    content = ?,
                WHERE id = ?''',
                (self.credsType, self.credsContent, self.id))
        else:
            #The creds doesn't exists in database : INSERT
            c.execute('''INSERT INTO creds(type,content)
                VALUES (?,?) ''',
                (self.credsType, self.credsContent))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM creds WHERE type=? and content=?',(self.credsType,self.credsContent))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def getKwargs(self):
        return self.obj.getKwargs()

    def toList(self):
        print(" #"+str(self.id)+" <"+self.obj.getKey()+"> "+self.obj.toList())

    def __str__(self):
        return "#"+str(self.id)

