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
from baboossh.utils import WORKSPACES_DIR, BABOOSSH_VERSION
from baboossh.extensions import Extensions
from baboossh.workspace import Workspace

def yes_no(prompt, default=None, list_val=None):
    """Simple Yes/No prompt to ask questions

    Args:
        prompt (str): The question to ask
        default (bool): The default answer
        list_val ([]): A list of values to output with "l" key

    Returns:
        A `bool` with `True` for yes else `False`
    """
    if list_val is None:
        if default is None:
            choices = "[y, n]"
        elif default:
            choices = "[Y, n]"
        else:
            choices = "[y, N]"
    else:
        if default is None:
            choices = "[y, n, l, ?]"
        elif default:
            choices = "[Y, n, l, ?]"
        else:
            choices = "[y, N, l, ?]"
    answer = ""
    while answer not in ["y", "n"]:
        answer = input(prompt+" "+choices+" ").lower()
        if answer == "?":
            print(" y => Yes")
            print(" n => No")
            print(" l => List values")
            print(" ? => Show help")
        elif list_val is not None and answer == "l":
            for elt in list_val:
                print(" "+str(elt))
        elif answer == "" and default is not None:
            answer = "y" if default else "n"
    return answer == "y"


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

    __CMD_CAT_OBJ = "Object management"
    __CMD_CAT_CON = "Connecting hosts"
    __CMD_CAT_WSP = "Workspace management"


#################################################################
###################          GETTERS          ###################
#################################################################

    def __get_option_creds(self):
        return [cmd2.CompletionItem("#"+str(creds.id), creds.obj.toList()) for creds in self.workspace.get_objects(creds=True, scope=True)]

    def __get_option_host(self):
        return [cmd2.CompletionItem(str(host.name), "; ".join(str(e) for e in host.endpoints)) for host in self.workspace.get_objects(hosts=True, scope=True)]

    def __get_arg_workspaces(self):
        return [name for name in os.listdir(WORKSPACES_DIR) if os.path.isdir(os.path.join(WORKSPACES_DIR, name))]

    def __get_option_gateway(self):
        return self.__get_host_or_local()

    def __get_option_user(self):
        return [cmd2.CompletionItem(str(user), str(user)) for user in self.workspace.get_objects(users=True, scope=True)]

    def __get_option_endpoint(self):
        return [cmd2.CompletionItem(str(endpoint), "" if endpoint.host == None else str(endpoint.host)) for endpoint in self.workspace.get_objects(endpoints=True, scope=True)]

    def __get_option_endpoint_tag(self):
        endpoints = [cmd2.CompletionItem(str(endpoint), "" if endpoint.host == None else str(endpoint.host)) for endpoint in self.workspace.get_objects(endpoints=True, scope=True)]
        tags = [cmd2.CompletionItem("!"+str(tag.name), "; ".join(str(e) for e in tag.endpoints)) for tag in self.workspace.get_objects(tags=True, scope=True)]
        return endpoints+tags

    def __get_option_payload(self):
        return Extensions.payloads.keys()

    def __get_option_connection(self):
        return [cmd2.CompletionItem(str(connection), "" if connection.endpoint.host == None else str(connection.endpoint.host)) for connection in self.workspace.get_objects(connections=True, scope=True)]

    def __get_search_fields_endpoint(self):
        return self.workspace.search_fields("Endpoint")

    def __get_search_fields_host(self):
        return self.workspace.search_fields("Host")

    def __get_open_tunnels(self):
        #TODO
        return self.workspace.get_objects(tunnels=True)

    def __get_run_targets(self):
        return self.__get_option_connection() + self.__get_option_host() + self.__get_option_endpoint()

    def __get_host_or_local(self):
        items = [cmd2.CompletionItem("local","BabooSSH host")]
        return items+[cmd2.CompletionItem(str(host.name), "; ".join(str(e) for e in host.endpoints)) for host in self.workspace.get_objects(hosts=True, scope=True)]

    def __get_endpoint_or_host(self):
        return self.__get_option_host() + self.__get_option_endpoint()

    def __get_tag(self):
        return [cmd2.CompletionItem(str(tag.name), "; ".join(str(e) for e in tag.endpoints)) for tag in self.workspace.get_objects(tags=True, scope=True)]

