import os
import re
from baboossh import User, Creds, Host, Endpoint, Tunnel
from baboossh import Path, Connection, Db, Extensions, WORKSPACES_DIR, Tag
from baboossh.exceptions import NoPathError, WorkspaceVersionError, ConnectionClosedError
from baboossh.utils import is_workspace_compat
from baboossh.version import BABOOSSH_VERSION

from baboossh.workspace.endpoints import EndpointsMixin
from baboossh.workspace.users import UsersMixin
from baboossh.workspace.hosts import HostsMixin
from baboossh.workspace.creds import CredsMixin
from baboossh.workspace.options import OptionsMixin
from baboossh.workspace.connections import ConnectionsMixin
from baboossh.workspace.tags import TagsMixin
from baboossh.workspace.paths import PathsMixin
from baboossh.workspace.probe import ProbeMixin
from baboossh.workspace.scope import ScopeMixin
from baboossh.workspace.tunnels import TunnelsMixin

__all__ = ["Workspace"]

class Workspace(
        EndpointsMixin,
        UsersMixin,
        HostsMixin,
        CredsMixin,
        OptionsMixin,
        ConnectionsMixin,
        TagsMixin,
        PathsMixin,
        ProbeMixin,
        ScopeMixin,
        TunnelsMixin,
    ):
    """A container to hold all related objects

    The workspace allows to separate environments with dedicated folders and
    database. Any object (`Endpoint`, `User`, `Creds`, `Connection`, etc. exists
    only in its workspace to avoid cluttering the user.

    This class' behavior is split across mixins in this package, one per
    domain (`endpoints.py`, `hosts.py`, `paths.py`, etc.) — this file only
    keeps object construction (this section) and the small set of helpers
    shared across every domain (`GETTERS` section below).
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
            print('Invalid characters in workspace name. \
                    Allowed characters are letters, numbers and ._-')
            raise ValueError
        workspace_folder = os.path.join(WORKSPACES_DIR, name)
        if not os.path.exists(workspace_folder):
            try:
                os.mkdir(workspace_folder)
                os.mkdir(os.path.join(workspace_folder, "loot"))
                os.mkdir(os.path.join(workspace_folder, "keys"))
                with open(os.path.join(workspace_folder, "workspace.version"), "w") as file:
                    file.write(BABOOSSH_VERSION)
            except OSError:
                print("Creation of the directory " + workspace_folder + " failed")
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
            print('Invalid characters in workspace name. \
                    Allowed characters are letters, numbers and ._-')
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
###################          GETTERS          ###################
#################################################################

    def get_objects(self, local=False, hosts=False, connections=False, endpoints=False, \
            users=False, creds=False, tunnels=False, paths=False, scope=None, tags=None):
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
            ret = ret + list(self.tunnels.values())
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
            if connection.transport is not None:
                connection.close()
        for obj in self.store.values():
            for instance in obj.values():
                del instance
        Db.close()
        type(self).active = None
        print("Closing workspace "+self.name)
