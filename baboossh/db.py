import sqlite3
import threading
import os
from baboossh.utils import WORKSPACES_DIR

class Db():
    """A singleton handling the database connection

    This class allows the use of a single sqlite connection for earch thread
    """

    __conn = None
    __threadsConn = {}
    __workspace = None

    @classmethod
    def get(cls):
        """Returns the database connection for the current thread

        If the current thread isn't the main and no connection is already
        opened, opens a new one and returns it

        Returns:
            An open :class:`sqlite3.Connection`
        """

        main_thread_name = threading.main_thread().getName()
        current_thread_name = threading.currentThread().getName()
        if current_thread_name != main_thread_name:
            if current_thread_name in cls.__threadsConn.keys():
                return cls.__threadsConn[current_thread_name]
            cls.connect(cls.__workspace)
            return cls.__threadsConn[current_thread_name]
        if cls.__conn is None:
            raise ValueError("Trying to use unconnected database")
        return cls.__conn

    @classmethod
    def build(cls, workspace):
        """Create the databases and the tables for a new :class:`Workspace`

        Args:
            workspace (str): the workspace's name
        """

        db_path = os.path.join(WORKSPACES_DIR, workspace, "workspace.db")
        connection = sqlite3.connect(db_path)
        connection.execute('''CREATE TABLE hosts (
            id INTEGER PRIMARY KEY ASC,
            name TEXT NOT NULL UNIQUE,
            hostname TEXT,
            uname TEXT,
            issue TEXT,
            machine_id TEXT,
            macs TEXT
            )''')
        connection.execute('''CREATE TABLE endpoints (
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
        connection.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY ASC,
            scope INTEGER NOT NULL,
            username TEXT NOT NULL,
            found INTEGER,
            FOREIGN KEY(found) REFERENCES endpoints(id)
            )''')
        connection.execute('''CREATE TABLE creds (
            id INTEGER PRIMARY KEY ASC,
            scope INTEGER NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            identifier TEXT NOT NULL,
            found INTEGER,
            FOREIGN KEY(found) REFERENCES endpoints(id)
            )''')
        connection.execute('''CREATE TABLE connections (
            id INTEGER PRIMARY KEY ASC,
            root INTEGER NOT NULL,
            endpoint INTEGER NOT NULL,
            user INTEGER NOT NULL,
            cred INTEGER,
            FOREIGN KEY(endpoint) REFERENCES endpoints(id)
            FOREIGN KEY(user) REFERENCES users(id)
            FOREIGN KEY(cred) REFERENCES creds(id)
            )''')
        connection.execute('''CREATE TABLE paths (
            id INTEGER PRIMARY KEY ASC,
            src INTEGER NOT NULL,
            dst INTEGER NOT NULL,
            FOREIGN KEY(src) REFERENCES hosts(id)
            FOREIGN KEY(dst) REFERENCES endpoints(id)
            )''')
        connection.execute('''CREATE TABLE tags (
            name INTEGER NOT NULL,
            endpoint INTEGER NOT NULL,
            FOREIGN KEY(endpoint) REFERENCES endpoints(id),
            UNIQUE(name, endpoint)
            )''')
            
        connection.commit()
        connection.close()

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

        db_path = os.path.join(WORKSPACES_DIR, workspace, "workspace.db")
        main_thread_name = threading.main_thread().getName()
        current_thread_name = threading.currentThread().getName()
        if current_thread_name != main_thread_name:
            if current_thread_name in cls.__threadsConn.keys():
                return
            cls.__threadsConn[current_thread_name] = sqlite3.connect(db_path)
            return
        if cls.__conn is not None:
            cls.__conn.close()
        cls.__workspace = workspace
        if not os.path.exists(db_path):
            raise ValueError("Workspace database not found, the workspace must be corrupted !")
        cls.__conn = sqlite3.connect(db_path)

    @classmethod
    def close(cls):
        """Closes the connection for the current Thread"""

        main_thread_name = threading.main_thread().getName()
        current_thread_name = threading.currentThread().getName()
        if current_thread_name != main_thread_name:
            if current_thread_name in cls.__threadsConn.keys():
                cls.__threadsConn[current_thread_name].close()
                del cls.__threadsConn[current_thread_name]
            return
        cls.__conn.close()
        cls.__conn = None
