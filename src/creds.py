import sqlite3


class Creds():
    def __init__(self,creds,conn):
        self.obj = creds
        self.conn = conn
        self.id = None
        c = self.conn.cursor()
        c.execute('SELECT id FROM creds WHERE type=? AND content=?',(self.obj.getKey(), self.obj.serialize()))
        savedCreds = c.fetchone()
        c.close()
        if savedCreds is not None:
            self.id = savedCreds[0]

    def getId(self):
        return self.id

    def save(self):
        c = self.conn.cursor()
        if self.id is not None:
            #If we have an ID, the creds is already saved in the database : UPDATE
            c.execute('''UPDATE creds 
                SET
                    type = ?,
                    content = ?,
                WHERE id = ?''',
                (self.obj.getKey(), self.obj.serialize(), self.id))
        else:
            #The creds doesn't exists in database : INSERT
            c.execute('''INSERT INTO creds(type,content)
                VALUES (?,?) ''',
                (self.obj.getKey(), self.obj.serialize()))
            c.close()
            c = self.conn.cursor()
            c.execute('SELECT id FROM creds WHERE type=? and content=?',(self.obj.getKey(),self.obj.serialize()))
            self.id = c.fetchone()[0]
        c.close()
        self.conn.commit()

    def toList(self):
        print(" #"+str(self.id)+" <"+self.obj.getKey()+"> "+self.obj.toList())


