import sqlite3
import importlib
import inspect
import threading
import os

home = os.path.expanduser("~")
workspacesDir = os.path.join(home,".baboossh")

class dbConn():
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
    def build(cls,workspace):
        """Create the databases and the tables for a new :class:`Workspace`

        Args:
            workspace (str): the workspace's name
        """

        dbPath = os.path.join(workspacesDir,workspace,"workspace.db")
        c = sqlite3.connect(dbPath)
        c.execute('''CREATE TABLE hosts (
            id INTEGER PRIMARY KEY ASC,
            name TEXT NOT NULL,
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
    def connect(cls,workspace):
        """Open the connection to the database for a :class:`Workspace`
        
        If this function is called from the main thread, it closes existing
        sqlite connections and opens a new one. Else, if a connection isn't
        already open for the current thread, it opens the connection.

        Args:
            workspace (str): the name of the Workspace to open

        Raises:
            ValueError: raised if the database file doesn't exist
        """

        dbPath = os.path.join(workspacesDir,workspace,"workspace.db")
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

class Extensions():
    """Load and access available extensions"""

    __auths = {}
    __payloads = {}
    __exports = {}
    __imports = {}

    @classmethod
    def load(cls):
        """Load extensions from the dedicated folder

        Load extensions and sort them according to their type:
        * Authentication Methods
        * Payloads
        * Exporter
        * Importer
        """

        nbExt = 0
        extensionsFolder = os.path.join(os.path.dirname(__file__),'extensions')
        files = [f.split('.')[0] for f in os.listdir(extensionsFolder) if os.path.isfile(os.path.join(extensionsFolder,f)) and f[0] != '.']
        for mod in files:
            moduleName = "baboossh.extensions."+mod
            try:
                newMod = importlib.import_module(moduleName)
            except Exception as e:
                print("Couldn't load extension "+mod+" :"+str(e))
                continue
            else:
                for name, data in inspect.getmembers(newMod):
                    if not inspect.isclass(data):
                        continue
                    if name != "BaboosshExt":
                        continue
        
                    modType = data.getModType()
                    if modType == "auth":
                        dico = cls.__auths
                    elif modType == "payload":
                        dico = cls.__payloads
                    elif modType == "export":
                        dico = cls.__exports
                    elif modType == "import":
                        dico = cls.__imports
                    else:
                        print(mod+"> module type Invalid")
                        continue
                    if data.getKey() in dico.keys():
                        print(mod+"> "+modType+' method "'+data.getKey()+'" already registered')
                        continue
                    dico[data.getKey()] = data
                    nbExt = nbExt+1
        print(str(nbExt)+" extensions loaded.")

    @classmethod
    def getAuthMethod(cls,key):
        """Get an authentication method by its key

        Args:
            key (str): the desired method key

        Returns:
            The AuthMethod class
        """

        if key not in cls.__auths.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__auths[key]

    @classmethod
    def authMethodsAvail(cls):
        """Get all available authentication methods

        Returns:
            A list of the keys of available methods
        """

        return cls.__auths.keys()

    @classmethod
    def getPayload(cls,key):
        """Get a payload by its key

        Args:
            key (str): the desired payload key

        Returns:
            The Payload class
        """

        if key not in cls.__payloads.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__payloads[key]

    @classmethod
    def payloadsAvail(cls):
        """Get all available payloads

        Returns:
            A list of the keys of available payloads
        """

        return cls.__payloads.keys()

    @classmethod
    def getExport(cls,key):
        """Get an exporter by its key

        Args:
            key (str): the desired exporter key

        Returns:
            The Exporter class
        """

        if key not in cls.__exports.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__exports[key]

    @classmethod
    def exportsAvail(cls):
        """Get all available exporters

        Returns:
            A list of the keys of exporters
        """

        return cls.__exports.keys()

    @classmethod
    def getImport(cls,key):
        """Get an importer by its key

        Args:
            key (str): the desired importer key

        Returns:
            The Importer class
        """

        if key not in cls.__imports.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.__imports[key]

    @classmethod
    def importsAvail(cls):
        """Get all available importers

        Returns:
            A list of the keys of available importers
        """

        return cls.__imports.keys()
