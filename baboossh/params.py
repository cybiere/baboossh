import sqlite3
import importlib
import inspect
import threading
from os.path import join,exists,isfile,expanduser,dirname
from os import listdir

home = expanduser("~")
workspacesDir = join(home,".baboossh")

def yesNo(prompt,default=None):
    if default is None:
        choices = "[y,n]"
    elif default:
        choices = "[Y,n]"
    else:
        choices = "[y,N]"
    a = ""
    while a not in ["y","n"]:
        a = input(prompt+" "+choices+" ").lower()
        if a == "" and default is not None:
            a = "y" if default else "n"
    return a == "y"

class dbConn():
    __conn=None
    __threadsConn={}
    __workspace=None

    @classmethod
    def get(cls):
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
        dbPath = join(workspacesDir,workspace,"workspace.db")
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
            scanned INTEGER NOT NULL,
            reachable INTEGER,
            auth TEXT,
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
            tested INTEGER NOT NULL,
            working INTEGER NOT NULL,
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
        dbPath = join(workspacesDir,workspace,"workspace.db")
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
        if not exists(dbPath):
            raise ValueError("Workspace database not found, the workspace must be corrupted !")
        cls.__conn = sqlite3.connect(dbPath)

    @classmethod
    def close(cls):
        mainThreadName = threading.main_thread().getName()
        currentName = threading.currentThread().getName()
        if currentName != mainThreadName:
            if currentName in cls.__threadsConn.keys():
                cls.__threadsConn[currentName].close()
                del cls.__threadsConn[currentName]
            return
        cls.__conn.close()
        cls.__conn = None

    @classmethod
    def cleanThreadsConn(cls):
        for c in cls.__threadsConn.values():
            c.close()
        cls.__threadsConn = {}

class Extensions():
    auths = {}
    payloads = {}
    exports = {}
    imports = {}

    @classmethod
    def load(cls):
        nbExt = 0
        extensionsFolder = join(dirname(__file__),'extensions')
        files = [f.split('.')[0] for f in listdir(extensionsFolder) if isfile(join(extensionsFolder,f)) and f[0] != '.']
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
                        dico = cls.auths
                    elif modType == "payload":
                        dico = cls.payloads
                    elif modType == "export":
                        dico = cls.exports
                    elif modType == "import":
                        dico = cls.imports
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
        if key not in cls.auths.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.auths[key]

    @classmethod
    def authMethodsAvail(cls):
        return cls.auths.keys()

    @classmethod
    def getPayload(cls,key):
        if key not in cls.payloads.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.payloads[key]

    @classmethod
    def payloadsAvail(cls):
        return cls.payloads.keys()

    @classmethod
    def getExport(cls,key):
        if key not in cls.exports.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.exports[key]

    @classmethod
    def exportsAvail(cls):
        return cls.exports.keys()

    @classmethod
    def getImport(cls,key):
        if key not in cls.imports.keys():
            raise IndexError("Extension "+key+" not found")
        return cls.imports[key]

    @classmethod
    def importsAvail(cls):
        return cls.imports.keys()

