import os
import re
from baboossh import User, Creds, Host, Endpoint, Tunnel, Path, Connection, dbConn, Extensions, workspacesDir

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

    #Manually add a endpoint
    def endpoint_add(self, ipaddr, port):
        """Add an :class:`Endpoint` to the workspace

        Args:
            ipaddr (str): the `Endpoint` 's IP address
            ipaddr (str): the `Endpoint` 's port
        """

        Endpoint(ipaddr, port).save()

    def endpoint_del(self, endpoint):
        """Remove an :class:`Endpoint` from the workspace

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
        """

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

    def user_add(self, name):
        """Add a :class:`User` to the workspace

        Args:
            name (str): The `User` 's username
        """

        User(name).save()

    def user_del(self, name):
        """Remove a :class:`User` from the workspace

        Args:
            name (str): The `User` 's username
        """

        user = User.find_one(name=name)
        if user is None:
            print("Could not find user.")
            return False
        return user.delete()

#################################################################
###################           HOSTS           ###################
#################################################################

    def host_del(self, host):
        """Remove a :class:`Host` from the workspace

        Args:
            name (str): The `Host` 's username
        """

        if host not in [host.name for host in Host.find_all()]:
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

    def creds_add(self, creds_type, stmt):
        """Add :class:`Creds` to the workspace

        Args:
            creds_type (str): The `Creds` ' object type
            stmt (`argparse.Namespace`): the rest of the command be parsed by the object
        """

        content = Extensions.getAuthMethod(creds_type).fromStatement(stmt)
        new_creds = Creds(creds_type, content)
        new_creds.save()
        return new_creds.id

    def creds_show(self, creds_id):
        """Show a :class:`Creds` ' properties

        Args:
            creds_id (str): The `Creds` ' id
        """

        if creds_id[0] == '#':
            creds_id = creds_id[1:]
        creds = Creds.find_one(creds_id=creds_id)
        if creds is None:
            print("Specified creds not found")
            return
        creds.show()

    def creds_edit(self, creds_id):
        """Edit a :class:`Creds` ' properties

        Args:
            creds_id (str): The `Creds` ' id
        """

        if creds_id[0] == '#':
            creds_id = creds_id[1:]
        creds = Creds.find_one(creds_id=creds_id)
        if creds is None:
            print("Specified creds not found")
            return
        creds.edit()

    def creds_del(self, creds_id):
        """Delete a :class:`Creds` ' from the workspace

        Args:
            creds_id (str): The `Creds` ' id
        """

        if creds_id[0] == '#':
            creds_id = creds_id[1:]
        creds = Creds.find_one(creds_id=creds_id)
        if creds is None:
            print("Specified creds not found")
            return False
        return creds.delete()

#################################################################
###################          OPTIONS          ###################
#################################################################

    def set_option(self, option, value):
        """Set an option for the `Workspace`

        Args:
            option (str): the option to set
            value (str): the new value
        """

        if option == 'connection':
            if value is None:
                self.options['endpoint'] = None
                self.options['user'] = None
                self.options['creds'] = None

                print("endpoint => "+str(self.options['endpoint']))
                print("user => "+str(self.options['user']))
                print("creds => "+str(self.options['creds']))

            elif '@' not in value or ':' not in value:
                return
            connection = Connection.fromTarget(value)
            if connection is None:
                return
            self.options['endpoint'] = connection.endpoint
            self.options['user'] = connection.user
            self.options['creds'] = connection.creds

            print("endpoint => "+str(self.options['endpoint']))
            print("user => "+str(self.options['user']))
            print("creds => "+str(self.options['creds']))

        if not option in list(self.options.keys()):
            raise ValueError(option+" isn't a valid option.")

        if value is not None:
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
                    creds_id = value[1:]
                else:
                    creds_id = value
                creds = Creds.find_one(creds_id=creds_id)
                if creds is None:
                    raise ValueError
                value = creds
            elif option == "payload":
                value = Extensions.getPayload(value)
            self.options[option] = value
        else:
            self.options[option] = None
        print(option+" => "+str(self.options[option]))

