import os
import re
import ipaddress
import sys
import threading
import asyncio
from baboossh.params import dbConn,Extensions,workspacesDir,yesNo
from baboossh.host import Host
from baboossh.endpoint import Endpoint
from baboossh.user import User
from baboossh.creds import Creds
from baboossh.connection import Connection
from baboossh.path import Path
from baboossh.tunnel import Tunnel

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
        workspaceFolder = os.path.join(workspacesDir,name)
        if not os.path.exists(workspaceFolder):
            try:
                os.mkdir(workspaceFolder)
                os.mkdir(os.path.join(workspaceFolder,"loot"))
                os.mkdir(os.path.join(workspaceFolder,"keys"))
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
        self.workspaceFolder = os.path.join(workspacesDir,name)
        if not os.path.exists(self.workspaceFolder):
            raise ValueError("Workspace "+name+" does not exist")
        dbConn.connect(name)
        self.name = name
        self.tunnels = {}
        self.options = {
            "endpoint":None,
            "user":None,
            "creds":None,
            "payload":None,
            "params":None,
                }

#################################################################
###################         ENDPOINTS         ###################
#################################################################

    #Checks if param is a valid IP (v4 or v6)
    def checkIsIP(self,ip):
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return False
        return True

    #Manually add a endpoint
    def addEndpoint(self,ip,port):
        if not self.checkIsIP(ip):
            print("The address given isn't a valid IP")
            raise ValueError
        if not port.isdigit():
            print("The port given isn't a positive integer")
            raise ValueError

        newEndpoint = Endpoint(ip,port)
        newEndpoint.save()

    def delEndpoint(self,endpoint):
        try:
            endpoint = Endpoint.findByIpPort(endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if endpoint is None:
            print("Could not find endpoint.")
            return False
        return endpoint.delete()

#################################################################
###################           USERS           ###################
#################################################################

    def addUser(self,name):
        newUser = User(name)
        newUser.save()

    def delUser(self,name):
        user = User.findByUsername(name)
        if user is None:
            print("Could not find user.")
            return False
        return user.delete()

#################################################################
###################           HOSTS           ###################
#################################################################

    def delHost(self,host):
        if host not in self.getHostsNames():
            print("Not a known Host name.")
            return False
        
        hosts = Host.findByName(host)
        if len(hosts) > 1:
            print("Several hosts corresponding. Please delete endpoints.")
            return False
        return hosts[0].delete()


#################################################################
###################           CREDS           ###################
#################################################################

    def addCreds(self,credsType,stmt):
        credsContent = Extensions.getAuthMethod(credsType).fromStatement(stmt)
        newCreds = Creds(credsType,credsContent)
        newCreds.save()
        return newCreds.getId()

    def showCreds(self,credsId):
        if credsId[0] == '#':
            credsId = credsId[1:]
        creds = Creds.find(credsId)
        if creds == None:
            print("Specified creds not found")
            return
        creds.show()

    def editCreds(self,credsId):
        if credsId[0] == '#':
            credsId = credsId[1:]
        creds = Creds.find(credsId)
        if creds == None:
            print("Specified creds not found")
            return
        creds.edit()

    def delCreds(self,credsId):
        if credsId[0] == '#':
            credsId = credsId[1:]
        creds = Creds.find(credsId)
        if creds == None:
            print("Specified creds not found")
            return False
        return creds.delete()

#################################################################
###################          OPTIONS          ###################
#################################################################

    def setOption(self,option,value):
        if option == 'connection':
            if value is None:
                self.options['endpoint'] = None
                self.options['user'] = None
                self.options['creds'] = None
                for option in ['endpoint','user','creds']:
                    print(option+" => "+str(self.getOption(option)))
                return 
            if '@' not in value or ':' not in value:
                return
            connection = Connection.fromTarget(value)
            if connection == None:
                return
            self.options['endpoint'] = connection.getEndpoint()
            self.options['user'] = connection.getUser()
            self.options['creds'] = connection.getCred()
            for option in ['endpoint','user','creds']:
                print(option+" => "+str(self.getOption(option)))
            return 
        if not option in list(self.options.keys()):
            raise ValueError(option+" isn't a valid option.")
        if value != None:
            value = value.strip()
            if option == "endpoint":
                endpoint = Endpoint.findByIpPort(value)
                if endpoint is None:
                    raise ValueError
                value = endpoint
            elif option == "user":
                user = User.findByUsername(value)
                if user is None:
                    raise ValueError
                value = user
            elif option == "creds":
                if value[0] == '#':
                    credId = value[1:]
                else:
                    credId = value
                creds = Creds.find(credId)
                if creds is None:
                    raise ValueError
                value = creds
            elif option == "payload":
                value = Extensions.getPayload(value)
            self.options[option] = value
        else:
            self.options[option] = None
        print(option+" => "+str(self.getOption(option)))

#################################################################
###################        CONNECTIONS        ###################
#################################################################
    
    def delConnection(self,target):
        connection = Connection.fromTarget(target)
        if connection is None:
            print("Connection not found.")
            return false
        return connection.delete()

    def parseOptionsTarget(self):
        user = self.getOption("user")
        if user is None:
            users = self.getUsers(scope=True)
        else:
            users = [User.find(user.getId())]
        endpoint = self.getOption("endpoint")
        if endpoint is None:
            endpoints = self.getEndpoints(scope=True)
        else:
            endpoints = [Endpoint.find(endpoint.getId())]
        cred = self.getOption("creds")
        if cred is None:
            creds = self.getCreds(scope=True)
        else:
            creds = [Creds.find(cred.getId())]
        return (endpoints,users,creds)

    def threadConnect(self,verbose,endpoint,users,creds):
        try:
            loop = asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        c = dbConn.get()
        if Path.hasDirectPath(endpoint):
            gw = None
        else:
            gateway = endpoint.findGatewayConnection()
            if gateway is not None:
                if verbose:
                    print("Connecting to gateway "+str(gateway)+" to reach "+str(endpoint)+"...")
                gw = gateway.initConnect(verbose=verbose)
            else:
                gw = None
        workingQueue = []
        dunnoQueue = []
        for user in users:
            for cred in creds:
                connection = Connection(endpoint,user,cred)
                if connection.isWorking():
                    workingQueue.append(connection)
                else:
                    dunnoQueue.append(connection)
        queue = workingQueue + dunnoQueue
        for connection in queue:
            try:
                working = connection.testConnect(gw,verbose=True)
            except:
                print("Due to timeout, subsequent connections to endpoint will be ignored.")
                break
            if working:
                break
        if gw is not None:
            gw.close()
        dbConn.close()


    def massConnect(self,verbose):
        try:
            endpoints,users,creds = self.parseOptionsTarget()
        except:
            return
        nbIter = len(endpoints)*len(users)*len(creds)
        if nbIter == 1:
            self.connect(endpoints[0],users[0],creds[0],verbose)
            return

        if not yesNo("This will attempt up to "+str(nbIter)+" connections. Proceed ?",False):
            return
        
        for endpoint in endpoints:
            t = threading.Thread(target=self.threadConnect, args=(verbose,endpoint,users,creds))
            t.start()
        main_thread = threading.main_thread()
        for t in threading.enumerate():
            if t is main_thread:
                continue
            t.join()

    def connect(self,endpoint,user,cred,verbose):
        connection = Connection(endpoint,user,cred)
        return connection.testConnect(verbose=verbose)

    def run(self,endpoint,user,cred,payload,stmt):
        connection = Connection(endpoint,user,cred)
        if not connection.working:
            #print("Please check connection "+str(connection)+" with connect first")
            return False
        return connection.run(payload,self.workspaceFolder,stmt)

    def scanTarget(self,target,gateway=None):
        if not isinstance(target,Endpoint):
            target = Endpoint.findByIpPort(target)
        if gateway is not None:
            if gateway == "local":
                gateway = None
            else:
                gateway = Connection.fromTarget(gateway)
        else:
            gateway = "auto"
        working = target.scan(gateway=gateway)
        return working


    def connectTarget(self,arg,verbose,gateway):
        if gateway is not None:
            if gateway == "local":
                gateway = None
            else:
                gateway = Connection.fromTarget(gateway)
        else:
            gateway = "auto"
        connection = Connection.fromTarget(arg)
        working = connection.testConnect(gateway=gateway,verbose=verbose)
        if working:
            if gateway != "auto":
                if gateway is None:
                    pathSrc = None
                elif gateway.getEndpoint().getHost() is None:
                    return working
                else:
                    pathSrc = gateway.getEndpoint().getHost()
                p = Path(pathSrc,connection.getEndpoint())
                p.save()
        return working

    def runTarget(self,arg,payloadName,stmt):
        if arg in self.getHostsNames():
            hosts = Host.findByName(arg)
            if len(hosts) > 1:
                print("Several hosts corresponding. Please target endpoint.")
                return False
            arg = str(hosts[0].getClosestEndpoint())
        connection = Connection.fromTarget(arg)
        if not connection.working:
            print("Please check connection "+str(connection)+" with connect first")
            return False
        payload = Extensions.getPayload(payloadName)
        return connection.run(payload,self.workspaceFolder,stmt)

#################################################################
###################           PATHS           ###################
#################################################################

    def getPathToDst(self,dst):
        if dst in self.getHostsNames():
            hosts = Host.findByName(dst)
            if len(hosts) > 1:
                print("Several hosts corresponding. Please target endpoint.")
                return False
            dst = str(hosts[0].getClosestEndpoint())
        try:
            dst = Endpoint.findByIpPort(dst)
        except:
            print("Please specify a valid endpoint in the IP:PORT form")
            return
        if dst is None:
            print("The endpoint provided doesn't exist in this workspace")
            return
        if Path.hasDirectPath(dst):
            print("The destination should be reachable from the host")
            return
        chain = Path.getPath(None,dst)
        if chain is None:
            print("No path could be found to the destination")
            return
        for path in chain:
            print(path)

    def delPath(self,src,dst):
        if src.lower() != "local":
            if src not in self.getHostsNames():
                print("Not a known Host name.")
                return False
            
            hosts = Host.findByName(src)
            if len(hosts) > 1:
                print("Several hosts corresponding. Add failed")
                return False
            src = hosts[0]
            if src is None:
                print("The source Host provided doesn't exist in this workspace")
                return False
        else:
            src = None
        try:
            dst = Endpoint.findByIpPort(dst)
        except:
            print("Please specify valid destination endpoint in the IP:PORT form")
        if dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return False
        p = Path(src,dst)
        if p.getId() is None:
            print("The specified Path doesn't exist in this workspace.")
            return False
        return p.delete()

    def addPath(self,src,dst):
        if src.lower() != "local":
            if src not in self.getHostsNames():
                print("Not a known Host name.")
                return
            
            hosts = Host.findByName(src)
            if len(hosts) > 1:
                print("Several hosts corresponding. Add failed")
                return
            src = hosts[0]
            if src is None:
                print("The source Host provided doesn't exist in this workspace")
                return
        else:
            src = None
        try:
            dst = Endpoint.findByIpPort(dst)
        except:
            print("Please specify valid destination endpoint in the IP:PORT form")
        if dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return
        p = Path(src,dst)
        p.save()
        print("Path saved")

    def findPath(self,dst):
        #DST is HOST
        #if dst in self.getHostsNames():
        #    hosts = Host.findByName(dst)
        #    if len(hosts) > 1:
        #        print("Several hosts corresponding. Please target endpoint.")
        #        return False
        #    dst = str(hosts[0].getClosestEndpoint())
        try:
            dst = Endpoint.findByIpPort(dst)
        except:
            print("Please specify a valid endpoint in the IP:PORT form")
            return
        if dst is None:
            print("The endpoint provided doesn't exist in this workspace")
            return
        if Path.hasDirectPath(dst):
            print("The destination should be reachable directly from the host.")
            return

        workingDirect = dst.scan(gateway=None,silent=True)
        if workingDirect:
            p = Path(None,dst)
            p.save()
            print("Could reach target directly, path added.")
            return

        for h in Path.getHostsOrderedClosest():
            e = h.getClosestEndpoint()
            gateway = Connection.findWorkingByEndpoint(e)
            working = dst.scan(gateway=gateway,silent=True)
            if working:
                p = Path(h,dst)
                p.save()
                print("Working with gw "+str(e)+" (host "+str(h)+")")
                return
        return

#################################################################
###################           SCOPE           ###################
#################################################################

    def identifyObject(self,target):
        if target[0] == "#":
            credsId = target[1:]
        else:
            credsId = target
        creds = Creds.find(credsId)
        if creds is not None:
            return creds
        user = User.findByUsername(target)
        if user is not None:
            return user
        try:
            dst = Endpoint.findByIpPort(target)
            if dst is not None:
                return dst
        except:
            pass
        hosts = Host.findByName(target)
        if len(hosts) > 1:
            print("Multiple hosts matching, use endpoints")
            return None
        if len(hosts) == 1:
            return hosts[0]
        print("Could not identify object.")
        return None

    def scope(self,target):
        obj = self.identifyObject(target)
        if obj is None:
            return False
        obj.rescope()
        obj.save()

    def unscope(self,target):
        obj = self.identifyObject(target)
        if obj is None:
            return False
        obj.unscope()
        obj.save()

#################################################################
###################          TUNNELS          ###################
#################################################################

    def getTunnels(self):
        return list(self.tunnels.values())

    def getTunnelsPort(self):
        return list(self.tunnels.keys())

    def openTunnel(self,target,port=None):
        if port is not None and port in self.tunnels.keys():
            print("A tunnel is already opened at port "+str(port))
            return False
        connection = Connection.fromTarget(target)
        try:
            t = Tunnel(connection,port)
        except Exception as e:
            print("Error opening tunnel: "+str(e))
            return False
        self.tunnels[t.getPort()] = t
        return True

    def closeTunnel(self,port):
        if port not in self.tunnels.keys():
            print("No tunnel on port "+str(port))
        t = self.tunnels.pop(port)
        try:
            t.close()
        except Exception as e:
            print("Error closing tunnel: "+str(e))

#################################################################
###################          GETTERS          ###################
#################################################################

    def getName(self):
        return self.name

    def getHosts(self,scope=None):
        return Host.findAll(scope=scope)

    def getHostsNames(self,scope=None):
        return Host.findAllNames(scope=scope)

    def getEndpoints(self,scope=None):
        endpoints = []
        for endpoint in Endpoint.findAll(scope=scope):
            endpoints.append(endpoint)
        return endpoints

    def getTargetsValidList(self,scope=None):
        connections = []
        for connection in Connection.findWorking():
            if scope is None:
                connections.append(str(connection))
            elif connection.inScope() == scope:
                connections.append(str(connection))
        return connections

    def getTargetsList(self,scope=None):
        connections = []
        for connection in Connection.findAll():
            if scope is None:
                connections.append(str(connection))
            elif connection.inScope() == scope:
                connections.append(str(connection))
        return connections

    def getPaths(self):
        return Path.findAll()

    def getUsers(self,scope=None):
        return User.findAll(scope=scope)

    def getCreds(self,scope=None):
        return Creds.findAll(scope=scope)

    def getConnections(self,tested=False,working=False):
        if working:
            return Connection.findWorking()
        if tested:
            return Connection.findTested()
        return Connection.findAll()

    def getOptionsValues(self):
        return self.options.items()

    def getOption(self,key):
        if key not in self.options.keys():
            raise ValueError()
        if self.options[key] == None:
            return None
        return self.options[key]
    
    def getBaseObjects(self,scope=None):
        return Endpoint.findAll(scope=scope) + Creds.findAll(scope=scope) + User.findAll(scope=scope) + Host.findAll(scope=scope)

    def getFoundEndpoints(self,endpoint):
        return Endpoint.findByFound(endpoint)

    def getFoundUsers(self,endpoint):
        return User.findByFound(endpoint)

    def getFoundCreds(self,endpoint):
        return Creds.findByFound(endpoint)

    def close(self):
        for tunnel in self.tunnels.values():
            tunnel.close()
        dbConn.close()
        print("Closing workspace "+self.name)


