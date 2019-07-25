import os
import re
import configparser
import sqlite3
import ipaddress
from src.host import Host
from src.target import Target

config = configparser.ConfigParser()
config.read('config.ini')
if "DEFAULT" not in config or "workspaces" not in config['DEFAULT']:
    print("Invalid config file")
    exit()


class Workspace():
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
        
        self.hosts = []
        c = self.conn.cursor()
        for row in c.execute('''SELECT name FROM hosts'''):
            self.hosts.append(Host(row[0],self.conn))
        c.close()


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
        newHost = Host(name,self.conn)
        newHost.save()
        self.hosts.append(newHost)

        #Creates and saves target associated to Host
        newTarget = Target(ip,port,newHost,self.conn)
        newTarget.save()
        #TODO


    def getName(self):
        return self.name

    def getHosts(self):
        return self.hosts

    def close(self):
        self.conn.close()
        print("Closing workspace "+self.name)


