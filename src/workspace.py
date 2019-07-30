import os
import re
import configparser
import ipaddress
from fabric import Connection as FabConnection
from src.params import dbConn,Extensions
from src.host import Host
from src.endpoint import Endpoint
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
            "endpoint":None,
            "user":None,
            "creds":None,
            "payload":None,
                }

#################################################################
###################         ENDPOINTS         ###################
#################################################################

    #Checks if a host already exists with given name
    def checkHostNameExists(self,name):
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM hosts WHERE name=?',(name,))
        res = c.fetchone()
        c.close()
        return res is not None

    #Checks if a endpoint already exists
    def checkEndpointExists(self,ip,port):
        c = dbConn.get().cursor()
        c.execute('SELECT id FROM endpoints WHERE ip=? AND port=?',(ip,port))
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

    #Manually add a endpoint
    def addEndpoint_Manual(self,ip,port):
        if not self.checkIsIP(ip):
            print("The address given isn't a valid IP")
            raise ValueError
        if not port.isdigit():
            print("The port given isn't a positive integer")
            raise ValueError
        if self.checkEndpointExists(ip,port):
            print("The endpoint "+ip+":"+port+" already exists")
            raise ValueError

        #Creates and saves endpoint associated to Host
        newEndpoint = Endpoint(ip,port)
        newEndpoint.save()

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
        if option == 'target' and '@' in value and ':' in value:
            auth,sep,endpoint = value.partition('@')
            endpoint  = Endpoint.findByIpPort(endpoint)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            user,sep,cred = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            user = User.findByUsername(user)
            if user is None:
                raise ValueError("Supplied user isn't in workspace")
            if cred[0] == "#":
                cred = cred[1:]
            cred = Creds.find(cred)
            if cred is None:
                raise ValueError("Supplied credentials aren't in workspace")
            self.options['endpoint'] = endpoint
            self.options['user'] = user
            self.options['creds'] = cred
            for option in ['endpoint','user','creds']:
                print(option+" => "+str(self.getOption(option)))
            return 
        if not option in self.options.keys():
            raise ValueError(option+" isn't a valid option.")
        if value != "":
            value = value.strip()
            if option == "endpoint":
                endpoint = Endpoint.findByIpPort(value)
                if endpoint is None:
                    raise ValueError
                value = endpoint
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

    def connect(self,endpoint,user,cred):
        newConn = Connection(endpoint,user,cred)
        print("Establishing connection to "+str(user)+"@"+str(endpoint)+" (with creds "+str(cred)+")",end="...")
        kwargs = {} #Add default values here
        authArgs = cred.getKwargs()
        c = FabConnection(host=endpoint.getIp(),port=endpoint.getPort(),user=user.getName(),connect_kwargs={**kwargs, **authArgs})
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

    def connectEndpoint(self,arg):
        if '@' in arg and ':' in arg:
            auth,sep,endpoint = arg.partition('@')
            endpoint  = Endpoint.findByIpPort(endpoint)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            user,sep,cred = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            user = User.findByUsername(user)
            if user is None:
                raise ValueError("Supplied user isn't in workspace")
            if cred[0] == "#":
                cred = cred[1:]
            cred = Creds.find(cred)
            if cred is None:
                raise ValueError("Supplied credentials aren't in workspace")
        else:    
            endpoint = Endpoint.findByIpPort(arg)
            if endpoint is None:
                raise ValueError("Supplied endpoint isn't in workspace")
            connection = endpoint.getConnection()
            if connection == None:
                raise ValueError("No working connection for supplied endpoint")
            user = connection.getUser()
            cred = connection.getCred()
        self.connect(endpoint,user,cred)


#################################################################
###################          GETTERS          ###################
#################################################################

    def getName(self):
        return self.name

    def getHosts(self):
        return Host.findAll()

    def getEndpoints(self):
        endpoints = []
        for endpoint in Endpoint.findAll():
            endpoints.append(endpoint)
        return endpoints

    def getEndpointsList(self):
        endpoints = []
        for host in Host.findAll():
            for endpoint in host.endpoints:
                endpoints.append(endpoint.ip+":"+endpoint.port)
        return endpoints

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


