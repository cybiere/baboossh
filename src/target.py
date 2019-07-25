import sqlite3
from src.host import Host

class Target():
    def __init__(self,ip,port,host,conn):
        self.ip = ip
        self.port = port
        self.host = host
        self.conn = conn
        self.id = None
        c = self.conn.cursor()
        c.execute('SELECT id FROM targets WHERE ip=? AND port=?',(self.ip,self.port))
        savedTarget = c.fetchone()
        c.close()
        if savedTarget is not None:
            self.id = savedTarget[0]

    def getId(self):
        return self.id

    def save(self):
        c = self.conn.cursor()
        if self.id is not None:
            #If we have an ID, the target is already saved in the database : UPDATE
            c.execute('''UPDATE targets 
                SET
                    ip = ?,
                    port = ?
                    host = ?
                WHERE id = ?''',
                (self.ip, self.port, self.host.getId(), self.id))
        else:
            #The target doesn't exists in database : INSERT
            c.execute('''INSERT INTO targets(ip,port,host)
                VALUES (?,?,?) ''',
                (self.ip,self.port,self.host.getId()))
            c.close()
            c = self.conn.cursor()
            c.execute('SELECT id FROM targets WHERE ip=? AND port=?',(self.ip,self.port))
            self.id  = c.fetchone()[0]
        c.close()
        self.conn.commit()


