import sqlite3
from src.params import dbConn

class Connection():
    def __init__(self,host,target,user,cred,wspace):
        self.host = host
        self.target = target
        self.user = user
        self.cred = cred
        self.wspace = wspace
        self.id = None
        self.tested = False
        self.working = False
        self.root = False
        c = dbConn.get().cursor()
        c.execute('SELECT id,tested,working,root FROM connections WHERE host=? AND target=? AND user=? AND cred=?',(self.host.getId(),self.target.getId(),self.user.getId(),self.cred.getId()))
        savedTarget = c.fetchone()
        c.close()
        if savedTarget is not None:
            self.id = savedTarget[0]
            self.tested = savedTarget[1] != 0
            self.working = savedTarget[2] != 0
            self.root = savedTarget[3] != 0

    def getId(self):
        return self.id

    def setTested(self, tested):
        self.tested = tested == True

    def setWorking(self, working):
        self.working = working == True

    def setRoot(self, root):
        self.root = root == True

    def isWorking(self):
        return self.working == True

    def save(self):
        c = dbConn.get().cursor()
        if self.id is not None:
            #If we have an ID, the target is already saved in the database : UPDATE
            c.execute('''UPDATE connections 
                SET
                    host = ?,
                    target= ?,
                    user = ?,
                    cred = ?,
                    tested = ?,
                    working = ?,
                    root = ?
                WHERE id = ?''',
                (self.host.getId(), self.target.getId(), self.user.getId(), self.cred.getId(), 1 if self.tested else 0, 1 if self.working else 0, 1 if self.root else 0, self.id))
        else:
            #The target doesn't exists in database : INSERT
            c.execute('''INSERT INTO connections(host,target,user,cred,tested,working,root)
                VALUES (?,?,?,?,?,?,?) ''',
                (self.host.getId(), self.target.getId(), self.user.getId(), self.cred.getId(), 1 if self.tested else 0, 1 if self.working else 0, 1 if self.root else 0))
            c.close()
            c = dbConn.get().cursor()
            c.execute('SELECT id FROM connections WHERE host=? AND target=? AND user=? AND cred=?',(self.host.getId(),self.target.getId(),self.user.getId(),self.cred.getId()))
            self.id  = c.fetchone()[0]
        c.close()
        dbConn.get().commit()

    def __str__(self):
        return str(self.user)+":"+str(self.cred)+"@"+str(self.target)


