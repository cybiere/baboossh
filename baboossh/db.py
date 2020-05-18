import sqlite3
import threading
import os
from baboossh.utils import workspacesDir

class Db():
    """A singleton handling the database connection

    This class allows the use of a single sqlite connection for earch thread
    """

    __conn=None
    __threadsConn={}
    __workspace=None

    @classmethod
    def get(cls):
        """Returns the database connection for the current thread

        If the current thread isn't the main and no connection is already
        opened, opens a new one and returns it

        Returns:
            An open :class:`sqlite3.Connection`
        """

        mainThreadName = threading.main_thread().getName()
        currentName = threading.currentThread().getName()
        if currentName != mainThreadName:
            if currentName in cls.__threadsConn.keys():
                return cls.__threadsConn[currentName]
            else:
                cls.connect(cls.__workspace)
                return cls.__threadsConn[currentName]
        if cls.__conn is None:
            raise ValueError("Trying to use unconnected database")
        return cls.__conn

    @classmethod
    def build(cls, workspace):
        """Create the databases and the tables for a new :class:`Workspace`

        Args:
            workspace (str): the workspace's name
        """

        dbPath = os.path.join(workspacesDir, workspace, "workspace.db")
        c = sqlite3.connect(dbPath)
        c.execute('''CREATE TABLE hosts (
            id INTEGER PRIMARY KEY ASC,
            name TEXT NOT NULL UNIQUE,
            hostname TEXT,
            uname TEXT,
            issue TEXT,
            machineid TEXT,
            macs TEXT
            )''')
        c.execute('''CREATE TABLE endpoints (
            id INTEGER PRIMARY KEY ASC,
            scope INTEGER NOT NULL,
            host INTEGER,
            ip TEXT NOT NULL,
            port TEXT NOT NULL,
            reachable INTEGER,
            distance INTEGER,
            found INTEGER,
            FOREIGN KEY(found) REFERENCES endpoints(id),
            FOREIGN KEY(host) REFERENCES hosts(id)
            )''')
        c.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY ASC,
            scope INTEGER NOT NULL,
            username TEXT NOT NULL,
            found INTEGER,
            FOREIGN KEY(found) REFERENCES endpoints(id)
            )''')
        c.execute('''CREATE TABLE creds (
            id INTEGER PRIMARY KEY ASC,
            scope INTEGER NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            identifier TEXT NOT NULL,
            found INTEGER,
            FOREIGN KEY(found) REFERENCES endpoints(id)
            )''')
        c.execute('''CREATE TABLE connections (
            id INTEGER PRIMARY KEY ASC,
            root INTEGER NOT NULL,
            endpoint INTEGER NOT NULL,
            user INTEGER NOT NULL,
            cred INTEGER,
            FOREIGN KEY(endpoint) REFERENCES endpoints(id)
            FOREIGN KEY(user) REFERENCES users(id)
            FOREIGN KEY(cred) REFERENCES creds(id)
            )''')
        c.execute('''CREATE TABLE paths (
            id INTEGER PRIMARY KEY ASC,
            src INTEGER NOT NULL,
            dst INTEGER NOT NULL,
            FOREIGN KEY(src) REFERENCES hosts(id)
            FOREIGN KEY(dst) REFERENCES endpoints(id)
            )''')
        c.commit()
        c.close()

    @classmethod
    def connect(cls, workspace):
        """Open the connection to the database for a :class:`Workspace`
        
        If this function is called from the main thread, it closes existing
        sqlite connections and opens a new one. Else, if a connection isn't
        already open for the current thread, it opens the connection.

        Args:
            workspace (str): the name of the Workspace to open

        Raises:
            ValueError: raised if the database file doesn't exist
        """

        dbPath = os.path.join(workspacesDir, workspace, "workspace.db")
        mainThreadName = threading.main_thread().getName()
        currentName = threading.currentThread().getName()
        if currentName != mainThreadName:
            if currentName in cls.__threadsConn.keys():
                return
            else:
                cls.__threadsConn[currentName] = sqlite3.connect(dbPath)
                return
        if cls.__conn is not None:
            cls.__conn.close()
        cls.__workspace = workspace
        if not os.path.exists(dbPath):
            raise ValueError("Workspace database not found, the workspace must be corrupted !")
        cls.__conn = sqlite3.connect(dbPath)

    @classmethod
    def close(cls):
        """Closes the connection for the current Thread"""

        mainThreadName = threading.main_thread().getName()
        currentName = threading.currentThread().getName()
        if currentName != mainThreadName:
            if currentName in cls.__threadsConn.keys():
                cls.__threadsConn[currentName].close()
                del cls.__threadsConn[currentName]
            return
        cls.__conn.close()
        cls.__conn = None

