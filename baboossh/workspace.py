import os
import re
from baboossh import User, Creds, Host, Endpoint, Tunnel, Path, Connection, Db, Extensions, WORKSPACES_DIR
from baboossh.exceptions import NoPathError

class Workspace():
    """A container to hold all related objects

    The workspace allows to separate environments with dedicated folders and
    database. Any object (`Endpoint`, `User`, `Creds`, `Connection`, etc. exists
    only in its workspace to avoid cluttering the user.

    """

    active = None

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
        workspace_folder = os.path.join(WORKSPACES_DIR, name)
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
        Db.build(name)
        return Workspace(name)

    def __init__(self, name):
        if name == "":
            raise ValueError("Cannot use workspace with empty name")
        if re.match(r'^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        self.workspace_folder = os.path.join(WORKSPACES_DIR, name)
        if not os.path.exists(self.workspace_folder):
            raise ValueError("Workspace "+name+" does not exist")
        Db.connect(name)
        self.name = name
        self.tunnels = {}
        self.options = {
            "endpoint":None,
            "user":None,
            "creds":None,
            "payload":None,
            "params":None,
                }
        type(self).active = self
        self.store = {
            "Connection": {},
            "Creds": {},
            "Endpoint": {},
            "Host": {},
            "Path": {},
            "User": {},
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
        if self.options["endpoint"] == endpoint:
            self.set_option("endpoint", None)
        self.unstore(endpoint.delete())
        return True

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
        if self.options["user"] == user:
            self.set_option("user", None)
        self.unstore(user.delete())
        return True

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
        host = Host.find_one(name=host)
        self.unstore(host.delete())
        return True


#################################################################
###################           CREDS           ###################
#################################################################

    def creds_add(self, creds_type, stmt):
        """Add :class:`Creds` to the workspace

        Args:
            creds_type (str): The `Creds` ' object type
            stmt (`argparse.Namespace`): the rest of the command be parsed by the object
        """

        content = Extensions.auths[creds_type].fromStatement(stmt)
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
        if self.options["creds"] == creds:
            self.set_option("creds", None)
        self.unstore(creds.delete())
        return True

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
            connection = Connection.from_target(value)
            if connection is None:
                return
            self.options['endpoint'] = connection.endpoint
            self.options['user'] = connection.user
            self.options['creds'] = connection.creds

            print("endpoint => "+str(self.options['endpoint']))
            print("user => "+str(self.options['user']))
            print("creds => "+str(self.options['creds']))
            return

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
                value = Extensions.payloads[value]
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

        connection = Connection.from_target(target)
        if connection is None:
            print("Connection not found.")
            return False
        self.unstore(connection.delete())
        return True

    def __enum_from_statement(self, target):
        if '@' not in target:
            host = Host.find_one(name=target)
            if host is not None:
                conn = Connection.find_one(endpoint=host.closest_endpoint)
                return ([conn.endpoint], [conn.user], [conn.creds])
            endpoint = Endpoint.find_one(ip_port=target)
            if endpoint is None:
                raise ValueError("Supplied value doesn't match a host nor an endpoint")
            return ([endpoint], [None], [None])
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
        return (endpoints, users, creds)


    def enum_targets(self, target=None, force=False, working=False):
        """Get the active target(s)

        #TODO

        Args:
            target: The target string passed to the command (if any)

        Returns:
            A dict where each <value> is a List of :class:`Connection` s to the
                <key> :class:`Endpoint`
        """

        if target is None:
            user = self.options["user"]
            if user is None:
                users = User.find_all(scope=True)
            else:
                users = [user]
            endpoint = self.options["endpoint"]
            if endpoint is None:
                endpoints = Endpoint.find_all(scope=True)
            else:
                endpoints = [endpoint]
            cred = self.options["creds"]
            if cred is None:
                creds = Creds.find_all(scope=True)
            else:
                creds = [cred]
        else:
            endpoints, users, creds = self.__enum_from_statement(target)

        ret = {}
        for endpoint in endpoints:
            if not force and not endpoint.reachable:
                continue
            ret[endpoint] = []
            for user in users:
                working_connections = Connection.find_all(endpoint=endpoint, user=user)
                if not working and not force and working_connections:
                    #We already have something working with this user & endpoint, ignore
                    continue
                for cred in creds:
                    conn = Connection(endpoint, user, cred)
                    if working:
                        if conn.id is not None:
                            ret[endpoint].append(conn)
                    elif force:
                        ret[endpoint].append(conn)
                    else:
                        if conn.id is None:
                            ret[endpoint].append(conn)
        return ret

    def run(self, targets, payload, stmt, probe_auto):
        """Run a payload on a list of :class:`Connection`

        Args:
            targets ([:class:`Connection`]): the target list
            payload (:class:`Payload`): the payload to run
            stmt (`argparse.Namespace`): the command parameters to pass to the payload
        """

        for connection in targets:
            if not connection.endpoint.reachable:
                if probe_auto:
                    self.probe([connection.endpoint])
                    if not connection.endpoint.reachable:
                        raise NoPathError
                else:
                    raise NoPathError

            connection.run(payload, self.workspace_folder, stmt)

    def connect(self, targets, gateway="auto", verbose=False, probe_auto=False):
        if gateway == "local":
            gateway = None
        elif gateway != "auto":
            gateway = Connection.find_one(endpoint=Host.find_one(name=gateway).closest_endpoint)

        for connection in targets:
            if not connection.endpoint.reachable:
                if probe_auto:
                    self.probe([connection.endpoint], gateway, verbose)
                    if not connection.endpoint.reachable:
                        raise NoPathError
                else:
                    raise NoPathError

            if connection.open(gateway=gateway, verbose=verbose):
                connection.close()
                if gateway != "auto":
                    if gateway is None:
                        path_src = None
                    elif gateway.endpoint.host is None:
                        continue
                    else:
                        path_src = gateway.endpoint.host
                    path = Path(path_src, connection.endpoint)
                    path.save()

#################################################################
###################           PATHS           ###################
#################################################################

    def path_find_existing(self, dst, as_ip=False):
        if dst in [host.name for host in Host.find_all()]:
            host = Host.find_one(name=dst)
            dst = host.closest_endpoint
        else:
            try:
                dst = Endpoint.find_one(ip_port=dst)
            except:
                print("Please specify a valid endpoint in the IP:PORT form")
                return
        if dst is None:
            print("The endpoint provided doesn't exist in this workspace")
            return
        if Path.direct(dst):
            print("The destination should be reachable from the host")
            return
        try:
            chain = Path.get(dst)
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
            src = Host.find_one(name=src)
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
        path = Path(src, dst)
        if path.id is None:
            print("The specified Path doesn't exist in this workspace.")
            return False
        self.unstore(p.delete())

    def path_add(self, src, dst):
        if src.lower() != "local":
            if src not in [host.name for host in Host.find_all()]:
                print("Not a known Host name.")
                return
            src = Host.find_one(name=src)
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
        path = Path(src, dst)
        path.save()
        print("Path saved")

#################################################################
###################           PROBE           ###################
#################################################################

    def probe(self, targets, gateway="auto", verbose=False, force=False):
        if gateway != "auto":
            if gateway == "local":
                gateway = None
                host = None
            else:
                host = Host.find_one(name=gateway)
                gateway = Connection.find_one(endpoint=host.closest_endpoint)

        for endpoint in targets:
            conn = Connection(endpoint, None, None)
            if not force and endpoint.reachable and str(gateway) == "auto":
                working = conn.probe()
                host = Host.find_one(prev_hop_to=endpoint)
            elif str(gateway) != "auto":
                working = conn.probe(gateway=gateway)
            else:
                try:
                    Path.get(endpoint)
                except NoPathError:
                    host = None
                    working = conn.probe(gateway=None)
                    if not working:
                        hosts = Host.find_all(scope=True)
                        hosts.sort(key=lambda h: h.distance)
                        working = False
                        for host in hosts:
                            gateway_endpoint = host.closest_endpoint
                            gateway = Connection.find_one(endpoint=gateway_endpoint)
                            working = conn.probe(gateway=gateway)
                            if working:
                                break
                else:
                    working = conn.probe()
                    host = Host.find_one(prev_hop_to=endpoint)

            if working:
                path = Path(host, endpoint)
                path.save()
                if host is None:
                    print("Working directly from local")
                else:
                    print("Working using "+str(host)+" as gateway")

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
        host = Host.find_one(name=target)
        if host is not None:
            return host
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
        connection = Connection.from_target(target)
        try:
            tun = Tunnel(connection, port)
        except Exception as exc:
            print("Error opening tunnel: "+str(exc))
            return False
        self.tunnels[tun.port] = tun
        return True

    def tunnel_close(self, port):
        if port not in self.tunnels.keys():
            print("No tunnel on port "+str(port))
        tun = self.tunnels.pop(port)
        try:
            tun.close()
        except Exception as exc:
            print("Error closing tunnel: "+str(exc))

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

    def unstore(self, data):
        for obj_type, objects in data.items():
            for item in objects:
                obj = self.store[obj_type].pop(item, None)
                if obj is not None:
                    print('Removed '+str(obj)+' from '+obj_type)

    def close(self):
        for tunnel in self.tunnels.values():
            tunnel.close()
        for obj in self.store.values():
            for instance in obj.values():
                del instance
        Db.close()
        type(self).active = None
        print("Closing workspace "+self.name)