#################################################################
###################        CONNECTIONS        ###################
#################################################################

    def connection_del(self, target):
        """Remove a :class:`Connection` from the workspace

        Args:
            target (str): the `Connection` string
        """

        connection = Connection.fromTarget(target)
        if connection is None:
            print("Connection not found.")
            return False
        return connection.delete()

    def enum_targets(self, target=None, working=None, reachable=None):
        """Returns a list of all the :class:`Connections` to target

        Args:
            target: The target string passed to the command (if any)
        """

        if target is None:
            user = self.options["user"]
            if user is None:
                users = User.find_all(scope=True)
            else:
                #WARNING the "find the object I already have" seems stupid but
                #it refreshes its params from the database. Without this it
                #would be stuck in the state it was when "set"
                users = [User.find_one(user_id=user.id)]
            endpoint = self.options["endpoint"]
            if endpoint is None:
                endpoints = Endpoint.find_all(scope=True)
            else:
                endpoints = [Endpoint.find_one(endpoint_id=endpoint.id)]
            cred = self.options["creds"]
            if cred is None:
                creds = Creds.find_all(scope=True)
            else:
                creds = [Creds.find_one(creds_id=cred.id)]
        else:
            if '@' not in target:
                #TODO
                hosts = Host.find_all(name=target)
                if len(hosts) != 0:
                    ret = []
                    for host in hosts:
                        ret.append(Connection.find_one(endpoint=host.closest_endpoint))
                    return ret
                else:
                    endpoint = Endpoint.find_one(ip_port=target)
                    if endpoint is not None:
                        endpoints = [endpoint]
                        creds = [None]
                        users = [None]
            else:
                auth, sep, endpoint = target.partition('@')
                if endpoint == "*":
                    endpoints = Endpoint.find_all(scope=True)
                else:
                    endpoint = Endpoint.find_one(ip_port=endpoint)
                    if endpoint is None:
                        raise ValueError("Supplied endpoint isn't in workspace")
                    endpoints = [endpoint]
    
                user, sep, cred = auth.partition(":")
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
        ret = {}
        for endpoint in endpoints:
            if reachable is not None and endpoint.reachable == reachable:
                continue
            ret[endpoint] = []
            for user in users:
                for cred in creds:
                    c = Connection(endpoint, user, cred)
                    if working is None:
                        ret[endpoint].append(c)
                    else:
                        if (c.id is not None) == working:
                            ret[endpoint].append(c)
        return ret

    def run(self, targets, payload, stmt):
        """Run a payload on a list of :class:`Connection`

        Args:
            targets ([:class:`Connection`]): the target list
            payload (:class:`Payload`): the payload to run
            stmt (`argparse.Namespace`): the command parameters to pass to the payload
        """

        for connection in targets:
            connection.run(payload, self.workspace_folder, stmt)

    def connect(self, targets, gateway, verbose):
        if gateway == "local":
            gateway = None
        elif gateway != "auto":
            gateway = Connection.fromTarget(gateway)

        for connection in targets:
            if not connection.endpoint.reachable:
                print(str(connection)+"> You must find a path to an endpoint before connecting to it")
                continue

            conn = connection.open(gateway=gateway, verbose=verbose)
            if conn is not None:
                conn.close()
                if gateway != "auto":
                    if gateway is None:
                        path_src = None
                    elif gateway.endpoint.host is None:
                        continue
                    else:
                        path_src = gateway.endpoint.host
                    p = Path(path_src, connection.endpoint)
                    p.save()

#################################################################
###################           PATHS           ###################
#################################################################

    def path_find_existing(self, dst, as_ip=False):
        if dst in [host.name for host in Host.find_all()]:
            hosts = Host.find_all(name=dst)
            if len(hosts) > 1:
                print("Several hosts corresponding. Please target endpoint.")
                return
            dst = str(hosts[0].closest_endpoint)
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
        except NoPathError:
            print("No path could be found to the destination")
            return
        if chain[0] is None:
            chain[0] = "local"
        if as_ip:
            print(" > ".join(str(link.closest_endpoint) if isinstance(link, Host) else str(link) for link in chain))
        else:
            print(" > ".join(str(link) for link in chain))

    def path_del(self, src, dst):
        if src.lower() != "local":
            if src not in [host.name for host in Host.find_all()]:
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

    def path_add(self, src, dst):
        if src.lower() != "local":
            if src not in [host.name for host in Host.find_all()]:
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

    def path_find_new(self, dst):
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

        conn = Connection(dst,None,None)

        if conn.touch(gateway=None):
            p = Path(None, dst)
            p.save()
            print("Could reach target directly, path added.")
            return

        hosts = Host.find_all(scope=True)
        hosts.sort(key=lambda h: h.distance)
        for host in hosts:
            endpoint = host.closest_endpoint
            gateway = Connection.find_one(endpoint=endpoint)
            working = conn.touch(gateway=gateway)
            if working:
                p = Path(host, dst)
                p.save()
                print("Working with gw "+str(endpoint)+" (host "+str(host)+")")
                return
        return

#################################################################
###################           SCOPE           ###################
#################################################################

    def identify_object(self, target):
        if target[0] == "#":
            creds_id = target[1:]
        else:
            creds_id = target
        creds = Creds.find_one(creds_id=creds_id)
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
        obj = self.identify_object(target)
        if obj is None:
            return
        obj.scope = not obj.scope
        obj.save()

#################################################################
###################          TUNNELS          ###################
#################################################################

    def tunnel_open(self, target, port=None):
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

    def tunnel_close(self, port):
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

    def get_objects(self, local=False, hosts=False, connections=False, endpoints=False, users=False, creds=False, tunnels=False, paths=False, scope=None):
        ret = []
        if local:
            ret.append("local")
        if hosts:
            ret = ret + Host.find_all(scope=scope)
        if connections:
            ret = ret + Connection.find_all(scope=scope)
        if endpoints:
            ret = ret + Endpoint.find_all(scope=scope)
        if users:
            ret = ret + User.find_all(scope=scope)
        if creds:
            ret = ret + Creds.find_all(scope=scope)
        if tunnels:
            ret = ret + list(self.tunnels.keys())
        if paths:
            ret = ret + Path.find_all()
        return ret

    def endpoint_search(self, field, val, show_all=False):
        return Endpoint.search(field, val, show_all)

    def host_search(self, field, val, show_all=False):
        return Host.search(field, val, show_all)

    def search_fields(self, obj):
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
