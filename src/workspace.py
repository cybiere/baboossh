import os
import re
import configparser
import ipaddress
from fabric import Connection as FabConnection
from src.params import dbConn,Extensions
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
        dbConn.build(name)
        return Workspace(name)

    def __init__(self,name):
        if name == "":
            raise ValueError("Cannot use workspace with empty name")
        if re.match('^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        workspaceFolder = os.path.join(config['DEFAULT']['workspaces'],name)
        if not os.path.exists(workspaceFolder):
            raise ValueError("Workspace "+name+" does not exist")
        dbConn.connect(name)
        self.name = name
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
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM hosts WHERE name=?',(name,))
        res = c.fetchone()
        c.close()
        return res is not None

    #Checks if a target already exists
    def checkTargetExists(self,ip,port):
        c = dbConn.get().cursor()
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
        newHost = Host(name)
        newHost.save()

        #Creates and saves target associated to Host
        newTarget = Target(ip,port,newHost)
        newTarget.save()

#################################################################
###################           USERS           ###################
#################################################################

    #Checks if a user already exists with given name
    def checkUserNameExists(self,name):
        c = dbConn.get().cursor()
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
        newUser = User(name)
        newUser.save()

#################################################################
###################           CREDS           ###################
#################################################################

    def addCreds_Manual(self,credsType):
        credsContent = Extensions.getAuthMethod(credsType).build()
        newCreds = Creds(credsType,credsContent)
        newCreds.save()

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
        newConn = Connection(target.getHost(),target,user,cred)
        #TODO: create connection if not exists
        #TODO: this is just a POC
        print("Establishing connection to "+str(user)+"@"+str(target)+" (with creds "+str(cred)+")",end="...")
        kwargs = {} #Add default values here
        authArgs = cred.getKwargs()
        c = FabConnection(host=target.getIp(),port=target.getPort(),user=user.getName(),connect_kwargs={**kwargs, **authArgs})
        try:
            c.open()
        except Exception as e:
            print("> "+str(e))
            newConn.setWorking(False)
        else:
            print("> \033[1;31;40mPWND\033[0m")
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
        return Host.findAll()

    def getTargets(self):
        targets = []
        for host in Host.findAll():
            for target in host.targets:
                targets.append(target)
        return targets

    def getTargetsList(self):
        targets = []
        for host in Host.findAll():
            for target in host.targets:
                targets.append(target.ip+":"+target.port)
        return targets

    def getUsersList(self):
        users = []
        for user in User.findAll():
            users.append(user.name)
        return users

    def getCredsById(self,credId):
        c = dbConn.get().cursor()
        c.execute('''SELECT type,content FROM creds WHERE id=?''',(credId,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Creds(row[0],row[1])

    def getUserByName(self,name):
        c = dbConn.get().cursor()
        c.execute('''SELECT username FROM users WHERE username=?''',(name,))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return User(name)

    def getTargetByIpPort(self,endpoint):
        ip,sep,port = endpoint.partition(":")
        if port == "":
            raise ValueError
        c = dbConn.get().cursor()
        c.execute('''SELECT host FROM targets WHERE ip=? and port=?''',(ip,port))
        row = c.fetchone()
        c.close()
        if row == None:
            return None
        return Target(ip,port,Host.find(row[0]))

    def getUsers(self):
        return User.findAll()

    def getCreds(self):
        return Creds.findAll()

    def getCredsIdList(self):
        idList = []
        for cred in Creds.findAll():
            idList.append(str(cred.getId()))
        return idList

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

    def close(self):
        dbConn.close()
        print("Closing workspace "+self.name)


