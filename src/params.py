import sqlite3
import importlib
import inspect
import configparser
from os.path import join,exists,isfile
from os import listdir

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
    def build(cls,workspace):
        dbPath = join(config['DEFAULT']['workspaces'],workspace,"workspace.db")
        c = sqlite3.connect(dbPath)
        c.execute('''CREATE TABLE hosts (
            id INTEGER PRIMARY KEY ASC,
            name TEXT NOT NULL,
            identifier TEXT
            )''')
        c.execute('''CREATE TABLE targets (
            id INTEGER PRIMARY KEY ASC,
            host INTEGER,
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
            host INTEGER,
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

class Extensions():
    auths = {}
    payloads = {}

    @classmethod
    def load(cls):
        nbExt = 0
        extensionsFolder = 'extensions'
        files = [f.split('.')[0] for f in listdir(extensionsFolder) if isfile(join(extensionsFolder,f)) and f[0] != '.']
        for mod in files:
            moduleName = extensionsFolder+"."+mod
            try:
                newMod = importlib.import_module(moduleName)
            except Exception as e:
                print("Couldn't load extension "+mod+" :"+str(e))
                continue
            else:
                for name, data in inspect.getmembers(newMod):
                    if not inspect.isclass(data):
                        continue
                    if name != "SpreadExt":
                        continue
        
                    modType = data.getModType()
                    if modType == "auth":
                        dico = cls.auths
                    elif modType == "payload":
                        dico = cls.payloads
                    else:
                        print(mod+"> module Type Invalid")
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


