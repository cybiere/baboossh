#!/usr/bin/env python3

"""BabooSSH interactive interface

This module contains the whole user interface for BabooSSH, extending
cmd2 and providing completion & command syntax help. It also loads the
extensions on startup.

Typical usage example:

    from baboossh.shell import Shell
    Shell().cmdloop()

"""

import os
import re
import argparse
import shutil
import cmd2
import tabulate
from baboossh.exceptions import *
from baboossh.utils import workspacesDir
from baboossh.extensions import Extensions
from baboossh.workspace import Workspace

def yes_no(prompt, default=None):
    """Simple Yes/No prompt to ask questions

    Args:
        prompt (str): The question to ask
        default (bool): The default answer

    Returns:
        A `bool` with `True` for yes else `False`
    """

    if default is None:
        choices = "[y, n]"
    elif default:
        choices = "[Y, n]"
    else:
        choices = "[y, N]"
    a = ""
    while a not in ["y", "n"]:
        a = input(prompt+" "+choices+" ").lower()
        if a == "" and default is not None:
            a = "y" if default else "n"
    return a == "y"


Extensions.load()

class Shell(cmd2.Cmd):
    """BabooSSH Shell interface

    This class extends cmd2.Cmd to build the user interface.

    Attributes:
        intro (str): The banner printed on program start
        prompt (str): The default prompt
        workspace (Workspace): The current open baboossh.Workspace
        debug (bool): Boolean for debug output
    """


#################################################################
###################          GETTERS          ###################
#################################################################

    def __get_option_creds(self):
        return self.workspace.get_objects(creds=True, scope=True)

    def __get_option_hosts(self):
        return self.workspace.get_objects(hosts=True, scope=True)

    def __get_arg_workspaces(self):
        return [name for name in os.listdir(workspacesDir) if os.path.isdir(os.path.join(workspacesDir, name))]

    def __get_option_gateway(self):
        ret = ["local"]
        endpoints = self.workspace.get_objects(endpoints=True, scope=True)
        for endpoint in endpoints:
            if endpoint.connection is not None:
                ret.append(endpoint)
        return ret

    def __get_option_user(self):
        return self.workspace.get_objects(users=True, scope=True)

    def __get_option_endpoint(self):
        return self.workspace.get_objects(endpoints=True, scope=True)

    def __get_option_payload(self):
        return Extensions.payloadsAvail()

    def __get_option_connection(self):
        return self.workspace.get_objects(connections=True, scope=True)

    def __get_search_fields_endpoint(self):
        return self.workspace.search_fields("Endpoint")

    def __get_search_fields_host(self):
        return self.workspace.search_fields("Host")

    def __get_open_tunnels(self):
        return self.workspace.get_objects(tunnels=True)

    def __get_run_targets(self):
        return self.workspace.get_objects(connections=True, hosts=True, endpoints=True, scope=True)

    def __get_host_or_local(self):
        return self.workspace.get_objects(local=True, hosts=True, scope=True)

    def __get_endpoint_or_host(self):
        return self.workspace.get_objects(hosts=True, endpoints=True, scope=True)