#################################################################
###################         WORKSPACE         ###################
#################################################################

    def __workspace_list(self, stmt):
        print("Existing workspaces :")
        workspaces = [name for name in os.listdir(WORKSPACES_DIR) if os.path.isdir(os.path.join(WORKSPACES_DIR, name))]
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
        if os.path.exists(os.path.join(WORKSPACES_DIR, name)):
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
        if not os.path.exists(os.path.join(WORKSPACES_DIR, name)):
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
        if not os.path.exists(os.path.join(WORKSPACES_DIR, name)):
            print("Workspace does not exist")
            return
        if self.workspace.name == name:
            print("Cannot delete current workspace, please change workspace first.")
            return
        if not yes_no("Are you sure you want to delete workspace "+name+"?", default=False):
            return
        shutil.rmtree(os.path.join(WORKSPACES_DIR, name))
        print("Workspace deleted !")

    __parser_wspace = argparse.ArgumentParser(prog="workspace")
    __subparser_wspace = __parser_wspace.add_subparsers(title='Actions', help='Available actions')
    __parser_wspace_list = __subparser_wspace.add_parser("list", help='List workspaces')
    __parser_wspace_add = __subparser_wspace.add_parser("add", help='Add a new workspace')
    __parser_wspace_add.add_argument('name', help='New workspace name')
    __parser_wspace_use = __subparser_wspace.add_parser("use", help='Change current workspace')
    __parser_wspace_use.add_argument('name', help='Name of workspace to use', choices_provider=__get_arg_workspaces)
    __parser_wspace_del = __subparser_wspace.add_parser("delete", help='Delete workspace')
    __parser_wspace_del.add_argument('name', help='Name of workspace to delete', choices_provider=__get_arg_workspaces)

    __parser_wspace_list.set_defaults(func=__workspace_list)
    __parser_wspace_add.set_defaults(func=__workspace_add)
    __parser_wspace_use.set_defaults(func=__workspace_use)
    __parser_wspace_del.set_defaults(func=__workspace_del)

    @cmd2.with_argparser(__parser_wspace)
    @cmd2.with_category(__CMD_CAT_WSP)
    def do_workspace(self, stmt: argparse.Namespace):
        '''Create, list, delete and use workspaces.

        Each workspace is a container for every object available in BabooSSH.
        Having several workspaces allows you to segregate various environments,
        keeping your findings and your loot organised.

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
            data.append([scope, host.name, host.distance, endpoints])
        print(tabulate.tabulate(data, headers=["", "Name", "Dist", "Endpoints"]))

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
        tag = getattr(stmt, 'tag', None)
        field = vars(stmt)['field']
        allowed_fields = self.__get_search_fields_host()
        if field not in allowed_fields:
            print("Invalid field specified, use one of "+str(allowed_fields)+".")
            return
        val = vars(stmt)['val']
        hosts = self.workspace.host_search(field, val, show_all, add_tag=tag)
        print("Search result for hosts:")
        if not hosts:
            print("No results")
            return
        self.__host_print(hosts)

    def __host_del(self, stmt):
        host = getattr(stmt, 'host', None)
        self.workspace.host_del(host)

    def __host_tag(self, stmt):
        host = vars(stmt)['host']
        tagname = vars(stmt)['tagname']
        self.workspace.host_tag(host, tagname)

    def __host_untag(self, stmt):
        host = vars(stmt)['host']
        tagname = vars(stmt)['tagname']
        self.workspace.host_untag(host, tagname)

    __parser_host = argparse.ArgumentParser(prog="host")
    __subparser_host = __parser_host.add_subparsers(title='Actions', help='Available actions')
    __parser_host_list = __subparser_host.add_parser("list", help='List hosts')
    __parser_host_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_host_search = __subparser_host.add_parser("search", help='Search a host')
    __parser_host_search.add_argument('field', help='Field to search in', choices_provider=__get_search_fields_host)
    __parser_host_search.add_argument('val', help='Value to search')
    __parser_host_search.add_argument("-t", "--tag", help="Add tag to search results", choices_provider=__get_tag)
    __parser_host_del = __subparser_host.add_parser("delete", help='Delete host')
    __parser_host_del.add_argument('host', help='Host name', choices_provider=__get_option_host)
    __parser_host_tag = __subparser_host.add_parser("tag", help='Tag an host')
    __parser_host_tag.add_argument('host', help='Host', choices_provider=__get_option_host)
    __parser_host_tag.add_argument('tagname', help='The tag name to add', choices_provider=__get_tag)
    __parser_host_untag = __subparser_host.add_parser("untag", help='Tag an host')
    __parser_host_untag.add_argument('host', help='Host', choices_provider=__get_option_host)
    __parser_host_untag.add_argument('tagname', help='The tag name to add', choices_provider=__get_tag)

    __parser_host_list.set_defaults(func=__host_list)
    __parser_host_search.set_defaults(func=__host_search)
    __parser_host_del.set_defaults(func=__host_del)
    __parser_host_tag.set_defaults(func=__host_tag)
    __parser_host_untag.set_defaults(func=__host_untag)

    @cmd2.with_argparser(__parser_host)
    @cmd2.with_category(__CMD_CAT_OBJ)
    def do_host(self, stmt):
        '''Search, list and delete hosts.

        You can list or delete hosts, and use them as pivots to force using a
        specific path. Host addition is performed automatically when you
        successfully connect to an endpoint for the first time.
        '''
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
            first = True
            taglist = ""
            for tag in endpoint.tags:
                taglist = taglist + ("!"+tag if first else ", !"+tag)
                first = False

            data.append([scope, endpoint, host, reachable, distance, conn, taglist])
        print(tabulate.tabulate(data, headers=["", "Endpoint", "Host", "Reachable", "Dist", "Working connection", "Tags"]))

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
        except Exception as exc:
            print("Endpoint addition failed: "+str(exc))
        else:
            print("Endpoint "+ip_add+":"+port+" added.")

    def __endpoint_del(self, stmt):
        endpoint = vars(stmt)['endpoint']
        self.workspace.endpoint_del(endpoint)

    def __endpoint_tag(self, stmt):
        endpoint = vars(stmt)['endpoint']
        tagname = vars(stmt)['tagname']
        self.workspace.endpoint_tag(endpoint, tagname)

    def __endpoint_untag(self, stmt):
        endpoint = vars(stmt)['endpoint']
        tagname = vars(stmt)['tagname']
        self.workspace.endpoint_untag(endpoint, tagname)


    def __endpoint_search(self, stmt):
        show_all = getattr(stmt, 'all', False)
        tag = getattr(stmt, 'tag', None)
        field = vars(stmt)['field']
        allowed_fields = self.__get_search_fields_endpoint()
        if field not in allowed_fields:
            print("Invalid field specified, use one of "+str(allowed_fields)+".")
            return
        val = vars(stmt)['val']
        endpoints = self.workspace.endpoint_search(field, val, show_all, add_tag=tag)
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
    __parser_endpoint_search.add_argument('field', help='Field to search in', choices_provider=__get_search_fields_endpoint)
    __parser_endpoint_search.add_argument('val', help='Value to search')
    __parser_endpoint_search.add_argument("-t", "--tag", help="Add tag to search results", choices_provider=__get_tag)
    __parser_endpoint_del = __subparser_endpoint.add_parser("delete", help='Set target endpoint')
    __parser_endpoint_del.add_argument('endpoint', help='Endpoint', choices_provider=__get_option_endpoint_tag)
    __parser_endpoint_tag = __subparser_endpoint.add_parser("tag", help='Tag an endpoint')
    __parser_endpoint_tag.add_argument('endpoint', help='Endpoint', choices_provider=__get_option_endpoint)
    __parser_endpoint_tag.add_argument('tagname', help='The tag name to add', choices_provider=__get_tag)
    __parser_endpoint_untag = __subparser_endpoint.add_parser("untag", help='Tag an endpoint')
    __parser_endpoint_untag.add_argument('endpoint', help='Endpoint', choices_provider=__get_option_endpoint)
    __parser_endpoint_untag.add_argument('tagname', help='The tag name to add', choices_provider=__get_tag)

    __parser_endpoint_list.set_defaults(func=__endpoint_list)
    __parser_endpoint_add.set_defaults(func=__endpoint_add)
    __parser_endpoint_search.set_defaults(func=__endpoint_search)
    __parser_endpoint_del.set_defaults(func=__endpoint_del)
    __parser_endpoint_tag.set_defaults(func=__endpoint_tag)
    __parser_endpoint_untag.set_defaults(func=__endpoint_untag)

    @cmd2.with_argparser(__parser_endpoint)
    @cmd2.with_category(__CMD_CAT_OBJ)
    def do_endpoint(self, stmt):
        '''Create, list, search and delete endpoints.

        An endpoint is a couple of an IP and a port on which a SSH service
        should be running. Once added, an endpoint must be reached using "probe"
        and then connected using "connect".
        '''
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
        except Exception as exc:
            print("User addition failed: "+str(exc))
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
    __parser_user_del.add_argument('name', help='User name', choices_provider=__get_option_user)

    __parser_user_list.set_defaults(func=__user_list)
    __parser_user_add.set_defaults(func=__user_add)
    __parser_user_del.set_defaults(func=__user_del)

    @cmd2.with_argparser(__parser_user)
    @cmd2.with_category(__CMD_CAT_OBJ)
    def do_user(self, stmt):
        '''Create, list and delete users.

        A user is a username used to authenticate on an endpoint. Once a user
        is added to the workspace, it can be used with "set" and "connect".
        '''
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
        for key in Extensions.auths:
            data.append([key, Extensions.auths[key].descr()])
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
        except Exception as exc:
            print("Credentials addition failed: "+str(exc))
        else:
            print("Credentials #"+str(creds_id)+" added.")

    __parser_creds = argparse.ArgumentParser(prog="creds")
    __subparser_creds = __parser_creds.add_subparsers(title='Actions', help='Available actions')
    __parser_creds_list = __subparser_creds.add_parser("list", help='List saved credentials')
    __parser_creds_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_creds_types = __subparser_creds.add_parser("types", help='List available credentials types')
    __parser_creds_show = __subparser_creds.add_parser("show", help='Show credentials details')
    __parser_creds_show.add_argument('id', help='Creds identifier', choices_provider=__get_option_creds)
    __parser_creds_edit = __subparser_creds.add_parser("edit", help='Edit credentials details')
    __parser_creds_edit.add_argument('id', help='Creds identifier', choices_provider=__get_option_creds)
    __parser_creds_add = __subparser_creds.add_parser("add", help='Add new credentials')
    __subparser_creds_add = __parser_creds_add.add_subparsers(title='Add creds', help='Available creds types')
    for __methodName in Extensions.auths:
        __method = Extensions.auths[__methodName]
        __parser_method = __subparser_creds_add.add_parser(__methodName, help=__method.descr())
        __parser_method.set_defaults(type=__methodName)
        __method.buildParser(__parser_method)
    __parser_creds_del = __subparser_creds.add_parser("delete", help='Delete credentials from workspace')
    __parser_creds_del.add_argument('id', help='Creds identifier', choices_provider=__get_option_creds)

    __parser_creds_list.set_defaults(func=__creds_list)
    __parser_creds_types.set_defaults(func=__creds_types)
    __parser_creds_show.set_defaults(func=__creds_show)
    __parser_creds_edit.set_defaults(func=__creds_edit)
    __parser_creds_add.set_defaults(func=__creds_add)
    __parser_creds_del.set_defaults(func=__creds_del)

    @cmd2.with_argparser(__parser_creds)
    @cmd2.with_category(__CMD_CAT_OBJ)
    def do_creds(self, stmt):
        '''Create, list, edit and delete credentials.

        Credentials are secrets used to authenticate. They can be of different
        types (see "creds types" to list supported types) and are used with "set"
        and "connect".

        The creds object provides a unified interface for the underlying types.
        '''
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
        for key in Extensions.payloads:
            data.append([key, Extensions.payloads[key].descr()])
        print(tabulate.tabulate(data, headers=["Key", "Description"]))

    __parser_payload = argparse.ArgumentParser(prog="payload")
    __subparser_payload = __parser_payload.add_subparsers(title='Actions', help='Available actions')
    __parser_payload_list = __subparser_payload.add_parser("list", help='List payloads')

    __parser_payload_list.set_defaults(func=__payload_list)

    @cmd2.with_argparser(__parser_payload)
    @cmd2.with_category(__CMD_CAT_WSP)
    def do_payload(self, stmt):
        '''List available payloads'''
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
            return True
        data = []
        for connection in connections:
            if not show_all:
                if not connection.scope:
                    continue
            data.append([connection.endpoint, connection.user, connection.creds, "o" if connection.conn is not None else ""])
        print(tabulate.tabulate(data, headers=["Endpoint", "User", "Creds", "Open"]))
        return True

    def __connection_close(self, stmt):
        connection = getattr(stmt, "connection", None)
        return self.workspace.connection_close(connection)


    def __connection_del(self, stmt):
        connection = getattr(stmt, "connection", None)
        return self.workspace.connection_del(connection)

    __parser_connection = argparse.ArgumentParser(prog="connection")
    __subparser_connection = __parser_connection.add_subparsers(title='Actions', help='Available actions')
    __parser_connection_list = __subparser_connection.add_parser("list", help='List connections')
    __parser_connection_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_connection_close = __subparser_connection.add_parser("close", help='Close connection')
    __parser_connection_close.add_argument('connection', help='Connection string', nargs="?", choices_provider=__get_option_connection)
    __parser_connection_del = __subparser_connection.add_parser("delete", help='Delete connection')
    __parser_connection_del.add_argument('connection', help='Connection string', choices_provider=__get_option_connection)

    __parser_connection_list.set_defaults(func=__connection_list)
    __parser_connection_close.set_defaults(func=__connection_close)
    __parser_connection_del.set_defaults(func=__connection_del)

    @cmd2.with_argparser(__parser_connection)
    @cmd2.with_category(__CMD_CAT_OBJ)
    def do_connection(self, stmt):
        '''List and delete working connections.

        A connection object is saved whenever a user and a creds object work on
        an endpoint, as tested by the "connect" command. Once the object is
        created, it can be used with "set" and "run" to run payloads.
        '''
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
    __parser_option_user.add_argument('username', help='User name', nargs="?", choices_provider=__get_option_user)
    __parser_option_creds = __subparser_option.add_parser("creds", help='Set target creds')
    __parser_option_creds.add_argument('id', help='Creds ID', nargs="?", choices_provider=__get_option_creds)
    __parser_option_endpoint = __subparser_option.add_parser("endpoint", help='Set target endpoint')
    __parser_option_endpoint.add_argument('endpoint', nargs="?", help='Endpoint', choices_provider=__get_option_endpoint_tag)
    __parser_option_payload = __subparser_option.add_parser("payload", help='Set target payload')
    __parser_option_payload.add_argument('payload', nargs="?", help='Payload name', choices_provider=__get_option_payload)
    __parser_option_connection = __subparser_option.add_parser("connection", help='Set target connection')
    __parser_option_connection.add_argument('connection', nargs="?", help='Connection string', choices_provider=__get_option_connection)
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
    @cmd2.with_category(__CMD_CAT_WSP)
    def do_set(self, stmt):
        '''Set the workspace active options.

        Once set, the options will be used when running "probe", "connect" and
        "run" without parameters to define which connections to target and
        which payload to run with which options.
        '''
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
###################           TAGS            ###################
#################################################################

    def __tag_list(self, stmt):
        print("Current tags in workspace:")
        tags = self.workspace.get_objects(tags=True)
        if not tags:
            print("No tags in current workspace")
            return
        data = []
        for tag in tags:
            data.append([tag])
        print(tabulate.tabulate(data, headers=["Tag name"]))

    def __tag_show(self, stmt):
        name = vars(stmt)['tagname']
        self.workspace.tag_show(name)

    def __tag_del(self, stmt):
        name = vars(stmt)['tagname']
        self.workspace.tag_del(name)

    __parser_tag = argparse.ArgumentParser(prog="tag")
    __subparser_tag = __parser_tag.add_subparsers(title='Actions', help='Available actions')
    __parser_tag_list = __subparser_tag.add_parser("list", help='List tags')
    __parser_tag_show = __subparser_tag.add_parser("show", help='Show endpoints with tag')
    __parser_tag_show.add_argument('tagname', help='Tag name', choices_provider=__get_tag)
    __parser_tag_del = __subparser_tag.add_parser("delete", help='Delete tag')
    __parser_tag_del.add_argument('tagname', help='Tag name', choices_provider=__get_tag)

    __parser_tag_list.set_defaults(func=__tag_list)
    __parser_tag_show.set_defaults(func=__tag_show)
    __parser_tag_del.set_defaults(func=__tag_del)

    @cmd2.with_argparser(__parser_tag)
    @cmd2.with_category(__CMD_CAT_OBJ)
    def do_tag(self, stmt):
        '''Manage tags'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__tag_list(stmt)


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
    __parser_path_get.add_argument('endpoint', help='Endpoint', choices_provider=__get_endpoint_or_host)
    __parser_path_add = __subparser_path.add_parser("add", help='Add path to endpoint')
    __parser_path_add.add_argument('src', help='Source host', choices_provider=__get_host_or_local)
    __parser_path_add.add_argument('dst', help='Destination endpoint', choices_provider=__get_option_endpoint)
    __parser_path_del = __subparser_path.add_parser("delete", help='Delete path to endpoint')
    __parser_path_del.add_argument('src', help='Source host', choices_provider=__get_host_or_local)
    __parser_path_del.add_argument('dst', help='Destination endpoint', choices_provider=__get_option_endpoint)

    __parser_path_list.set_defaults(func=__path_list)
    __parser_path_get.set_defaults(func=__path_get)
    __parser_path_add.set_defaults(func=__path_add)
    __parser_path_del.set_defaults(func=__path_del)

    @cmd2.with_argparser(__parser_path)
    @cmd2.with_category(__CMD_CAT_OBJ)
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
    __parser_probe.add_argument("-a", "--again", help="include already probed endpoints", action="store_true")
    __parser_probe.add_argument("-n", "--new", help="try finding new shorter path", action="store_true")
    __parser_probe.add_argument("-g", "--gateway", help="force specific gateway", choices_provider=__get_option_gateway)
    __parser_probe.add_argument('target', help='Endpoint to probe', nargs="?", choices_provider=__get_option_endpoint_tag)

    @cmd2.with_argparser(__parser_probe)
    @cmd2.with_category(__CMD_CAT_CON)
    def do_probe(self, stmt):
        '''Try to reach an endpoint through pivoting, using an existing path or finding a new one'''
        target = getattr(stmt, 'target', None)
        verbose = getattr(stmt, 'verbose', False)
        again = getattr(stmt, 'again', False)
        new = getattr(stmt, 'new', False)
        gateway = getattr(stmt, 'gateway', "auto")
        if gateway is None:
            gateway = "auto"

        if new and gateway != "auto":
            print("Error: You cannot use both --new and --gateway options.")
            return

        targets = self.workspace.enum_probe(target, again)
        nb_targets = len(targets)
        if nb_targets > 1:
            if not yes_no("This will probe "+str(nb_targets)+" endpoints. Proceed ?", False, list_val=targets):
                return

        self.workspace.probe(targets, gateway, verbose, find_new=new)

