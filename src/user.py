import sqlite3


class User():
    def __init__(self,name,conn):
        self.name = name
        self.conn = conn
        self.id = None
        c = self.conn.cursor()
        c.execute('SELECT id FROM users WHERE username=?',(self.name,))
        savedUser = c.fetchone()
        c.close()
        if savedUser is not None:
            self.id = savedUser[0]

    def getId(self):
        return self.id

    def getName(self):
        return self.name

    def save(self):
        c = self.conn.cursor()
        if self.id is not None:
            #If we have an ID, the user is already saved in the database : UPDATE
            c.execute('''UPDATE users 
                SET
                    username = ?,
                WHERE id = ?''',
                (self.name, self.id))
        else:
            #The user doesn't exists in database : INSERT
            c.execute('''INSERT INTO users(username)
                VALUES (?) ''',
                (self.name,))
            c.close()
            c = self.conn.cursor()
            c.execute('SELECT id FROM users WHERE username=?',(self.name,))
            self.id = c.fetchone()[0]
        c.close()
        self.conn.commit()

    def toList(self):
        print("<"+self.name+">")

    def __str__(self):
        return self.name

