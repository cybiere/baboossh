import os
import re
import ipaddress
import threading
import asyncio
from baboossh import *

class Workspace():
    """A container to hold all related objects

    The workspace allows to separate environments with dedicated folders and
    database. Any object (`Endpoint`, `User`, `Creds`, `Connection`, etc. exists
    only in its workspace to avoid cluttering the user.

    """


#################################################################
###################           INIT            ###################
#################################################################

    @classmethod
    def create(cls, name: str):
        """Create a new workspace

        Create a new workspace with its dedicated folder (in `$HOME/.baboossh` by
        default) and its database.

        """

        if name == "":
            print("Cannot use workspace with empty name")
            raise ValueError
        if re.match(r'^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        workspace_folder = os.path.join(workspacesDir, name)
        if not os.path.exists(workspace_folder):
            try:
                os.mkdir(workspace_folder)
                os.mkdir(os.path.join(workspace_folder, "loot"))
                os.mkdir(os.path.join(workspace_folder, "keys"))
            except OSError:
                print("Creation of the directory %s failed" % workspace_folder)
                raise OSError
            print("Workspace "+name+" created")
        else:
            print("Workspace already exists")
            raise ValueError
        #create database
        dbConn.build(name)
        return Workspace(name)

    def __init__(self, name):
        if name == "":
            raise ValueError("Cannot use workspace with empty name")
        if re.match(r'^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        self.workspace_folder = os.path.join(workspacesDir, name)
        if not os.path.exists(self.workspace_folder):
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
    def __check_is_ip(self, ipaddr):
        try:
            ipaddress.ip_address(ipaddr)
        except ValueError:
            return False
        return True

    #Manually add a endpoint
    def addEndpoint(self, ipaddr, port):
        if not self.__check_is_ip(ipaddr):
            print("The address given isn't a valid IP")
            raise ValueError
        if not port.isdigit():
            print("The port given isn't a positive integer")
            raise ValueError

        newEndpoint = Endpoint(ipaddr, port)
        newEndpoint.save()

    def delEndpoint(self, endpoint):
        try:
            endpoint = Endpoint.find_one(ip_port=endpoint)
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

    def addUser(self, name):
        newUser = User(name)
        newUser.save()

    def delUser(self, name):
        user = User.find_one(name=name)
        if user is None:
            print("Could not find user.")
            return False
        return user.delete()

#################################################################
###################           HOSTS           ###################
#################################################################

    def delHost(self, host):
        if host not in self.getHostsNames():
            print("Not a known Host name.")
            return False
        hosts = Host.find_all(name=host)
        if len(hosts) > 1:
            print("Several hosts corresponding. Please delete endpoints.")
            return False
        return hosts[0].delete()


#################################################################
###################           CREDS           ###################
#################################################################

    def addCreds(self, credsType, stmt):
        credsContent = Extensions.getAuthMethod(credsType).fromStatement(stmt)
        newCreds = Creds(credsType, credsContent)
        newCreds.save()
        return newCreds.id

    def showCreds(self, credsId):
        if credsId[0] == '#':
            credsId = credsId[1:]
        creds = Creds.find_one(creds_id=credsId)
        if creds == None:
            print("Specified creds not found")
            return
        creds.show()

    def editCreds(self, credsId):
        if credsId[0] == '#':
            credsId = credsId[1:]
        creds = Creds.find_one(creds_id=credsId)
        if creds == None:
            print("Specified creds not found")
            return
        creds.edit()

    def delCreds(self, credsId):
        if credsId[0] == '#':
            credsId = credsId[1:]
        creds = Creds.find_one(creds_id=credsId)
        if creds == None:
            print("Specified creds not found")
            return False
        return creds.delete()

#################################################################
###################          OPTIONS          ###################
#################################################################

    def setOption(self, option, value):
        if option == 'connection':
            if value is None:
                self.options['endpoint'] = None
                self.options['user'] = None
                self.options['creds'] = None
                for option in ['endpoint', 'user', 'creds']:
                    print(option+" => "+str(self.getOption(option)))
                return
            if '@' not in value or ':' not in value:
                return
            connection = Connection.fromTarget(value)
            if connection == None:
                return
            self.options['endpoint'] = connection.endpoint
            self.options['user'] = connection.user
            self.options['creds'] = connection.creds
            for option in ['endpoint', 'user', 'creds']:
                print(option+" => "+str(self.getOption(option)))
            return
        if not option in list(self.options.keys()):
            raise ValueError(option+" isn't a valid option.")
        if value != None:
            value = value.strip()
            if option == "endpoint":
                endpoint = Endpoint.find_one(ip_port=value)
                if endpoint is None:
                    raise ValueError
                value = endpoint
            elif option == "user":
                user = User.find_one(name=value)
                if user is None:
                    raise ValueError
                value = user
            elif option == "creds":
                if value[0] == '#':
                    credId = value[1:]
                else:
                    credId = value
                creds = Creds.find_one(creds_id=credId)
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

    def delConnection(self, target):
        connection = Connection.fromTarget(target)
        if connection is None:
            print("Connection not found.")
            return false
        return connection.delete()

    def enumTargets(self,connection=None,working=None):
        """Returns a list of all the :class:`Connections` to target
    
        Args:
            connection: The target string passed to the command (if any)
        """

        if connection is None:
            user = self.getOption("user")
            if user is None:
                users = User.find_all(scope=True)
            else:
                #WARNING the "find the object I already have" seems stupid but
                #it refreshes its params from the database. Without this it
                #would be stuck in the state it was when "set"
                users = [User.find_one(user_id=user.id)]
            endpoint = self.getOption("endpoint")
            if endpoint is None:
                endpoints = Endpoint.find_all(scope=True)
            else:
                endpoints = [Endpoint.find_one(endpoint_id=endpoint.id)]
            cred = self.getOption("creds")
            if cred is None:
                creds = Creds.find_all(scope=True)
            else:
                creds = [Creds.find_one(creds_id=cred.id)]
        else:
            if '@' not in connection:
                #TODO
                hosts = Host.find_all(name=connection)
                if len(hosts) == 0:
                    raise ValueError("No matching Host name in workspace")
                ret = []
                for host in hosts:
                    ret.append(Connection.findWorkingByEndpoint(host.getClosestEndpoint()))
                return ret
            else:
                auth,sep,endpoint = connection.partition('@')
                if endpoint == "*":
                    endpoints = Endpoint.find_all(scope=True)
                else:
                    endpoint  = Endpoint.find_one(ip_port=endpoint)
                    if endpoint is None:
                        raise ValueError("Supplied endpoint isn't in workspace")
                    endpoints = [endpoint]

                user,sep,cred = auth.partition(":")
                if sep == "":
                    raise ValueError("No credentials supplied")

                if user == "*":
                    users = User.find_all(scope=True)
                else:
                    user = User.find_one(name=user)
                    if user is None:
                        raise ValueError("Supplied user isn't in workspace")
                    users = [user]
                if cred == "*":
                    creds = Creds.find_all(scope=True)
                else:
                    if cred[0] == "#":
                        cred = cred[1:]
                    cred = Creds.find_one(creds_id=cred)
                    if cred is None:
                        raise ValueError("Supplied credentials aren't in workspace")
                    creds = [cred]
        ret = []
        for endpoint in endpoints:
            for user in users:
                for cred in creds:
                    c = Connection(endpoint,user,cred)
                    if working is None:
                        ret.append(c)
                    else:
                        if (c.id is not None) == working:
                            ret.append(c)
        return ret

    def run(self, targets, payload, stmt):
        for connection in targets:
            connection.run(payload, self.workspace_folder, stmt)

    def scanTarget(self, target, gateway=None):
        if not isinstance(target, Endpoint):
            target = Endpoint.find_one(ip_port=target)
        if gateway is not None:
            if gateway == "local":
                gateway = None
            else:
                gateway = Connection.fromTarget(gateway)
        else:
            gateway = "auto"
        working = target.scan(gateway=gateway)
        return working


    def connect(self, targets, gateway, verbose):
        if gateway == "local":
            gateway = None
        elif gateway != "auto":
            gateway = Connection.fromTarget(gateway)

        for connection in targets:
            if not connection.endpoint.scanned:
                print(str(connection)+"> You must scan an endpoint before connecting to it")
                continue

            working = connection.testConnect(gateway=gateway, verbose=verbose)
            if working:
                if gateway != "auto":
                    if gateway is None:
                        pathSrc = None
                    elif gateway.endpoint.host is None:
                        continue
                    else:
                        pathSrc = gateway.endpoint.host
                    p = Path(pathSrc, connection.endpoint)
                    p.save()

#################################################################
###################           PATHS           ###################
#################################################################

    def getPathToDst(self, dst, asIp=False):
        if dst in self.getHostsNames():
            hosts = Host.find_all(name=dst)
            if len(hosts) > 1:
                print("Several hosts corresponding. Please target endpoint.")
                return False
            dst = str(hosts[0].getClosestEndpoint())
        try:
            dst = Endpoint.find_one(ip_port=dst)
        except:
            print("Please specify a valid endpoint in the IP:PORT form")
            return
        if dst is None:
            print("The endpoint provided doesn't exist in this workspace")
            return
        if Path.hasDirectPath(dst):
            print("The destination should be reachable from the host")
            return
        try:
            chain = Path.getPath(dst)
        except NoPathException:
            print("No path could be found to the destination")
            return
        if chain[0] is None:
            chain[0] = "Local"
        if asIp:
            print(" > ".join(str(link.getClosestEndpoint()) if isinstance(link,Host) else str(link) for link in chain))
        else:
            print(" > ".join(str(link) for link in chain))

    def delPath(self, src, dst):
        if src.lower() != "local":
            if src not in self.getHostsNames():
                print("Not a known Host name.")
                return False
            hosts = Host.find_all(name=src)
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
            dst = Endpoint.find_one(ip_port=dst)
        except:
            print("Please specify valid destination endpoint in the IP:PORT form")
        if dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return False
        p = Path(src, dst)
        if p.id is None:
            print("The specified Path doesn't exist in this workspace.")
            return False
        return p.delete()

    def addPath(self, src, dst):
        if src.lower() != "local":
            if src not in self.getHostsNames():
                print("Not a known Host name.")
                return
            hosts = Host.find_all(name=src)
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
            dst = Endpoint.find_one(ip_port=dst)
        except:
            print("Please specify valid destination endpoint in the IP:PORT form")
        if dst is None:
            print("The destination endpoint provided doesn't exist in this workspace")
            return
        p = Path(src, dst)
        p.save()
        print("Path saved")

    def findPath(self, dst):
        try:
            dst = Endpoint.find_one(ip_port=dst)
        except:
            print("Please specify a valid endpoint in the IP:PORT form")
            return
        if dst is None:
            print("The endpoint provided doesn't exist in this workspace")
            return
        if Path.hasDirectPath(dst):
            print("The destination should be reachable directly from the host.")
            return

        workingDirect = dst.scan(gateway=None, silent=True)
        if workingDirect:
            p = Path(None, dst)
            p.save()
            print("Could reach target directly, path added.")
            return
        
        for h in Path.getHostsOrderedClosest():
            e = h.getClosestEndpoint()
            gateway = Connection.findWorkingByEndpoint(e)
            working = dst.scan(gateway=gateway, silent=True)
            if working:
                p = Path(h, dst)
                p.save()
                print("Working with gw "+str(e)+" (host "+str(h)+")")
                return
        return

#################################################################
###################           SCOPE           ###################
#################################################################

    def identifyObject(self, target):
        if target[0] == "#":
            credsId = target[1:]
        else:
            credsId = target
        creds = Creds.find_one(creds_id=credsId)
        if creds is not None:
            return creds
        user = User.find_one(name=target)
        if user is not None:
            return user
        try:
            dst = Endpoint.find_one(ip_port=target)
            if dst is not None:
                return dst
        except:
            pass
        hosts = Host.find_all(name=target)
        if len(hosts) > 1:
            print("Multiple hosts matching, use endpoints")
            return None
        if len(hosts) == 1:
            return hosts[0]
        print("Could not identify object.")
        return None

    def scope(self, target):
        obj = self.identifyObject(target)
        if obj is None:
            return False
        obj.scope = not obj.scope
        obj.save()

#################################################################
###################          TUNNELS          ###################
#################################################################

    def getTunnels(self):
        return list(self.tunnels.values())

    def getTunnelsPort(self):
        return list(self.tunnels.keys())

    def openTunnel(self, target, port=None):
        if port is not None and port in self.tunnels.keys():
            print("A tunnel is already opened at port "+str(port))
            return False
        connection = Connection.fromTarget(target)
        try:
            t = Tunnel(connection, port)
        except Exception as e:
            print("Error opening tunnel: "+str(e))
            return False
        self.tunnels[t.port] = t
        return True

    def closeTunnel(self, port):
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

    def getHosts(self, scope=None):
        return Host.find_all(scope=scope)

    def getHostsNames(self, scope=None):
        ret = []
        for host in Host.find_all(scope=scope):
            ret.append(host.name)
        return ret

    def getEndpoints(self, scope=None):
        endpoints = []
        for endpoint in Endpoint.find_all(scope=scope):
            endpoints.append(endpoint)
        return endpoints

    def searchEndpoints(self, field, val, showAll=False):
        return Endpoint.search(field, val, showAll)

    def searchHosts(self, field, val, showAll=False):
        return Host.search(field, val, showAll)

    def getTargetsValidList(self, scope=None):
        connections = []
        for connection in Connection.findAll():
            if scope is None:
                connections.append(str(connection))
            elif connection.scope == scope:
                connections.append(str(connection))
        return connections

    def getTargetsList(self, scope=None):
        connections = []
        for connection in Connection.findAll():
            if scope is None:
                connections.append(str(connection))
            elif connection.scope == scope:
                connections.append(str(connection))
        return connections

    def getPaths(self):
        return Path.find_all()

    def getUsers(self, scope=None):
        return User.find_all(scope=scope)

    def getCreds(self, scope=None):
        return Creds.find_all(scope=scope)

    def getConnections(self):
        return Connection.findAll()

    def getOptionsValues(self):
        return self.options.items()

    def getOption(self, key):
        if key not in self.options.keys():
            raise ValueError()
        if self.options[key] == None:
            return None
        return self.options[key]

    def getBaseObjects(self, scope=None):
        return Endpoint.find_all(scope=scope) + Creds.find_all(scope=scope) + User.find_all(scope=scope) + Host.find_all(scope=scope)

    def getFoundEndpoints(self, endpoint):
        return Endpoint.find_all(found=endpoint)

    def getFoundUsers(self, endpoint):
        return User.find_all(found=endpoint)

    def getFoundCreds(self, endpoint):
        return Creds.find_all(found=endpoint)

    def getSearchFields(self, obj):
        if obj == "Endpoint":
            return Endpoint.search_fields
        if obj == "Host":
            return Host.search_fields
        return []

    def close(self):
        for tunnel in self.tunnels.values():
            tunnel.close()
        dbConn.close()
        print("Closing workspace "+self.name)
