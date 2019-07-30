import sqlite3
import configparser
from os.path import join,exists

config = configparser.ConfigParser()
config.read('config.ini')
if "DEFAULT" not in config or "workspaces" not in config['DEFAULT']:
    print("Invalid config file")
    exit()


class dbConn():
    __conn=None

    @classmethod
    def get(cls):
        if cls.__conn is None:
            raise ValueError("Trying to use unconnected database")
        return cls.__conn

    @classmethod
    def build(cls):
        dbPath = join(config['DEFAULT']['workspaces'],workspace,"workspace.db")
        c = sqlite3.connect(dbPath)
        c.execute('''CREATE TABLE hosts (
            id INTEGER PRIMARY KEY ASC,
            name TEXT NOT NULL,
            identifier TEXT
            )''')
        c.execute('''CREATE TABLE targets (
            id INTEGER PRIMARY KEY ASC,
            host INTEGER NOT NULL,
            ip TEXT NOT NULL,
            port TEXT NOT NULL,
            FOREIGN KEY(host) REFERENCES hosts(id)
            )''')
        c.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY ASC,
            username TEXT NOT NULL
            )''')
        c.execute('''CREATE TABLE creds (
            id INTEGER PRIMARY KEY ASC,
            type TEXT NOT NULL,
            content TEXT NOT NULL
            )''')
        c.execute('''CREATE TABLE connections (
            id INTEGER PRIMARY KEY ASC,
            tested INTEGER NOT NULL,
            working INTEGER NOT NULL,
            root INTEGER NOT NULL,
            host INTEGER NOT NULL,
            target INTEGER NOT NULL,
            user INTEGER NOT NULL,
            cred INTEGER NOT NULL,
            FOREIGN KEY(host) REFERENCES hosts(id)
            FOREIGN KEY(target) REFERENCES targets(id)
            FOREIGN KEY(user) REFERENCES users(id)
            FOREIGN KEY(cred) REFERENCES creds(id)
            )''')
        c.commit()
        c.close()

    @classmethod
    def connect(cls,workspace):
        if cls.__conn is not None:
            cls.__conn.close()
        dbPath = join(config['DEFAULT']['workspaces'],workspace,"workspace.db")
        if not exists(dbPath):
            raise ValueError("Workspace database not found, the workspace must be corrupted !")
        cls.__conn = sqlite3.connect(dbPath)

    @classmethod
    def close(cls):
        cls.__conn.close()
        cls.__conn = None


