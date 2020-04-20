#!/usr/bin/env python3

"""BabooSSH interactive interface

This module contains the whole user interface for BabooSSH, extending
cmd2 and providing completion & command syntax help. It also loads the
extensions on startup.

Typical usage example:

    from baboossh.shell import BaboosshShell
    BaboosshShell().cmdloop()

"""

import os
import re
import argparse
from shutil import rmtree
import cmd2
from tabulate import tabulate
from baboossh.params import Extensions, workspacesDir, yesNo
from baboossh.workspace import Workspace

Extensions.load()

class BaboosshShell(cmd2.Cmd):
    """BabooSSH Shell interface

    This class extends cmd2.Cmd to build the user interface.

    Attributes:
        intro (str): The banner printed on program start
        prompt (str): The default prompt
        workspace (Workspace): The current open baboossh.Workspace
        debug (bool): Boolean for debug output
    """

    intro = '''                                                                            &%%%%#%%%%%
  %%%%%%%%%%%@         %%%%%&        %%%%%%%%%%%         @%%%%%%%%@       %%/          %%@    @%%%%%%%%%@    %%%%%%%%%&   %%%%       %%%%  
  %%%%%%%%%%%%%       %%%%%%%        %%%%%%%%%%%%%     %%/        *%%@  &%,              %%  %%%%%%%%%%%   &%%%%%%%%%%    %%%%       %%%%  
  %%%%     %%%%      @%%% %%%%       %%%%     %%%%   %%.      .##.   %%@%.      % *@@(    %& %%%%          %%%%           %%%%       %%%%  
  %%%%   @&%%%%      %%%%  %%%&      %%%%   @%%%%%  %%       #  @@@   %%%      *@(@@@@.   /% %%%%%&        %%%%%&         %%%%       %%%%  
  %%%%%%%%%%%@      %%%%   %%%%      %%%%%%%%%%&@  @%*      ,@@@@@@.  .%#       @@@@@*    ,%   %%%%%%%&      %%%%%%%&     %%%%%%%%%%%%%%%  
  %%%%     %%%%    %%%%%%%%%%%%%     %%%%     %%%% %%.       .@@@@     %%                 #%      %%%%%%        %%%%%%&   %%%%       %%%%  
  %%%%     @%%%&  @%%%%%%%%%%%%%%    %%%%     &%%%  %(                ,%%#               *%          %%%%          %%%%   %%%%       %%%%  
  %%%%&&&%%%%%%   %%%%       %%%%&   %%%%&&&%%%%%%  %%*               %% %%,            %%   %%%&&@&%%%%   %%%&&@&%%%%%   %%%%       %%%%  
  %%%%%%%%%%%%   %%%%%        %%%%   %%%%%%%%%%%      %%            #%%    %%%.      #%%%    %%%%%%%%%%    %%%%%%%%%%     %%%%       %%%%  
                                                       %%%(      *%%%         %%%%%%%                                                      
                                                           %%%%%%

Welcome to BabooSSH. Type help or ? to list commands.'''

    prompt = '> '

#################################################################
###################          GETTERS          ###################
#################################################################

    def __get_options_creds(self):
        return self.workspace.getCreds(scope=True)

    def __get_hosts(self):
        return self.workspace.getHostsNames(scope=True)

    def __get_arg_workspaces(self):
        return [name for name in os.listdir(workspacesDir) if os.path.isdir(os.path.join(workspacesDir, name))]

    def __get_option_gateway(self):
        ret = ["local"]
        endpoints = self.workspace.getEndpoints(scope=True)
        for endpoint in endpoints:
            if endpoint.getConnection() is not None:
                ret.append(endpoint)
        return ret

    def __get_option_user(self):
        return self.workspace.getUsers(scope=True)

    def __get_option_endpoint(self):
        return self.workspace.getEndpoints(scope=True)

    def __get_option_payload(self):
        return Extensions.payloadsAvail()

    def __get_option_valid_connection(self):
        return self.workspace.getTargetsValidList(scope=True)

    def __get_option_connection(self):
        return self.workspace.getTargetsList(scope=True)

    def __get_search_fields_endpoint(self):
        return self.workspace.getSearchFields("Endpoint")

    def __get_search_fields_host(self):
        return self.workspace.getSearchFields("Host")

    def __get_open_tunnels(self):
        return self.workspace.getTunnelsPort()

    def __get_run_targets(self):
        connections = self.__get_option_valid_connection()
        endpoints = self.__get_option_endpoint()
        hosts = self.workspace.getHostsNames(scope=True)
        return connections + endpoints + hosts

    def __get_host_or_local(self):
        hosts = self.workspace.getHostsNames(scope=True)
        hosts.append("local")
        return hosts

    def __get_endpoint_or_host(self):
        endpoints = self.workspace.getEndpoints(scope=True)
        hosts = self.workspace.getHostsNames(scope=True)
        return endpoints + hosts