#################################################################
###################          CONNECT          ###################
#################################################################

    __parser_connect = argparse.ArgumentParser(prog="connect")
    __parser_connect.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_connect.add_argument("-f", "--force", help="force connection even if already existing", action="store_true")
    __parser_connect.add_argument("-p", "--probe", help="Automatically probe the endpoint if it wasn't yet", action="store_true")
    __parser_connect.add_argument('connection', help='Connection string', nargs="?", choices_provider=__get_option_connection)

    @cmd2.with_argparser(__parser_connect)
    @cmd2.with_category(__CMD_CAT_CON)
    def do_connect(self, stmt):
        '''Try to authenticate on an Enpoint using a User and Creds'''
        connection = getattr(stmt, 'connection', None)
        verbose = getattr(stmt, 'verbose', False)
        force = getattr(stmt, 'force', False)
        probe_auto = getattr(stmt, 'probe', False)

        targets = self.workspace.enum_connect(connection, force=force, unprobed=probe_auto)
        nb_targets = len(targets)
        if nb_targets > 1:
            if not yes_no("This will attempt up to "+str(nb_targets)+" connections. Proceed ?", False, list_val=targets):
                return
        
        nb_working = self.workspace.connect(targets, verbose, probe_auto)
        print("\033[1;32m"+str(nb_working)+"/"+str(nb_targets)+"\033[0m working.")


    __parser_run = argparse.ArgumentParser(prog="run")
    __parser_run.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_run.add_argument('connection', help='Connection string', nargs="?", choices_provider=__get_run_targets)
    __subparser_run = __parser_run.add_subparsers(title='Actions', help='Available actions')
    for __payloadName in Extensions.payloads:
        __payload = Extensions.payloads[__payloadName]
        __parser_payload = __subparser_run.add_parser(__payloadName, help=__payload.descr())
        __parser_payload.set_defaults(type=__payloadName)
        __payload.buildParser(__parser_payload)

    @cmd2.with_argparser(__parser_run)
    @cmd2.with_category(__CMD_CAT_CON)
    def do_run(self, stmt):
        '''Run a payload on a connection'''
        connection = getattr(stmt, 'connection', None)
        payload = getattr(stmt, 'type', None)
        verbose = getattr(stmt, 'verbose', False)
        self._reset_completion_defaults()

        if payload is not None:
            payload = Extensions.payloads[payload]
        else:
            payload = self.workspace.options["payload"]
            params = self.workspace.options["params"]
            __parser = argparse.ArgumentParser(description='Params __parser')
            payload.buildParser(__parser)
            if params is None:
                params = ""
            stmt, junk = __parser.parse_known_args(params.split())

        if payload is None:
            print("Error : No payload specified")
            return

        targets = self.workspace.enum_run(connection)
        nb_targets = len(targets)
        if nb_targets == 0:
            print("No valid targets found.")
            return
        if nb_targets > 1:
            if not yes_no("The payload will be run on "+str(nb_targets)+" connections. Proceed ?", False, list_val=targets):
                return

        self.workspace.run(targets, payload, stmt, verbose=verbose)

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
    __parser_tunnel_open.add_argument('connection', help='Connection string', choices_provider=__get_option_connection)
    __parser_tunnel_open.add_argument('port', help='Tunnel entry port', type=int, nargs='?')
    __parser_tunnel_close = __subparser_tunnel.add_parser("close", help='Close tunnel')
    __parser_tunnel_close.add_argument('port', help='Tunnel entry port', type=int, choices_provider=__get_open_tunnels)

    __parser_tunnel_list.set_defaults(func=__tunnel_list)
    __parser_tunnel_open.set_defaults(func=__tunnel_open)
    __parser_tunnel_close.set_defaults(func=__tunnel_close)

    @cmd2.with_argparser(__parser_tunnel)
    @cmd2.with_category(__CMD_CAT_CON)
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
    for __key in Extensions.exports:
        __export = Extensions.exports[__key]
        __parser_method = __subparser_export.add_parser(__key, help=__export.descr())
        __parser_method.set_defaults(exporter=__key)
        __export.buildParser(__parser_method)

    @cmd2.with_argparser(__parser_export)
    @cmd2.with_category(__CMD_CAT_WSP)
    def do_export(self, stmt):
        '''Export workspace info'''
        key = getattr(stmt, 'exporter', 'list')
        if key == 'list':
            print("Available exporters:")
            data = []
            for key in Extensions.exports:
                data.append([key, Extensions.exports[key].descr()])
            print(tabulate.tabulate(data, headers=["Key", "Description"]))
            return
        try:
            exporter = Extensions.exports[key]
        except Exception as exc:
            print("Error: "+str(exc))
            return
        exporter.run(stmt, self.workspace)

