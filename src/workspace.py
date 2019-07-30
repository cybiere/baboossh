import os
import re
import configparser
import sqlite3
import ipaddress
import inspect
import importlib
from fabric import Connection as FabConnection
from src.host import Host
from src.target import Target
from src.user import User
from src.creds import Creds
from src.connection import Connection


config = configparser.ConfigParser()
config.read('config.ini')
if "DEFAULT" not in config or "workspaces" not in config['DEFAULT']:
    print("Invalid config file")
    exit()


class Workspace():

#################################################################
###################           INIT            ###################
#################################################################

    @classmethod
    def create(cls,name):
        if name == "":
            print("Cannot use workspace with empty name")
            raise ValueError
        if re.match('^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        workspaceFolder = os.path.join(config['DEFAULT']['workspaces'],name)
        if not os.path.exists(workspaceFolder):
            try:
                os.mkdir(workspaceFolder)
            except OSError:
                print ("Creation of the directory %s failed" % workspaceFolder)
                raise OSError
            print("Workspace "+name+" created")
        else:
            print("Workspace already exists")
            raise ValueError
        #create database
        c = sqlite3.connect(os.path.join(workspaceFolder,"workspace.db"))
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
        return Workspace(name)

    def loadHosts(self):
        self.hosts = []
        c = self.conn.cursor()
        for row in c.execute('''SELECT name FROM hosts'''):
            self.hosts.append(Host(row[0],self))
        c.close()

    def loadUsers(self):
        self.users = []
        c = self.conn.cursor()
        for row in c.execute('''SELECT username FROM users'''):
            self.users.append(User(row[0],self))
        c.close()

    def loadCreds(self):
        self.creds = []
        c = self.conn.cursor()
        for row in c.execute('''SELECT type,content FROM creds'''):
            self.creds.append(Creds(row[0],row[1],self))
        c.close()

    def loadExtensions(self):
        nbExt = 0
        extensionsFolder = 'extensions'
        files = [f.split('.')[0] for f in os.listdir(extensionsFolder) if os.path.isfile(os.path.join(extensionsFolder,f)) and f[0] != '.']
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
                        dico = self.authMethods
                    elif modType == "payload":
                        dico = self.payloads
                    else:
                        print(mod+"> module Type Invalid")
                        continue
                    if data.getKey() in dico.keys():
                        print(mod+"> "+modType+' method "'+data.getKey()+'" already registered')
                        continue
                    dico[data.getKey()] = data
                    nbExt = nbExt+1
        print(str(nbExt)+" extensions loaded.")

    def __init__(self,name):
        if name == "":
            print("Cannot use workspace with empty name")
            raise ValueError
        if re.match('^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        workspaceFolder = os.path.join(config['DEFAULT']['workspaces'],name)
        if not os.path.exists(workspaceFolder):
            print("Workspace "+name+" does not exist")
            raise ValueError
        self.name = name
        dbPath = os.path.join(workspaceFolder,"workspace.db")
        if not os.path.exists(dbPath):
            print("Workspace database not found, the workspace must be corrupted !")
            raise ValueError
        self.conn = sqlite3.connect(os.path.join(workspaceFolder,"workspace.db"))

        self.authMethods = {}
        self.payloads = {}

        self.loadExtensions()
        
        self.loadHosts()
        self.loadUsers()
        self.loadCreds()

        self.options = {
            "target":None,
            "user":None,
            "creds":None,
            "payload":None,
                }

#################################################################
###################          TARGETS          ###################
#################################################################

    #Checks if a host already exists with given name
    def checkHostNameExists(self,name):
        c = self.conn.cursor()
        c.execute('SELECT id FROM hosts WHERE name=?',(name,))
        res = c.fetchone()
        c.close()
        return res is not None

    #Checks if a target already exists
    def checkTargetExists(self,ip,port):
        c = self.conn.cursor()
        c.execute('SELECT id FROM targets WHERE ip=? AND port=?',(ip,port))
        res = c.fetchone()
        c.close()
        return res is not None

    #Checks if param is a valid IP (v4 or v6)
    def checkIsIP(self,ip):
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return False
        return True

    #Manually add a host and its first target
    def addHost_Manual(self,name,ip,port):
        if self.checkHostNameExists(name):
            print("A host already exists with the name "+name)
            raise ValueError
        if not self.checkIsIP(ip):
            print("The address given isn't a valid IP")
            raise ValueError
        if not port.isdigit():
            print("The port given isn't a positive integer")
            raise ValueError
        if self.checkTargetExists(ip,port):
            print("The target "+ip+":"+port+" already exists")
            raise ValueError

        #Creates and saves host
        newHost = Host(name,self)
        newHost.save()
        self.hosts.append(newHost)

        #Creates and saves target associated to Host
        newTarget = Target(ip,port,newHost,self)
        newTarget.save()

#################################################################
###################           USERS           ###################
#################################################################

    #Checks if a user already exists with given name
    def checkUserNameExists(self,name):
        c = self.conn.cursor()
        c.execute('SELECT id FROM users WHERE username=?',(name,))
        res = c.fetchone()
        c.close()
        return res is not None

    #Manually add a user
    def addUser_Manual(self,name):
        if self.checkUserNameExists(name):
            print("A user already exists with the name "+name)
            raise ValueError

        #Creates and saves user
        newUser = User(name,self)
        newUser.save()
        self.users.append(newUser)

#################################################################
###################           CREDS           ###################
#################################################################

    def addCreds_Manual(self,credsType):
        credsContent = self.authMethods[credsType].build()
        newCreds = Creds(credsType,credsContent,self)
        newCreds.save()
        self.creds.append(newCreds)

#################################################################
###################          OPTIONS          ###################
#################################################################

    def setOption(self,option,value):
        if not option in self.options.keys():
            print(option+" isn't a valid option.")
            raise ValueError
        if value != "":
            value = value.strip()
            if option == "target":
                target = self.getTargetByIpPort(value)
                if target is None:
                    raise ValueError
                value = target
            elif option == "user":
                user = self.getUserByName(value)
                if user is None:
                    raise ValueError
                value = user
            elif option == "creds":
                if value[0] == '#':
                    credId = value[1:]
                else:
                    credId = value
                creds = self.getCredsById(credId)
                if creds is None:
                    raise ValueError
                value = creds
        else:
            self.options[option] = None
    
        self.options[option] = value
        print(option+" => "+str(self.getOption(option)))

#################################################################
###################        CONNECTIONS        ###################
#################################################################

    def connect(self,target,user,cred):
        newConn = Connection(target.getHost(),target,user,cred,self)
        #TODO: create connection if not exists
        #TODO: this is just a POC
        print("Establishing connection to "+str(user)+"@"+str(target)+" (with creds "+str(cred)+")",end="...")
        kwargs = {} #Add default values here
        authArgs = cred.getKwargs()
        c = FabConnection(host=target.getIp(),port=target.getPort(),user=user.getName(),connect_kwargs={**kwargs, **authArgs})
        try:
            c.open()
        except Exception as e:
            print("\t> Connection failed : "+str(e))
            newConn.setWorking(False)
        else:
            print("\t> Connection successful")
            newConn.setWorking(True)
        c.close()
        newConn.setTested(True)
        newConn.save()
        return newConn.isWorking()

#################################################################
###################          GETTERS          ###################
#################################################################

    def getName(self):
        return self.name

    def getHosts(self):
        return self.hosts

    def getTargets(self):
        targets = []
        for host in self.hosts:
            for target in host.targets:
                targets.append(target)
        return targets

    def getTargetsList(self):
        targets = []
        for host in self.hosts:
            for target in host.targets:
                targets.append(target.ip+":"+target.port)
        return targets

    def getUsersList(self):
        users = []
        for user in self.users:
            users.append(user.name)
        return users

    def getCredsById(self,credId):
        c = self.conn.cursor()
        c.execute('''SELECT type,content FROM creds WHERE id=?''',(credId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Creds(row[0],row[1],self)

    def getUserByName(self,name):
        c = self.conn.cursor()
        c.execute('''SELECT username FROM users WHERE username=?''',(name,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return User(name,self)

    def getHostById(self,hostId):
        c = self.conn.cursor()
        c.execute('''SELECT name FROM hosts WHERE id=?''',(hostId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Host(row[0],self)

    def getTargetByIpPort(self,endpoint):
        ip,sep,port = endpoint.partition(":")
        if port == "":
            raise ValueError
        c = self.conn.cursor()
        c.execute('''SELECT host FROM targets WHERE ip=? and port=?''',(ip,port))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Target(ip,port,self.getHostById(row[0]),self)

    def getUsers(self):
        return self.users

    def getCreds(self):
        return self.creds

    def getCredsIdList(self):
        idList = []
        for cred in self.creds:
            idList.append(str(cred.getId()))
        return idList

    def getAuthTypes(self):
        return self.authMethods.keys()
    
    def getAuthMethods(self):
        return self.authMethods.items()

    def getAuthClasses(self):
        return self.authMethods

    def getPayloads(self):
        return self.payloads.items()

    def getOptions(self):
        return self.options.keys()

    def getOptionsValues(self):
        return self.options.items()

    def getOption(self,key):
        if key not in self.options.keys():
            raise ValueError()
        if self.options[key] == None:
            return None
        return self.options[key]

    def getConn(self):
        return self.conn

    def close(self):
        self.conn.close()
        print("Closing workspace "+self.name)


