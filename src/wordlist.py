import sqlite3
from src.params import dbConn


class Wordlist():
    def __init__(self,name,filename):
        self.name = name
        self.file = filename
        self.id = None
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM wordlists WHERE name=?',(self.name,))
        savedWordlist = c.fetchone()
        c.close()
        if savedWordlist is not None:
            self.id = savedWordlist[0]

    def getId(self):
        return self.id

    def getName(self):
        return self.name

    def getFile(self):
        return self.file

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the wordlist is already saved in the database : UPDATE
            c.execute('''UPDATE wordlists 
                SET
                    name = ?,
                    file = ?,
                WHERE id = ?''',
                (self.name, self.file, self.id))
        else:
            #The wordlist doesn't exists in database : INSERT
            c.execute('''INSERT INTO wordlists(name,file)
                VALUES (?,?) ''',
                (self.name,self.file))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM wordlists WHERE name=?',(self.name,))
            self.id = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    @classmethod
    def findAll(cls):
        ret = []
        c = dbConn.get().cursor()
        for row in c.execute('SELECT name,file FROM wordlists'):
            ret.append(Wordlist(row[0],row[1]))
        return ret

    @classmethod
    def find(cls,wordlistId):
        c = dbConn.get().cursor()
        c.execute('''SELECT name FROM wordlists WHERE id=?''',(wordlistId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Wordlist(row[0])

    @classmethod
    def findByName(cls,name):
        c = dbConn.get().cursor()
        c.execute('''SELECT name,file FROM wordlists WHERE name=?''',(name,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Wordlist(row[0],row[1])


    def toList(self):
        return "<"+self.name+"> "+self.file

    def __str__(self):
        return self.name