#################################################################
###################          IMPORTS          ###################
#################################################################

    __parser_import = argparse.ArgumentParser(prog="import")
    __subparser_import = __parser_import.add_subparsers(title='Actions', help='Available importers')
    __parser_method = __subparser_import.add_parser('list', help='List available importers')
    for __key in Extensions.imports:
        __importer = Extensions.imports[__key]
        __parser_method = __subparser_import.add_parser(__key, help=__importer.descr())
        __parser_method.set_defaults(importer=__key)
        __importer.buildParser(__parser_method)

    @cmd2.with_argparser(__parser_import)
    @cmd2.with_category(__CMD_CAT_WSP)
    def do_import(self, stmt):
        '''Import workspace info'''
        key = getattr(stmt, 'importer', 'list')
        if key == 'list':
            print("Available importers:")
            data = []
            for key in Extensions.imports:
                data.append([key, Extensions.imports[key].descr()])
            print(tabulate.tabulate(data, headers=["Key", "Description"]))
            return
        try:
            importer = Extensions.imports[key]
        except Exception as exc:
            print("Error: "+str(exc))
            return
        importer.run(stmt, self.workspace)

#################################################################
###################           SCOPE           ###################
#################################################################

    def __get_all_objects(self):
        return self.workspace.get_objects(endpoints=True, creds=True, users=True, hosts=True)

    __parser_scope = argparse.ArgumentParser(prog="scope")
    __parser_scope.add_argument('target', help='Object to scope', choices_provider=__get_all_objects)
    @cmd2.with_argparser(__parser_scope)
    @cmd2.with_category(__CMD_CAT_WSP)
    def do_scope(self, stmt):
        '''Toggle object in/out of scope'''
        key = getattr(stmt, 'target', None)
        self.workspace.scope(key)

