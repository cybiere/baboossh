import os
import re
from baboossh import User, Creds, Host, Endpoint, Tunnel, Path, Connection, Db, Extensions, WORKSPACES_DIR, Tag
from baboossh.exceptions import NoPathError, WorkspaceVersionError, ConnectionClosedError
from baboossh.utils import is_workspace_compat, BABOOSSH_VERSION

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
                with open(os.path.join(workspace_folder, "workspace.version"), "w") as f:
                    f.write(BABOOSSH_VERSION)
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
        try:
            with open(os.path.join(self.workspace_folder, "workspace.version"), "r") as f:
                self.version = f.read()
        except FileNotFoundError:
            self.version = "1.0.x"
        if not is_workspace_compat(self.version):
            raise WorkspaceVersionError(BABOOSSH_VERSION, self.version)
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

        if endpoint[0] == "!":
            tag = Tag(endpoint[1:])
            for endpoint in tag.endpoints:
                self.unstore(endpoint.delete())
            return True
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

    def endpoint_tag(self, endpoint, tagname):
        """Add a :class:`Tag` to an :class:`Endpoint`

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if endpoint is None:
            print("Could not find endpoint.")
            return False
        endpoint.tag(tagname)
        return True

    def endpoint_untag(self, endpoint, tagname):
        """Remove a :class:`Tag` from an :class:`Endpoint`

        Args:
            endpoint (str): the `Endpoint` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            endpoint = Endpoint.find_one(ip_port=endpoint)
        except ValueError:
            print("Could not find endpoint.")
            return False
        if endpoint is None:
            print("Could not find endpoint.")
            return False
        endpoint.untag(tagname)
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

    def host_tag(self, host, tagname):
        """Add a :class:`Tag` to an :class:`Host`

        Args:
            host (str): the `Host` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            host = Host.find_one(name=host)
        except ValueError:
            print("Could not find host.")
            return False
        if host is None:
            print("Could not find host.")
            return False
        for endpoint in host.endpoints:
            endpoint.tag(tagname)
        return True

    def host_untag(self, host, tagname):
        """Remove a :class:`Tag` from an :class:`Host`

        Args:
            host (str): the `Host` 's string (ip:port)
            tagname (str): the :class:`Tag` name
        """

        if tagname[0] == "!":
            tagname = tagname[1:]
        try:
            host = Host.find_one(name=host)
        except ValueError:
            print("Could not find host.")
            return False
        if host is None:
            print("Could not find host.")
            return False
        for endpoint in host.endpoints:
            endpoint.untag(tagname)
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
                if value[0] == "!":
                    value = Tag(value[1:])
                else:
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

    def connection_close(self, target):
        """Close a :class:`Connection` and any connection or tunnel using it

        Args:
            target (str): the `Connection` string
        """

        connection = Connection.from_target(target)
        if connection is None:
            print("Connection not found.")
            return False
        return connection.close()

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

    def enum_probe(self, target=None, again=False):
        if target is not None:
            if target == "*":
                endpoints = Endpoint.find_all(scope=True)
            elif target[0] == "!":
                tag = Tag(target[1:])
                endpoints = tag.endpoints
            else:
                endpoint = Endpoint.find_one(ip_port=target)
                if endpoint is None:
                    raise ValueError("Supplied endpoint isn't in workspace")
                return [endpoint]
        elif self.options["endpoint"] is not None:
            if isinstance(self.options["endpoint"], Tag):
                return self.options["endpoint"].endpoints
            return [self.options["endpoint"]]
        else:
            endpoints = Endpoint.find_all(scope=True)

        if not again:
            endpoints = [endpoint for endpoint in endpoints if not endpoint.reachable]

        return endpoints

    def enum_connect(self, target=None, force=False, unprobed=False):
        if target is not None:
            if '@' not in target:
                host = Host.find_one(name=target)
                if host is not None:
                    conn = Connection.find_one(endpoint=host.closest_endpoint)
                    if conn is not None:
                        return [conn]
                raise ValueError("Supplied value doesn't match a known host or a connection string")

            auth, sep, endpoint = target.partition('@')
            if endpoint == "*":
                endpoints = Endpoint.find_all(scope=True)
            elif endpoint[0] == "!":
                tag = Tag(endpoint[1:])
                endpoints = tag.endpoints
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
            if len(endpoints)*len(users)*len(creds) == 1:
                return [Connection(endpoints[0], users[0], creds[0])]
        else:
            user = self.options["user"]
            if user is None:
                users = User.find_all(scope=True)
            else:
                users = [user]
            endpoint = self.options["endpoint"]
            if isinstance(endpoint, Tag):
                endpoints = endpoint.endpoints
            elif endpoint is None:
                endpoints = Endpoint.find_all(scope=True)
            else:
                endpoints = [endpoint]
            cred = self.options["creds"]
            if cred is None:
                creds = Creds.find_all(scope=True)
            else:
                creds = [cred]
            if len(endpoints)*len(users)*len(creds) == 1:
                return [Connection(endpoints[0], users[0], creds[0])]

        ret = []
        for endpoint in endpoints:
            if not unprobed and not endpoint.reachable:
                continue
            for user in users:
                if len(creds) != 1:
                    working_connections = Connection.find_all(endpoint=endpoint, user=user)
                    if not force and working_connections:
                        print("Connection already found with user "+str(user)+" on endpoint "+str(endpoint)+", creds bruteforcing is disabled. Specify creds or use --force.")
                        continue
                for cred in creds:
                    conn = Connection(endpoint, user, cred)
                    if force:
                        ret.append(conn)
                    else:
                        if conn.id is None:
                            ret.append(conn)
        return ret

    def enum_run(self, target=None):
        if target is not None:
            if '@' not in target:
                host = Host.find_one(name=target)
                if host is not None:
                    conn = Connection.find_one(endpoint=host.closest_endpoint)
                    if conn is not None:
                        return [conn]
                raise ValueError("Supplied value doesn't match a known host or a connection string")

            auth, sep, endpoint = target.partition('@')
            if endpoint == "*":
                endpoint = None
            elif endpoint[0] == "!":
                tag = Tag(endpoint[1:])
                endpoints = tag.endpoints
            else:
                endpoint = Endpoint.find_one(ip_port=endpoint)
                if endpoint is None:
                    raise ValueError("Supplied endpoint isn't in workspace")

            user, sep, cred = auth.partition(":")
            if sep == "":
                raise ValueError("No credentials supplied")
            if user == "*":
                user = None
            else:
                user = User.find_one(name=user)
                if user is None:
                    raise ValueError("Supplied user isn't in workspace")
            if cred == "*":
                cred = None
            else:
                if cred[0] == "#":
                    cred = cred[1:]
                cred = Creds.find_one(creds_id=cred)
                if cred is None:
                    raise ValueError("Supplied credentials aren't in workspace")
        else:
            user = self.options["user"]
            endpoint = self.options["endpoint"]
            cred = self.options["creds"]

        return Connection.find_all(endpoint=endpoint, user=user, creds=cred)


    def run(self, targets, payload, stmt, verbose=False):
        """Run a payload on a list of :class:`Connection`

        Args:
            targets ([:class:`Connection`]): the target list
            payload (:class:`Payload`): the payload to run
            stmt (`argparse.Namespace`): the command parameters to pass to the payload
        """

        for connection in targets:
            if not connection.endpoint.reachable:
                raise NoPathError

            connection.run(payload, self.workspace_folder, stmt, verbose=verbose)

    def connect(self, targets, verbose=False, probe_auto=False):
        nb_working = 0
        for connection in targets:
            if not connection.endpoint.reachable:
                if probe_auto:
                    self.probe([connection.endpoint], verbose=verbose)
                    if not connection.endpoint.reachable:
                        print("\033[1;31mError\033[0m: could not find path to the target.")
                        continue
                else:
                    print("\033[1;31mError\033[0m: could not find path to the target.")
                    continue
            if connection.open(verbose=verbose, target=True):
                nb_working = nb_working + 1
        return nb_working

#################################################################
###################           TAGS            ###################
#################################################################

    def tag_show(self, name):
        if name[0] == "!":
            name = name[1:]
        tag = Tag.find_one(name=name)
        if tag is None:
            print("No tag matching "+name)
            return
        print("Tag "+name+" members :")
        for endpoint in tag.endpoints:
            print(" - "+str(endpoint))

    def tag_del(self, name):
        if name[0] == "!":
            name = name[1:]
        tag = Tag.find_one(name=name)
        if tag is None:
            print("No tag matching "+name)
            return
        tag.delete()
        print("Tag "+name+" deleted")

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
        if str(src).lower() != "local":
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
        self.unstore(path.delete())
        return True

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

    def probe(self, targets, gateway="auto", verbose=False, find_new=False):
        for endpoint in targets:
            print("Probing \033[1;34m"+str(endpoint)+"\033[0m > ", end="", flush=True)
            if verbose:
                print("")

            conn = Connection(endpoint, None, None)
            working = False
            if not find_new and endpoint.reachable and str(gateway) == "auto":
                if verbose:
                    print("\nEndpoint is supposed to be reachable, trying...")
                working = conn.probe(verbose=verbose)
                host = Host.find_one(prev_hop_to=endpoint)
            if not working and str(gateway) != "auto":
                if verbose:
                    print("\nA gateway was given, trying...")
                if gateway == "local":
                    gateway_conn = None
                    host = None
                else:
                    host = Host.find_one(name=gateway)
                    gateway_conn = Connection.find_one(endpoint=host.closest_endpoint)
                try:
                    working = conn.probe(gateway=gateway_conn, verbose=verbose)
                except ConnectionClosedError as exc:
                    print("\nError: "+str(exc))
                    return
            if not working and not find_new:
                try:
                    Path.get(endpoint)
                except NoPathError:
                    pass
                else:
                    if verbose:
                        print("\nThere is an existing path to the Endpoint, trying...")
                    working = conn.probe(verbose=verbose)
                    host = Host.find_one(prev_hop_to=endpoint)
                    if not working and host is not None:
                        self.path_del(host, endpoint)
            if not working:
                if verbose:
                    print("\nTrying to reach directly from local...")
                host = None
                working = conn.probe(gateway=None, verbose=verbose)
            if not working:
                if verbose:
                    print("\nTrying from every Host from closest to furthest...")
                hosts = Host.find_all(scope=True)
                hosts.sort(key=lambda h: h.distance)
                working = False
                for host in hosts:
                    gateway_endpoint = host.closest_endpoint
                    loop_gateway = Connection.find_one(endpoint=gateway_endpoint)
                    working = conn.probe(gateway=loop_gateway, verbose=verbose)
                    if working:
                        break

            if working:
                path = Path(host, endpoint)
                path.save()
                if host is None:
                    print("\033[1;32mOK\033[0m: reached directly from \033[1;34mlocal\033[0m.")
                else:
                    print("\033[1;32mOK\033[0m: reached using \033[1;34m"+str(host)+"\033[0m as gateway")
            else:
                print("\033[1;31mKO\033[0m: could not reach the endpoint.")
            if verbose:
                print("########################\n")

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

    def get_objects(self, local=False, hosts=False, connections=False, endpoints=False, users=False, creds=False, tunnels=False, paths=False, scope=None, tags=None):
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
        if tags:
            ret = ret + Tag.find_all()
        return ret

    def endpoint_search(self, field, val, show_all=False, add_tag=None):
        endpoints = Endpoint.search(field, val, show_all)
        if add_tag is not None:
            for endpoint in endpoints:
                endpoint.tag(add_tag)
        return endpoints

    def host_search(self, field, val, show_all=False, add_tag=None):
        hosts = Host.search(field, val, show_all)
        if add_tag is not None:
            for host in hosts:
                for endpoint in host.endpoints:
                    endpoint.tag(add_tag)
        return hosts

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
        for connection in Connection.find_all():
            if connection.conn is not None:
                connection.close()
        for obj in self.store.values():
            for instance in obj.values():
                del instance
        Db.close()
        type(self).active = None
        print("Closing workspace "+self.name)
