import sqlite3
from src.params import dbConn


class Host():
    def __init__(self,name):
        from src.target import Target
        self.name = name
        self.id = None
        self.identifier = ""
        self.targets = []
        c = dbConn.get().cursor()
        c.execute('SELECT id,identifier FROM hosts WHERE name=?',(self.name,))
        savedHost = c.fetchone()
        c.close()
        if savedHost is not None:
            self.id, self.identifier = savedHost
            c = dbConn.get().cursor()
            for row in c.execute('''SELECT ip,port FROM targets WHERE host=?''',(self.id,)):
                self.targets.append(Target(row[0],row[1],self))
            c.close()

    def getId(self):
        return self.id

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the host is already saved in the database : UPDATE
            c.execute('''UPDATE hosts 
                SET
                    name = ?,
                    identifier = ?
                WHERE id = ?''',
                (self.name, self.identifier, self.id))
        else:
            #The host doesn't exists in database : INSERT
            c.execute('''INSERT INTO hosts(name,identifier)
                VALUES (?,?) ''',
                (self.name,self.identifier))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id,identifier FROM hosts WHERE name=?',(self.name,))
            self.id = c.fetchone()[0]
            self.targets = []
            c = dbConn.get().cursor()
            for row in c.execute('''SELECT ip,port FROM targets WHERE host=?''',(self.id,)):
                self.targets.append(Target(row[0],row[1],self))
            c.close()
        c.close()
        dbConn.get().commit()

    def registerTarget(self,target):
        self.targets.append(target)

    @classmethod
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT name FROM hosts'):
            ret.append(Host(row[0]))
        return ret

    @classmethod
    def find(cls,hostId):
        c = dbConn.get().cursor()
        c.execute('''SELECT name FROM hosts WHERE id=?''',(hostId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Host(row[0])

    def toList(self):
        listStr = "<"+self.name+">"
        for target in self.targets:
            listStr = listStr+"\n\t- "+target.toList()
        return listStr
    
    def __str__(self):
        return self.name