#################################################################
###################            CMD            ###################
#################################################################

    @cmd2.with_category(__CMD_CAT_WSP)
    def do_store(self, arg):
        for obj_type, objects in self.workspace.store.items():
            print(obj_type)
            for obj_id, obj in objects.items():
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

        if not os.path.exists(WORKSPACES_DIR):
            print("> First run ? Creating workspaces directory")
            os.makedirs(WORKSPACES_DIR)
        #Create default workspace if not exists
        if not os.path.exists(os.path.join(WORKSPACES_DIR, 'default')):
            Workspace.create('default')

        self.intro = '''
  %%%%%/      %%%     %%%%%.      .%%/     %%     %/   /%%%/   ,%%%/  *%%    %%
  %%   %%*   %% %%    %%   %%  %*       % %    /@*  % %%      %%      *%%    %% 
  %%%%%%    %%, %%%   %%%%%%  %    @@@@  %    /@@@  /  %%%%    %%%%   *%%%%%%%% 
  %%   %%% %%%%%%%%,  %%   %%(%          %%         %     %%%     %%% *%%    %% 
  %%%%%%  ,%%     %%  %%%%%%   %%      ,%   %#   %%   %%%%%.  %%%%%.  *%%    %%

Welcome to BabooSSH v\033[1;32m'''+BABOOSSH_VERSION+'''\033[0m. To start, use "help -v" to list commands.'''

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
