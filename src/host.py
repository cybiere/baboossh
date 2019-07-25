import sqlite3

class Host():
    def __init__(self,name,conn):
        self.name = name
        self.conn = conn
        self.id = None
        self.identifier = ""
        c = self.conn.cursor()
        c.execute('SELECT id,identifier FROM hosts WHERE name=?',(self.name,))
        savedHost = c.fetchone()
        c.close()
        if savedHost is not None:
            self.id, self.identifier = savedHost

    def getId(self):
        return self.id

    def save(self):
        c = self.conn.cursor()
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
            c = self.conn.cursor()
            c.execute('SELECT id,identifier FROM hosts WHERE name=?',(self.name,))
            self.id = c.fetchone()[0]
        c.close()
        self.conn.commit()

    def toList(self):
        print("<"+self.name+">")