#################################################################
###################         WORKSPACE         ###################
#################################################################

    def __workspace_list(self, stmt):
        print("Existing workspaces :")
        workspaces = [name for name in os.listdir(workspacesDir) if os.path.isdir(os.path.join(workspacesDir, name))]
        for workspace in workspaces:
            if workspace == self.workspace.name:
                print(" -["+workspace+"]")
            else:
                print(" - "+workspace)

    def __workspace_add(self, stmt):
        name = vars(stmt)['name']
        #Check if name was given
        if re.match(r'^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            return
        #Check if workspace already exists
        if os.path.exists(os.path.join(workspacesDir, name)):
            print("Workspace already exists")
            return
        try:
            new_workspace = Workspace.create(name)
        except (OSError, ValueError) as exc:
            print("Workspace creation failed: "+str(exc))
        else:
            self.workspace = new_workspace

    def __workspace_use(self, stmt):
        name = vars(stmt)['name']
        #Check if workspace already exists
        if not os.path.exists(os.path.join(workspacesDir, name)):
            print("Workspace does not exist")
            return
        try:
            new_workspace = Workspace(name)
        except ValueError as exc:
            print("Workspace change failed: "+str(exc))
        else:
            self.workspace = new_workspace

    def __workspace_del(self, stmt):
        name = vars(stmt)['name']
        #Check if workspace already exists
        if not os.path.exists(os.path.join(workspacesDir, name)):
            print("Workspace does not exist")
            return
        if self.workspace.name == name:
            print("Cannot delete current workspace, please change workspace first.")
            return
        if not yes_no("Are you sure you want to delete workspace "+name+"?", default=False):
            return
        shutil.rmtree(os.path.join(workspacesDir, name))
        print("Workspace deleted !")

    __parser_wspace = argparse.ArgumentParser(prog="workspace")
    __subparser_wspace = __parser_wspace.add_subparsers(title='Actions', help='Available actions')
    __parser_wspace_list = __subparser_wspace.add_parser("list", help='List workspaces')
    __parser_wspace_add = __subparser_wspace.add_parser("add", help='Add a new workspace')
    __parser_wspace_add.add_argument('name', help='New workspace name')
    __parser_wspace_use = __subparser_wspace.add_parser("use", help='Change current workspace')
    __parser_wspace_use.add_argument('name', help='Name of workspace to use', choices_method=__get_arg_workspaces)
    __parser_wspace_del = __subparser_wspace.add_parser("delete", help='Delete workspace')
    __parser_wspace_del.add_argument('name', help='Name of workspace to delete', choices_method=__get_arg_workspaces)

    __parser_wspace_list.set_defaults(func=__workspace_list)
    __parser_wspace_add.set_defaults(func=__workspace_add)
    __parser_wspace_use.set_defaults(func=__workspace_use)
    __parser_wspace_del.set_defaults(func=__workspace_del)

    @cmd2.with_argparser(__parser_wspace)
    def do_workspace(self, stmt: argparse.Namespace):
        '''Manage workspaces

        List, add, delete and switch workspaces.

        '''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__workspace_list(stmt)

#################################################################
###################           HOSTS           ###################
#################################################################

    def __host_print(self, hosts):
        data = []
        for host in hosts:
            endpoints = ""
            for endpoint in host.endpoints:
                if endpoints == "":
                    endpoints = str(endpoint)
                else:
                    endpoints = endpoints + ", "+str(endpoint)
            scope = "o" if host.scope else ""
            data.append([scope, host.id, host.name, host.distance, endpoints])
        print(tabulate.tabulate(data, headers=["", "ID", "Hostname", "Dist", "Endpoints"]))

    def __host_list(self, stmt):
        print("Current hosts in workspace:")
        show_all = getattr(stmt, 'all', False)
        hosts = self.workspace.get_objects(hosts=True, scope=None if show_all else True)
        if not hosts:
            print("No hosts in current workspace")
            return
        self.__host_print(hosts)

    def __host_search(self, stmt):
        show_all = getattr(stmt, 'all', False)
        field = vars(stmt)['field']
        allowed_fields = self.__get_search_fields_host()
        if field not in allowed_fields:
            print("Invalid field specified, use one of "+str(allowed_fields)+".")
            return
        val = vars(stmt)['val']
        hosts = self.workspace.searchHosts(field, val, show_all)
        print("Search result for hosts:")
        if not hosts:
            print("No results")
            return
        self.__host_print(hosts)

    def __host_del(self, stmt):
        host = getattr(stmt, 'host', None)
        self.workspace.host_del(host)

    __parser_host = argparse.ArgumentParser(prog="host")
    __subparser_host = __parser_host.add_subparsers(title='Actions', help='Available actions')
    __parser_host_list = __subparser_host.add_parser("list", help='List hosts')
    __parser_host_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_host_search = __subparser_host.add_parser("search", help='Search a host')
    __parser_host_search.add_argument('field', help='Field to search in', choices_method=__get_search_fields_host)
    __parser_host_search.add_argument('val', help='Value to search')

    __parser_host_del = __subparser_host.add_parser("delete", help='Delete host')
    __parser_host_del.add_argument('host', help='Host name', choices_method=__get_option_hosts)

    __parser_host_list.set_defaults(func=__host_list)
    __parser_host_search.set_defaults(func=__host_search)
    __parser_host_del.set_defaults(func=__host_del)

    @cmd2.with_argparser(__parser_host)
    def do_host(self, stmt):
        '''Manage hosts'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__host_list(stmt)

#################################################################
###################         ENDPOINTS         ###################
#################################################################

    def __endpoint_print(self, endpoints):
        data = []
        for endpoint in endpoints:
            scope = "o" if endpoint.scope else ""
            conn = endpoint.connection
            if conn is None:
                conn = ""
            host = endpoint.host
            if host is None:
                host = ""
            if endpoint.reachable is None:
                reachable = "?"
            else:
                reachable = str(endpoint.reachable)
            if endpoint.distance is None:
                distance = ""
            else:
                distance = str(endpoint.distance)
            data.append([scope, endpoint, host, reachable, distance, conn])
        print(tabulate.tabulate(data, headers=["", "Endpoint", "Host", "Reachable", "Dist", "Working connection"]))

    def __endpoint_list(self, stmt):
        print("Current endpoints in workspace:")
        show_all = getattr(stmt, 'all', False)
        reachable = getattr(stmt, 'reachable', None)
        conn = getattr(stmt, 'conn', None)
        endpoints = self.workspace.get_objects(endpoints=True, scope=None if show_all else True)
        if not endpoints:
            print("No endpoints in current workspace")
            return

        endpoint_list = []
        for endpoint in endpoints:
            if reachable is not None:
                flag_reachable = reachable == "true"
                if endpoint.reachable != flag_reachable:
                    continue
            if conn is not None:
                flag_conn = conn == "true"
                if (endpoint.connection is None) == flag_conn:
                    continue
            endpoint_list.append(endpoint)
        self.__endpoint_print(endpoint_list)

    def __endpoint_add(self, stmt):
        ip_add = vars(stmt)['ip']
        port = str(vars(stmt)['port'])
        try:
            self.workspace.endpoint_add(ip_add, port)
        except Exception as e:
            print("Endpoint addition failed: "+str(e))
        else:
            print("Endpoint "+ip_add+":"+port+" added.")

    def __endpoint_del(self, stmt):
        endpoint = vars(stmt)['endpoint']
        self.workspace.endpoint_del(endpoint)

    def __endpoint_search(self, stmt):
        show_all = getattr(stmt, 'all', False)
        field = vars(stmt)['field']
        allowed_fields = self.__get_search_fields_endpoint()
        if field not in allowed_fields:
            print("Invalid field specified, use one of "+str(allowed_fields)+".")
            return
        val = vars(stmt)['val']
        endpoints = self.workspace.endpoint_search(field, val, show_all)
        print("Search result for endpoints:")
        if not endpoints:
            print("No results")
            return
        self.__endpoint_print(endpoints)


    __parser_endpoint = argparse.ArgumentParser(prog="endpoint")
    __subparser_endpoint = __parser_endpoint.add_subparsers(title='Actions', help='Available actions')
    __parser_endpoint_list = __subparser_endpoint.add_parser("list", help='List endpoints')
    __parser_endpoint_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_endpoint_list.add_argument("-r", "--reachable", help="Show only reachable endpoints", nargs='?', choices=["true", "false"], const="true")
    __parser_endpoint_list.add_argument("-c", "--conn", help="Show only endpoints with connection", nargs='?', choices=["true", "false"], const="true")
    __parser_endpoint_add = __subparser_endpoint.add_parser("add", help='Add a new endpoint')
    __parser_endpoint_add.add_argument('ip', help='New endpoint ip')
    __parser_endpoint_add.add_argument('port', help='New endpoint port', type=int, default=22, nargs='?')
    __parser_endpoint_search = __subparser_endpoint.add_parser("search", help='Search an endpoint')
    __parser_endpoint_search.add_argument("-a", "--all", help="Include out of scope elements in search", action="store_true")
    __parser_endpoint_search.add_argument('field', help='Field to search in', choices_method=__get_search_fields_endpoint)
    __parser_endpoint_search.add_argument('val', help='Value to search')
    __parser_endpoint_del = __subparser_endpoint.add_parser("delete", help='Set target endpoint')
    __parser_endpoint_del.add_argument('endpoint', help='Endpoint', choices_method=__get_option_endpoint)

    __parser_endpoint_list.set_defaults(func=__endpoint_list)
    __parser_endpoint_add.set_defaults(func=__endpoint_add)
    __parser_endpoint_search.set_defaults(func=__endpoint_search)
    __parser_endpoint_del.set_defaults(func=__endpoint_del)

    @cmd2.with_argparser(__parser_endpoint)
    def do_endpoint(self, stmt):
        '''Manage endpoints'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__endpoint_list(stmt)

#################################################################
###################           USERS           ###################
#################################################################

    def __user_list(self, stmt):
        print("Current users in workspace:")
        show_all = getattr(stmt, 'all', False)
        users = self.workspace.get_objects(users=True, scope=None if show_all else True)
        if not users:
            print("No users in current workspace")
            return
        data = []
        for user in users:
            scope = "o" if user.scope else ""
            data.append([scope, user])
        print(tabulate.tabulate(data, headers=["", "Username"]))

    def __user_add(self, stmt):
        name = vars(stmt)['name']
        try:
            self.workspace.user_add(name)
        except Exception as e:
            print("User addition failed: "+str(e))
        else:
            print("User "+name+" added.")

    def __user_del(self, stmt):
        name = vars(stmt)['name']
        self.workspace.user_del(name)

    __parser_user = argparse.ArgumentParser(prog="user")
    __subparser_user = __parser_user.add_subparsers(title='Actions', help='Available actions')
    __parser_user_list = __subparser_user.add_parser("list", help='List users')
    __parser_user_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_user_add = __subparser_user.add_parser("add", help='Add a new user')
    __parser_user_add.add_argument('name', help='New user name')
    __parser_user_del = __subparser_user.add_parser("delete", help='Delete a user')
    __parser_user_del.add_argument('name', help='User name', choices_method=__get_option_user)

    __parser_user_list.set_defaults(func=__user_list)
    __parser_user_add.set_defaults(func=__user_add)
    __parser_user_del.set_defaults(func=__user_del)

    @cmd2.with_argparser(__parser_user)
    def do_user(self, stmt):
        '''Manage users'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__user_list(stmt)

#################################################################
###################           CREDS           ###################
#################################################################

    def __creds_types(self, stmt):
        print("Supported credential types:")
        data = []
        for key in Extensions.authMethodsAvail():
            data.append([key, Extensions.getAuthMethod(key).descr()])
        print(tabulate.tabulate(data, headers=["Key", "Description"]))

    def __creds_list(self, stmt):
        show_all = getattr(stmt, 'all', False)
        creds = self.workspace.get_objects(creds=True, scope=None if show_all else True)
        if not creds:
            print("No creds in current workspace")
            return
        data = []
        for cred in creds:
            scope = "o" if cred.scope else ""
            data.append([scope, "#"+str(cred.id), cred.obj.getKey(), cred.obj.toList()])
        print(tabulate.tabulate(data, headers=["", "ID", "Type", "Value"]))

    def __creds_show(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.creds_show(creds_id)

    def __creds_edit(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.creds_edit(creds_id)

    def __creds_del(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.creds_del(creds_id)

    def __creds_add(self, stmt):
        creds_type = vars(stmt)['type']
        try:
            creds_id = self.workspace.creds_add(creds_type, stmt)
        except Exception as e:
            print("Credentials addition failed: "+str(e))
        else:
            print("Credentials #"+str(creds_id)+" added.")

    __parser_creds = argparse.ArgumentParser(prog="creds")
    __subparser_creds = __parser_creds.add_subparsers(title='Actions', help='Available actions')
    __parser_creds_list = __subparser_creds.add_parser("list", help='List saved credentials')
    __parser_creds_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_creds_types = __subparser_creds.add_parser("types", help='List available credentials types')
    __parser_creds_show = __subparser_creds.add_parser("show", help='Show credentials details')
    __parser_creds_show.add_argument('id', help='Creds identifier', choices_method=__get_option_creds)
    __parser_creds_edit = __subparser_creds.add_parser("edit", help='Edit credentials details')
    __parser_creds_edit.add_argument('id', help='Creds identifier', choices_method=__get_option_creds)
    __parser_creds_add = __subparser_creds.add_parser("add", help='Add a new credentials')
    __subparser_creds_add = __parser_creds_add.add_subparsers(title='Add creds', help='Available creds types')
    for __methodName in Extensions.authMethodsAvail():
        __method = Extensions.getAuthMethod(__methodName)
        __parser_method = __subparser_creds_add.add_parser(__methodName, help=__method.descr())
        __parser_method.set_defaults(type=__methodName)
        __method.buildParser(__parser_method)
    __parser_creds_del = __subparser_creds.add_parser("delete", help='Delete credentials from workspace')
    __parser_creds_del.add_argument('id', help='Creds identifier', choices_method=__get_option_creds)

    __parser_creds_list.set_defaults(func=__creds_list)
    __parser_creds_types.set_defaults(func=__creds_types)
    __parser_creds_show.set_defaults(func=__creds_show)
    __parser_creds_edit.set_defaults(func=__creds_edit)
    __parser_creds_add.set_defaults(func=__creds_add)
    __parser_creds_del.set_defaults(func=__creds_del)

    @cmd2.with_argparser(__parser_creds)
    def do_creds(self, stmt):
        '''Manage credentials'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__creds_list(stmt)

#################################################################
###################          PAYLOADS         ###################
#################################################################

    def __payload_list(self, stmt):
        print("Available payloads:")
        data = []
        for key in Extensions.payloadsAvail():
            data.append([key, Extensions.getPayload(key).descr()])
        print(tabulate.tabulate(data, headers=["Key", "Description"]))

    __parser_payload = argparse.ArgumentParser(prog="payload")
    __subparser_payload = __parser_payload.add_subparsers(title='Actions', help='Available actions')
    __parser_payload_list = __subparser_payload.add_parser("list", help='List payloads')

    __parser_payload_list.set_defaults(func=__payload_list)

    @cmd2.with_argparser(__parser_payload)
    def do_payload(self, stmt):
        '''Manage payloads'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__payload_list(None)

#################################################################
###################        CONNECTIONS        ###################
#################################################################

    def __connection_list(self, stmt):
        print("Available connections:")
        show_all = getattr(stmt, 'all', False)
        connections = self.workspace.get_objects(connections=True, scope=None if show_all else True)
        if not connections:
            print("No connections in current workspace")
            return
        data = []
        for connection in connections:
            if not show_all:
                if not connection.scope:
                    continue
            data.append([connection.endpoint, connection.user, connection.creds])
        print(tabulate.tabulate(data, headers=["Endpoint", "User", "Creds"]))

    def __connection_del(self, stmt):
        connection = getattr(stmt, "connection", None)
        self.workspace.connection_del(connection)

    __parser_connection = argparse.ArgumentParser(prog="connection")
    __subparser_connection = __parser_connection.add_subparsers(title='Actions', help='Available actions')
    __parser_connection_list = __subparser_connection.add_parser("list", help='List connections')
    __parser_connection_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_connection_del = __subparser_connection.add_parser("delete", help='Delete connection')
    __parser_connection_del.add_argument('connection', help='Connection string', choices_method=__get_option_connection)

    __parser_connection_list.set_defaults(func=__connection_list)
    __parser_connection_del.set_defaults(func=__connection_del)

    @cmd2.with_argparser(__parser_connection)
    def do_connection(self, stmt):
        '''Manage connections'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__connection_list(stmt)


#################################################################
###################          OPTIONS          ###################
#################################################################

    def __options_list(self):
        print("Current options:")
        for key, val in self.workspace.options.items():
            print("    - "+key+": "+str(val))

    __parser_option = argparse.ArgumentParser(prog="option")
    __subparser_option = __parser_option.add_subparsers(title='Actions', help='Available actions')
    __parser_option_list = __subparser_option.add_parser("list", help='List options')
    __parser_option_user = __subparser_option.add_parser("user", help='Set target user')
    __parser_option_user.add_argument('username', help='User name', nargs="?", choices_method=__get_option_user)
    __parser_option_creds = __subparser_option.add_parser("creds", help='Set target creds')
    __parser_option_creds.add_argument('id', help='Creds ID', nargs="?", choices_method=__get_option_creds)
    __parser_option_endpoint = __subparser_option.add_parser("endpoint", help='Set target endpoint')
    __parser_option_endpoint.add_argument('endpoint', nargs="?", help='Endpoint', choices_method=__get_option_endpoint)
    __parser_option_payload = __subparser_option.add_parser("payload", help='Set target payload')
    __parser_option_payload.add_argument('payload', nargs="?", help='Payload name', choices_method=__get_option_payload)
    __parser_option_connection = __subparser_option.add_parser("connection", help='Set target connection')
    __parser_option_connection.add_argument('connection', nargs="?", help='Connection string', choices_method=__get_option_connection)
    __parser_option_params = __subparser_option.add_parser("params", help='Set payload params')
    __parser_option_params.add_argument('params', nargs="*", help='Payload params')

    __parser_option_list.set_defaults(option="list")
    __parser_option_user.set_defaults(option="user")
    __parser_option_creds.set_defaults(option="creds")
    __parser_option_endpoint.set_defaults(option="endpoint")
    __parser_option_payload.set_defaults(option="payload")
    __parser_option_connection.set_defaults(option="connection")
    __parser_option_params.set_defaults(option="params")

    @cmd2.with_argparser(__parser_option)
    def do_set(self, stmt):
        '''Manage options'''
        if 'option' not in vars(stmt):
            self.__options_list()
            return
        option = vars(stmt)['option']
        if option is not None:
            if option == "list":
                self.__options_list()
                return
            if option == "user":
                value = vars(stmt)['username']
            elif option == "creds":
                value = vars(stmt)['id']
            elif option == "endpoint":
                value = vars(stmt)['endpoint']
            elif option == "payload":
                value = vars(stmt)['payload']
            elif option == "connection":
                value = vars(stmt)['connection']
            elif option == "params":
                value = " ".join(vars(stmt)['params'])
            try:
                self.workspace.set_option(option, value)
            except:
                print("Invalid value for "+option)

        else:
            self.__options_list()

#################################################################
###################           PATHS           ###################
#################################################################

    def __path_list(self, stmt):
        print("Current paths in workspace:")
        show_all = getattr(stmt, 'all', False)
        paths = self.workspace.get_objects(paths=True)
        if not paths:
            print("No paths in current workspace")
            return
        data = []
        for path in paths:
            if not path.scope and not show_all:
                continue
            src = path.src
            if src is None:
                src = "Local"
            data.append([src, path.dst])
        print(tabulate.tabulate(data, headers=["Source", "Destination"]))

    def __path_get(self, stmt):
        endpoint = vars(stmt)['endpoint']
        as_ip = getattr(stmt, "numeric", False)
        self.workspace.path_find_existing(endpoint, as_ip)

    def __path_add(self, stmt):
        src = vars(stmt)['src']
        dst = vars(stmt)['dst']
        self.workspace.path_add(src, dst)

    def __path_del(self, stmt):
        src = vars(stmt)['src']
        dst = vars(stmt)['dst']
        self.workspace.path_del(src, dst)

    __parser_path = argparse.ArgumentParser(prog="path")
    __subparser_path = __parser_path.add_subparsers(title='Actions', help='Available actions')
    __parser_path_list = __subparser_path.add_parser("list", help='List paths')
    __parser_path_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_path_get = __subparser_path.add_parser("get", help='Get path to endpoint')
    __parser_path_get.add_argument("-n", "--numeric", help="Show Endpoint instead of Host", action="store_true")
    __parser_path_get.add_argument('endpoint', help='Endpoint', choices_method=__get_endpoint_or_host)
    __parser_path_add = __subparser_path.add_parser("add", help='Add path to endpoint')
    __parser_path_add.add_argument('src', help='Source host', choices_method=__get_host_or_local)
    __parser_path_add.add_argument('dst', help='Destination endpoint', choices_method=__get_option_endpoint)
    __parser_path_del = __subparser_path.add_parser("delete", help='Delete path to endpoint')
    __parser_path_del.add_argument('src', help='Source host', choices_method=__get_host_or_local)
    __parser_path_del.add_argument('dst', help='Destination endpoint', choices_method=__get_option_endpoint)

    __parser_path_list.set_defaults(func=__path_list)
    __parser_path_get.set_defaults(func=__path_get)
    __parser_path_add.set_defaults(func=__path_add)
    __parser_path_del.set_defaults(func=__path_del)

    @cmd2.with_argparser(__parser_path)
    def do_path(self, stmt):
        '''Manage paths'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__path_list(stmt)

#################################################################
###################           PROBE           ###################
#################################################################

    __parser_probe = argparse.ArgumentParser(prog="probe")
    __parser_probe.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_probe.add_argument("-f", "--force", help="probe only unprobed endpoints", action="store_true")
    __parser_probe.add_argument("-n", "--new", help="try finding new shorter path", action="store_true")
    __parser_probe.add_argument("-g", "--gateway", help="force specific gateway", choices_method=__get_option_gateway)
    __parser_probe.add_argument('target', help='Endpoint to probe', nargs="?", choices_method=__get_option_endpoint)

    @cmd2.with_argparser(__parser_probe)
    def do_probe(self, stmt):
        '''Try to reach an endpoint through pivoting, using an existing path or finding a new one'''
        target = getattr(stmt, 'target', None)
        verbose = getattr(stmt,'verbose',False)
        force = getattr(stmt,'force',False)
        new = getattr(stmt,'new',False)
        gateway = getattr(stmt, 'gateway', "auto")
        if gateway is None:
            gateway = "auto"

        endpoints = self.workspace.enum_targets(target, force=True).keys()
        if force:
            targets = endpoints
        else:
            targets = [endpoint for endpoint in endpoints if not endpoint.reachable]
        nb_targets = len(targets)
        if nb_targets > 1:
            if not yes_no("This will probe "+str(nb_targets)+" endpoints. Proceed ?", False):
                return

        self.workspace.probe(targets, gateway, verbose, new)

#################################################################
###################          CONNECT          ###################
#################################################################

    __parser_connect = argparse.ArgumentParser(prog="connect")
    __parser_connect.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_connect.add_argument("-f", "--force", help="force connection even if already existing", action="store_true")
    __parser_connect.add_argument("-g", "--gateway", help="force specific gateway", choices_method=__get_option_gateway)
    __parser_connect.add_argument("-p", "--probe", help="Automatically probe the endpoint if it wasn't yet, using gateway if specified", action="store_true")
    __parser_connect.add_argument('connection', help='Connection string', nargs="?", choices_method=__get_option_connection)

    @cmd2.with_argparser(__parser_connect)
    def do_connect(self, stmt):
        '''Try connection to endpoint and identify host'''
        connection = getattr(stmt, 'connection', None)
        verbose = vars(stmt)['verbose']
        force = getattr(stmt,'force',False)
        probe_auto = getattr(stmt, 'probe', False)
        gateway = getattr(stmt, 'gateway', "auto")
        if gateway is None:
            gateway = "auto"

        if probe_auto:
            force=True

        targets = [target for endpoint in self.workspace.enum_targets(connection, force=force).values() for target in endpoint]
        nb_targets = len(targets)
        if nb_targets > 1:
            if not yes_no("This will attempt up to "+str(nb_targets)+" connections. Proceed ?", False):
                return

        self.workspace.connect(targets, gateway, verbose, probe_auto)


    __parser_run = argparse.ArgumentParser(prog="run")
    __parser_run.add_argument('connection', help='Connection string', nargs="?", choices_method=__get_run_targets)
    __subparser_run = __parser_run.add_subparsers(title='Actions', help='Available actions')
    for __payloadName in Extensions.payloadsAvail():
        __payload = Extensions.getPayload(__payloadName)
        __parser_payload = __subparser_run.add_parser(__payloadName, help=__payload.descr())
        __parser_payload.set_defaults(type=__payloadName)
        __payload.buildParser(__parser_payload)

    @cmd2.with_argparser(__parser_run)
    def do_run(self, stmt):
        '''Run a payload on a connection'''
        connection = getattr(stmt, 'connection', None)
        payload = getattr(stmt, 'type', None)
        self._reset_completion_defaults()

        if payload is not None:
            payload = Extensions.getPayload(payload)
        else:
            payload = self.workspace.options["payload"]

        if payload is None:
            print("Error : No payload specified")
            return

        params = self.workspace.options["params"]
        __parser = argparse.ArgumentParser(description='Params __parser')
        payload.buildParser(__parser)
        if params is None:
            params = ""
        stmt, junk = __parser.parse_known_args(params.split())

        targets = [target for endpoint in self.workspace.enum_targets(connection, working=True).values() for target in endpoint]
        nb_targets = len(targets)
        if nb_targets > 1:
            if not yes_no("This will attempt up to "+str(nb_targets)+" connections. Proceed ?", False):
                return

        self.workspace.run(targets, payload, stmt)

#################################################################
###################          TUNNELS          ###################
#################################################################

    def __tunnel_list(self, stmt):
        print("Current tunnels in workspace:")
        tunnels = self.workspace.tunnels.values()
        if not tunnels:
            print("No tunnels in current workspace")
            return
        data = []
        for tunnel in tunnels:
            data.append([tunnel.port, tunnel.connection])
        print(tabulate.tabulate(data, headers=["Local port", "Destination"]))

    def __tunnel_open(self, stmt):
        connection_str = getattr(stmt, 'connection', None)
        port = getattr(stmt, 'port', None)
        self.workspace.tunnel_open(connection_str, port)

    def __tunnel_close(self, stmt):
        port = getattr(stmt, 'port', None)
        self.workspace.tunnel_close(port)

    __parser_tunnel = argparse.ArgumentParser(prog="tunnel")
    __subparser_tunnel = __parser_tunnel.add_subparsers(title='Actions', help='Available actions')
    __parser_tunnel_list = __subparser_tunnel.add_parser("list", help='List tunnels')
    __parser_tunnel_open = __subparser_tunnel.add_parser("open", help='Open tunnel')
    __parser_tunnel_open.add_argument('connection', help='Connection string', choices_method=__get_option_connection)
    __parser_tunnel_open.add_argument('port', help='Tunnel entry port', type=int, nargs='?')
    __parser_tunnel_close = __subparser_tunnel.add_parser("close", help='Close tunnel')
    __parser_tunnel_close.add_argument('port', help='Tunnel entry port', type=int, choices_method=__get_open_tunnels)

    __parser_tunnel_list.set_defaults(func=__tunnel_list)
    __parser_tunnel_open.set_defaults(func=__tunnel_open)
    __parser_tunnel_close.set_defaults(func=__tunnel_close)

    @cmd2.with_argparser(__parser_tunnel)
    def do_tunnel(self, stmt):
        '''Manage tunnels'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__tunnel_list(None)

#################################################################
###################          EXPORTS          ###################
#################################################################


    __parser_export = argparse.ArgumentParser(prog="export")
    __subparser_export = __parser_export.add_subparsers(title='Actions', help='Available exporters')
    __parser_method = __subparser_export.add_parser('list', help='List available exporters')
    for __key in Extensions.exportsAvail():
        __export = Extensions.getExport(__key)
        __parser_method = __subparser_export.add_parser(__key, help=__export.descr())
        __parser_method.set_defaults(exporter=__key)
        __export.buildParser(__parser_method)

    @cmd2.with_argparser(__parser_export)
    def do_export(self, stmt):
        '''Export workspace info'''
        key = getattr(stmt, 'exporter', 'list')
        if key == 'list':
            print("Available exporters:")
            data = []
            for key in Extensions.exportsAvail():
                data.append([key, Extensions.getExport(key).descr()])
            print(tabulate.tabulate(data, headers=["Key", "Description"]))
            return
        try:
            exporter = Extensions.getExport(key)
        except Exception as e:
            print("Error: "+str(e))
            return
        exporter.run(stmt, self.workspace)

#################################################################
###################          IMPORTS          ###################
#################################################################

    __parser_import = argparse.ArgumentParser(prog="import")
    __subparser_import = __parser_import.add_subparsers(title='Actions', help='Available importers')
    __parser_method = __subparser_import.add_parser('list', help='List available importers')
    for __key in Extensions.importsAvail():
        __importer = Extensions.getImport(__key)
        __parser_method = __subparser_import.add_parser(__key, help=__importer.descr())
        __parser_method.set_defaults(importer=__key)
        __importer.buildParser(__parser_method)

    @cmd2.with_argparser(__parser_import)
    def do_import(self, stmt):
        '''Import workspace info'''
        key = getattr(stmt, 'importer', 'list')
        if key == 'list':
            print("Available importers:")
            data = []
            for key in Extensions.importsAvail():
                data.append([key, Extensions.getImport(key).descr()])
            print(tabulate.tabulate(data, headers=["Key", "Description"]))
            return
        try:
            importer = Extensions.getImport(key)
        except Exception as e:
            print("Error: "+str(e))
            return
        importer.run(stmt, self.workspace)

#################################################################
###################           SCOPE           ###################
#################################################################

    def __get_all_objects(self):
        return self.workspace.get_objects(endpoints=True, creds=True, users=True, hosts=True)

    __parser_scope = argparse.ArgumentParser(prog="scope")
    __parser_scope.add_argument('target', help='Object to scope', choices_method=__get_all_objects)
    @cmd2.with_argparser(__parser_scope)
    def do_scope(self, stmt):
        '''Toggle object in/out of scope'''
        key = getattr(stmt, 'target', None)
        self.workspace.scope(key)

#################################################################
###################            CMD            ###################
#################################################################

    def do_store(self, arg):
        for obj_type, objects in self.workspace.store.items():
            print(obj_type)
            for obj_id,obj in objects.items():
                print('\t'+str(obj)+' > '+str(obj_id))



    def do_exit(self, arg):
        'Close active workspace & quit Baboossh'

        self.workspace.close()
        print("Bye !")
        return True

    def __init_prompt(self):
        'Build prompt to output currect workspace & active options'

        new_prompt = "\033[1;33m"
        new_prompt = new_prompt+"["+self.workspace.name+"]\033[1;34m"
        user = self.workspace.options["user"]
        creds = self.workspace.options["creds"]
        endpoint = self.workspace.options["endpoint"]
        payload = self.workspace.options["payload"]
        if user or endpoint or creds:
            if user:
                new_prompt = new_prompt+str(user)
            else:
                new_prompt = new_prompt+"*"
            new_prompt = new_prompt+":"
            if creds:
                new_prompt = new_prompt+str(creds)
            else:
                new_prompt = new_prompt+"*"
            new_prompt = new_prompt+"@"
            if endpoint:
                new_prompt = new_prompt+str(endpoint)
            else:
                new_prompt = new_prompt+"*"
        if payload:
            new_prompt = new_prompt+"\033[1;31m("+str(payload)+")\033[0m"
        self.prompt = new_prompt+"\033[1;33m>\033[0m "

    def emptyline(self):
        'Don\'t output empty line after command'


    def postcmd(self, stop, line):
        'Refresh promt after each command to reflect parameters changes'

        self.__init_prompt()
        return stop


    def __init__(self):
        'Init BabooSSH shell & cmd2.Cmd, create (if needed) & open default workspace.'

        super().__init__()

        if not os.path.exists(workspacesDir):
            print("> First run ? Creating workspaces directory")
            os.makedirs(workspacesDir)
        #Create default workspace if not exists
        if not os.path.exists(os.path.join(workspacesDir, 'default')):
            Workspace.create('default')

        self.intro = '''  %%%%%/      %%%     %%%%%.      .%%/     %%     %/   /%%%/   ,%%%/  *%%    %%
  %%   %%*   %% %%    %%   %%  %*       % %    /@*  % %%      %%      *%%    %% 
  %%%%%%    %%, %%%   %%%%%%  %    @@@@  %    /@@@  /  %%%%    %%%%   *%%%%%%%% 
  %%   %%% %%%%%%%%,  %%   %%(%          %%         %     %%%     %%% *%%    %% 
  %%%%%%  ,%%     %%  %%%%%%   %%      ,%   %#   %%   %%%%%.  %%%%%.  *%%    %%

Welcome to BabooSSH. Type help or ? to list commands.'''

        self.workspace = Workspace("default")
        self.__init_prompt()
        #Removes cmd2 default commands
        self.disable_command("run_pyscript", "disabled")
        self.disable_command("run_script", "disabled")
        self.disable_command("alias", "disabled")
        self.disable_command("edit", "disabled")
        self.disable_command("quit", "disabled")
        self.disable_command("macro", "disabled")
        self.disable_command("shortcuts", "disabled")
        self.quit_on_sigint = False
        #TODO remove debug
        self.debug = True