#################################################################
###################         WORKSPACE         ###################
#################################################################

    def __workspace_list(self, stmt):
        print("Existing workspaces :")
        workspaces = [name for name in os.listdir(workspacesDir) if os.path.isdir(os.path.join(workspacesDir, name))]
        for workspace in workspaces:
            if workspace == self.workspace.getName():
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
        except Exception as exc:
            print("Workspace creation failed: "+str(exce))
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
        except:
            print("Workspace change failed")
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
        if not yesNo("Are you sure you want to delete workspace "+name+"?", default=False):
            return
        rmtree(os.path.join(workspacesDir, name))
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
            for endpoint in host.getEndpoints():
                if endpoints == "":
                    endpoints = str(endpoint)
                else:
                    endpoints = endpoints + ", "+str(endpoint)
            scope = "o" if host.inScope() else ""
            data.append([scope, host.getId(), host.getName(), endpoints])
        print(tabulate(data, headers=["", "ID", "Hostname", "Endpoints"]))

    def __host_list(self, stmt):
        print("Current hosts in workspace:")
        show_all = getattr(stmt, 'all', False)
        hosts = self.workspace.getHosts()
        if not hosts:
            print("No hosts in current workspace")
            return
        data = []
        for host in hosts:
            if not host.inScope() and not show_all:
                continue
            data.append(host)
        self.__host_print(data)

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
        return self.workspace.delHost(host)

    __parser_host = argparse.ArgumentParser(prog="host")
    __subparser_host = __parser_host.add_subparsers(title='Actions', help='Available actions')
    __parser_host_list = __subparser_host.add_parser("list", help='List hosts')
    __parser_host_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_host_search = __subparser_host.add_parser("search", help='Search a host')
    __parser_host_search.add_argument('field', help='Field to search in', choices_method=__get_search_fields_host)
    __parser_host_search.add_argument('val', help='Value to search')

    __parser_host_del = __subparser_host.add_parser("delete", help='Delete host')
    __parser_host_del.add_argument('host', help='Host name', choices_method=__get_hosts)

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
            scope = "o" if endpoint.inScope() else ""
            conn = endpoint.getConnection()
            if conn is None:
                conn = ""
            host = endpoint.getHost()
            if host is None:
                host = ""
            scanned = str(endpoint.isScanned())
            if endpoint.isReachable() is None:
                reachable = "?"
            else:
                reachable = str(endpoint.isReachable())
            if not endpoint.getAuth():
                auth = "?"
            else:
                auth = str(endpoint.getAuth())
            data.append([scope, endpoint, host, scanned, reachable, auth, conn])
        print(tabulate(data, headers=["", "Endpoint", "Host", "Scanned", "Reachable", "Authentication", "Working connection"]))

    def __endpoint_list(self, stmt):
        print("Current endpoints in workspace:")
        show_all = getattr(stmt, 'all', False)
        reachable = getattr(stmt, 'reachable', None)
        scanned = getattr(stmt, 'scanned', None)
        conn = getattr(stmt, 'conn', None)
        endpoints = self.workspace.getEndpoints()
        if not endpoints:
            print("No endpoints in current workspace")
            return

        endpoint_list = []
        for endpoint in endpoints:
            if not show_all:
                if not endpoint.inScope():
                    continue
                if scanned is not None:
                    flag_scanned = scanned == "true"
                    if endpoint.isScanned() != flag_scanned:
                        continue
                if reachable is not None:
                    flag_reachable = reachable == "true"
                    if endpoint.isReachable() != flag_reachable:
                        continue
                if conn is not None:
                    flag_conn = conn == "true"
                    if (endpoint.getConnection() is None) == flag_conn:
                        continue
            endpoint_list.append(endpoint)
        self.__endpoint_print(endpoint_list)

    def __endpoint_add(self, stmt):
        ip_add = vars(stmt)['ip']
        port = str(vars(stmt)['port'])
        try:
            self.workspace.addEndpoint(ip_add, port)
        except Exception as e:
            print("Endpoint addition failed: "+str(e))
        else:
            print("Endpoint "+ip_add+":"+port+" added.")

    def __endpoint_del(self, stmt):
        endpoint = vars(stmt)['endpoint']
        return self.workspace.delEndpoint(endpoint)

    def __endpoint_search(self, stmt):
        show_all = getattr(stmt, 'all', False)
        field = vars(stmt)['field']
        allowed_fields = self.__get_search_fields_endpoint()
        if field not in allowed_fields:
            print("Invalid field specified, use one of "+str(allowed_fields)+".")
            return
        val = vars(stmt)['val']
        endpoints = self.workspace.searchEndpoints(field, val, show_all)
        print("Search result for endpoints:")
        if not endpoints:
            print("No results")
            return
        self.__endpoint_print(endpoints)


    __parser_endpoint = argparse.ArgumentParser(prog="endpoint")
    __subparser_endpoint = __parser_endpoint.add_subparsers(title='Actions', help='Available actions')
    __parser_endpoint_list = __subparser_endpoint.add_parser("list", help='List endpoints')
    __parser_endpoint_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_endpoint_list.add_argument("-s", "--scanned", help="Show only scanned endpoints", nargs='?', choices=["true", "false"], const="true")
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
        users = self.workspace.getUsers()
        if not users:
            print("No users in current workspace")
            return
        data = []
        for user in users:
            if not user.inScope() and not show_all:
                continue
            scope = "o" if user.inScope() else ""
            data.append([scope, user])
        print(tabulate(data, headers=["", "Username"]))

    def __user_add(self, stmt):
        name = vars(stmt)['name']
        try:
            self.workspace.addUser(name)
        except Exception as e:
            print("User addition failed: "+str(e))
        else:
            print("User "+name+" added.")

    def __user_del(self, stmt):
        name = vars(stmt)['name']
        return self.workspace.delUser(name)

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
        print(tabulate(data, headers=["Key", "Description"]))

    def __creds_list(self, stmt):
        show_all = getattr(stmt, 'all', False)
        creds = self.workspace.getCreds()
        if not creds:
            print("No creds in current workspace")
            return
        data = []
        for cred in creds:
            if not cred.inScope() and not show_all:
                continue
            scope = "o" if cred.inScope() else ""
            data.append([scope, "#"+str(cred.getId()), cred.obj.getKey(), cred.obj.toList()])
        print(tabulate(data, headers=["", "ID", "Type", "Value"]))

    def __creds_show(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.showCreds(creds_id)

    def __creds_edit(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.editCreds(creds_id)

    def __creds_del(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.delCreds(creds_id)

    def __creds_add(self, stmt):
        creds_type = vars(stmt)['type']
        try:
            creds_id = self.workspace.addCreds(creds_type, stmt)
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
    __parser_creds_show.add_argument('id', help='Creds identifier', choices_method=__get_options_creds)
    __parser_creds_edit = __subparser_creds.add_parser("edit", help='Edit credentials details')
    __parser_creds_edit.add_argument('id', help='Creds identifier', choices_method=__get_options_creds)
    __parser_creds_add = __subparser_creds.add_parser("add", help='Add a new credentials')
    __subparser_creds_add = __parser_creds_add.add_subparsers(title='Add creds', help='Available creds types')
    for __methodName in Extensions.authMethodsAvail():
        __method = Extensions.getAuthMethod(__methodName)
        __parser_method = __subparser_creds_add.add_parser(__methodName, help=__method.descr())
        __parser_method.set_defaults(type=__methodName)
        __method.buildParser(__parser_method)
    __parser_creds_del = __subparser_creds.add_parser("delete", help='Delete credentials from workspace')
    __parser_creds_del.add_argument('id', help='Creds identifier', choices_method=__get_options_creds)

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
        print(tabulate(data, headers=["Key", "Description"]))

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
        working = getattr(stmt, 'working', None)
        tested = getattr(stmt, 'tested', None)
        connections = self.workspace.getConnections()
        if not connections:
            print("No connections in current workspace")
            return
        data = []
        for connection in connections:
            if not show_all:
                if not connection.inScope():
                    continue
                if working is not None:
                    flag_working = working == "true"
                    if connection.isWorking() != flag_working:
                        continue
                if tested is not None:
                    flag_tested = tested == "true"
                    if connection.isTested() != flag_tested:
                        continue
            data.append([connection.getEndpoint(), connection.getUser(), connection.getCred(), connection.isTested(), connection.isWorking()])
        print(tabulate(data, headers=["Endpoint", "User", "Creds", "Tested", "Working"]))

    def __connection_del(self, stmt):
        connection = getattr(stmt, "connection", None)
        return self.workspace.delConnection(connection)

    __parser_connection = argparse.ArgumentParser(prog="connection")
    __subparser_connection = __parser_connection.add_subparsers(title='Actions', help='Available actions')
    __parser_connection_list = __subparser_connection.add_parser("list", help='List connections')
    __parser_connection_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_connection_list.add_argument("-w", "--working", help="Show only working connections", nargs='?', choices=["true", "false"], const="true")
    __parser_connection_list.add_argument("-t", "--tested", help="Show only tested connections", nargs='?', choices=["true", "false"], const="true")
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
        for key, val in self.workspace.getOptionsValues():
            print("    - "+key+": "+str(val))

    __parser_option = argparse.ArgumentParser(prog="option")
    __subparser_option = __parser_option.add_subparsers(title='Actions', help='Available actions')
    __parser_option_list = __subparser_option.add_parser("list", help='List options')
    __parser_option_user = __subparser_option.add_parser("user", help='Set target user')
    __parser_option_user.add_argument('username', help='User name', nargs="?", choices_method=__get_option_user)
    __parser_option_creds = __subparser_option.add_parser("creds", help='Set target creds')
    __parser_option_creds.add_argument('id', help='Creds ID', nargs="?", choices_method=__get_options_creds)
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
                self.workspace.setOption(option, value)
            except ValueError:
                print("Invalid value for "+option)
        else:
            self.__options_list()

#################################################################
###################           PATHS           ###################
#################################################################

    def __path_list(self, stmt):
        print("Current paths in workspace:")
        show_all = getattr(stmt, 'all', False)
        paths = self.workspace.getPaths()
        if not paths:
            print("No paths in current workspace")
            return
        data = []
        for path in paths:
            if not path.inScope() and not show_all:
                continue
            src = path.src
            if src is None:
                src = "Local"
            data.append([src, path.dst])
        print(tabulate(data, headers=["Source", "Destination"]))

    def __path_get(self, stmt):
        endpoint = vars(stmt)['endpoint']
        self.workspace.getPathToDst(endpoint)

    def __path_add(self, stmt):
        src = vars(stmt)['src']
        dst = vars(stmt)['dst']
        self.workspace.addPath(src, dst)

    def __path_del(self, stmt):
        src = vars(stmt)['src']
        dst = vars(stmt)['dst']
        self.workspace.delPath(src, dst)

    def __path_find(self, stmt):
        dst = vars(stmt)['dst']
        self.workspace.findPath(dst)

    __parser_path = argparse.ArgumentParser(prog="path")
    __subparser_path = __parser_path.add_subparsers(title='Actions', help='Available actions')
    __parser_path_list = __subparser_path.add_parser("list", help='List paths')
    __parser_path_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_path_get = __subparser_path.add_parser("get", help='Get path to endpoint')
    __parser_path_get.add_argument('endpoint', help='Endpoint', choices_method=__get_endpoint_or_host)
    __parser_path_add = __subparser_path.add_parser("add", help='Add path to endpoint')
    __parser_path_add.add_argument('src', help='Source host', choices_method=__get_host_or_local)
    __parser_path_add.add_argument('dst', help='Destination endpoint', choices_method=__get_option_endpoint)
    __parser_path_del = __subparser_path.add_parser("delete", help='Delete path to endpoint')
    __parser_path_del.add_argument('src', help='Source host', choices_method=__get_host_or_local)
    __parser_path_del.add_argument('dst', help='Destination endpoint', choices_method=__get_option_endpoint)
    __parser_path_find = __subparser_path.add_parser("find", help='Find shortest path to endpoint or host')
    __parser_path_find.add_argument('dst', help='Destination', choices_method=__get_endpoint_or_host)

    __parser_path_list.set_defaults(func=__path_list)
    __parser_path_get.set_defaults(func=__path_get)
    __parser_path_add.set_defaults(func=__path_add)
    __parser_path_del.set_defaults(func=__path_del)
    __parser_path_find.set_defaults(func=__path_find)

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
###################           SCAN            ###################
#################################################################

    __parser_scan = argparse.ArgumentParser(prog="scan")
    __parser_scan.add_argument("-g", "--gateway", help="force specific gateway", choices_method=__get_option_gateway)
    __parser_scan.add_argument('endpoint', help='Endpoint', nargs="?", choices_method=__get_option_endpoint)

    @cmd2.with_argparser(__parser_scan)
    def do_scan(self, stmt):
        '''Scan endpoint to check connectivity and supported authentication methods'''
        target = vars(stmt)['endpoint']
        gateway = vars(stmt)['gateway']
        if target is not None:
            try:
                self.workspace.scanTarget(target, gateway=gateway)
            except Exception as e:
                print("Targeted scan failed : "+str(e))
            return
        try:
            endpoints, users, creds = self.workspace.parseOptionsTarget()
        except:
            return
        nb_iter = len(endpoints)
        if nb_iter > 1:
            if not yesNo("This will attempt up to "+str(nb_iter)+" scans. Proceed ?", False):
                return
        for endpoint in endpoints:
            self.workspace.scanTarget(endpoint, gateway=gateway)

#################################################################
###################          CONNECT          ###################
#################################################################

    __parser_connect = argparse.ArgumentParser(prog="connect")
    __parser_connect.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_connect.add_argument("-g", "--gateway", help="force specific gateway", choices_method=__get_option_gateway)
    __parser_connect.add_argument('connection', help='Connection string', nargs="?", choices_method=__get_option_connection)

    @cmd2.with_argparser(__parser_connect)
    def do_connect(self, stmt):
        '''Try connection to endpoint and identify host'''
        connect = vars(stmt)['connection']
        verbose = vars(stmt)['verbose']
        gateway = getattr(stmt, 'gateway', None)
        if connect is not None:
            try:
                self.workspace.connectTarget(connect, verbose, gateway)
            except Exception as e:
                print("Targeted connect failed : "+str(e))
            return
        self.workspace.massConnect(verbose)


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
        connect = getattr(stmt, 'connection', None)
        payload = getattr(stmt, 'type', None)
        self._reset_completion_defaults()
        if connect is not None and payload is not None:
            try:
                self.workspace.runTarget(connect, payload, stmt)
            except Exception as e:
                print("Run failed : "+str(e))
            return
        payload = self.workspace.getOption("payload")
        if payload is None:
            print("Error : No payload specified")
            return
        params = self.workspace.getOption("params")

        __parser = argparse.ArgumentParser(description='Params __parser')
        payload.buildParser(__parser)
        if params is None:
            params = ""
        stmt, unk = __parser.parse_known_args(params.split())

        try:
            endpoints, users, creds = self.workspace.parseOptionsTarget()
        except:
            return
        nb_iter = len(endpoints)*len(users)*len(creds)
        if nb_iter > 1:
            if not yesNo("This will attempt up to "+str(nb_iter)+" connections. Proceed ?", False):
                return
        for endpoint in endpoints:
            for user in users:
                for cred in creds:
                    if self.workspace.run(endpoint, user, cred, payload, stmt):
                        break

#################################################################
###################          TUNNELS          ###################
#################################################################

    def __tunnel_list(self, stmt):
        print("Current tunnels in workspace:")
        tunnels = self.workspace.getTunnels()
        if not tunnels:
            print("No tunnels in current workspace")
            return
        data = []
        for tunnel in tunnels:
            data.append([tunnel.port, tunnel.connection])
        print(tabulate(data, headers=["Local port", "Destination"]))

    def __tunnel_open(self, stmt):
        connection_str = getattr(stmt, 'connection', None)
        port = getattr(stmt, 'port', None)
        self.workspace.openTunnel(connection_str, port)

    def __tunnel_close(self, stmt):
        port = getattr(stmt, 'port', None)
        self.workspace.closeTunnel(port)

    __parser_tunnel = argparse.ArgumentParser(prog="tunnel")
    __subparser_tunnel = __parser_tunnel.add_subparsers(title='Actions', help='Available actions')
    __parser_tunnel_list = __subparser_tunnel.add_parser("list", help='List tunnels')
    __parser_tunnel_open = __subparser_tunnel.add_parser("open", help='Open tunnel')
    __parser_tunnel_open.add_argument('connection', help='Connection string', choices_method=__get_option_valid_connection)
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
            print(tabulate(data, headers=["Key", "Description"]))
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
            print(tabulate(data, headers=["Key", "Description"]))
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

    def __get_scope_object(self):
        return self.workspace.getBaseObjects(scope=False)

    def __get_unscope_object(self):
        return self.workspace.getBaseObjects(scope=True)

    __parser_scope = argparse.ArgumentParser(prog="scope")
    __parser_scope.add_argument('target', help='Object to scope', choices_method=__get_scope_object)
    @cmd2.with_argparser(__parser_scope)
    def do_scope(self, stmt):
        '''Add object to scope'''
        key = getattr(stmt, 'target', None)
        self.workspace.scope(key)

    __parser_unscope = argparse.ArgumentParser(prog="unscope")
    __parser_unscope.add_argument('target', help='Object to unscope', choices_method=__get_unscope_object)
    @cmd2.with_argparser(__parser_unscope)
    def do_unscope(self, stmt):
        '''Remove object from scope'''
        key = getattr(stmt, 'target', None)
        self.workspace.unscope(key)

#################################################################
###################            CMD            ###################
#################################################################

    def do_exit(self, arg):
        'Close active workspace & quit Baboossh'

        self.workspace.close()
        print("Bye !")
        return True

    def __init_prompt(self):
        'Build prompt to output currect workspace & active options'

        new_prompt = "\033[1;33m"
        new_prompt = new_prompt+"["+self.workspace.getName()+"]\033[1;34m"
        if self.workspace.getOption("endpoint"):
            if self.workspace.getOption("user"):
                new_prompt = new_prompt+str(self.workspace.getOption("user"))
                if self.workspace.getOption("creds"):
                    new_prompt = new_prompt+":"+str(self.workspace.getOption("creds"))
                new_prompt = new_prompt+"@"
            new_prompt = new_prompt+str(self.workspace.getOption("endpoint"))
        elif self.workspace.getOption("user"):
            new_prompt = new_prompt+str(self.workspace.getOption("user"))
            if self.workspace.getOption("creds"):
                new_prompt = new_prompt+":"+str(self.workspace.getOption("creds"))
            new_prompt = new_prompt+"@..."
        if self.workspace.getOption("payload"):
            new_prompt = new_prompt+"\033[1;31m("+str(self.workspace.getOption("payload"))+")\033[0m"
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
