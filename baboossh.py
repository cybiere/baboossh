#!/usr/bin/env python3

from src.params import Extensions, workspacesDir
from src.workspace import Workspace
from tabulate import tabulate
import cmd2, sys, os
import re
import argparse
from cmd2 import with_argparser

Extensions.load()

def yesNo(prompt,default=None):
    if default is None:
        choices = "[y,n]"
    elif default:
        choices = "[Y,n]"
    else:
        choices = "[y,N]"
    a = ""
    while a not in ["y","n"]:
        a = input(prompt+" "+choices+" ").lower()
        if a == "" and default is not None:
            a = "y" if default else "n"
    return a == "y"


class BaboosshShell(cmd2.Cmd):
    intro = '\nWelcome to baboossh. Type help or ? to list commands.\n'
    prompt = '> '

#################################################################
###################         WORKSPACE         ###################
#################################################################

    def workspace_list(self, params):
        print("Existing workspaces :")
        workspaces = [name for name in os.listdir(workspacesDir)
            if os.path.isdir(os.path.join(workspacesDir, name))]
        for workspace in workspaces:
            if workspace == self.workspace.getName():
                print(" -["+workspace+"]")
            else:
                print(" - "+workspace)

    def workspace_add(self, stmt):
        name = vars(stmt)['name']
        #Check if name was given
        if re.match('^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            return
        #Check if workspace already exists
        if os.path.exists(os.path.join(workspacesDir,name)):
            print("Workspace already exists")
            return
        try:
            newWorkspace = Workspace.create(name)
        except:
            print("Workspace creation failed")
        else:
            self.workspace = newWorkspace

    def workspace_use(self,stmt):
        name = vars(stmt)['name']
        #Check if workspace already exists
        if not os.path.exists(os.path.join(workspacesDir,name)):
            print("Workspace does not exist")
        try:
            newWorkspace = Workspace(name)
        except:
            print("Workspace change failed")
        else:
            self.workspace = newWorkspace

    def getArgWorkspaces(self):
        return [name for name in os.listdir(workspacesDir) if os.path.isdir(os.path.join(workspacesDir, name))]

    parser_wspace = argparse.ArgumentParser(prog="workspace")
    subparser_wspace = parser_wspace.add_subparsers(title='Actions',help='Available actions')
    parser_wspace_list = subparser_wspace.add_parser("list",help='List workspaces')
    parser_wspace_add = subparser_wspace.add_parser("add",help='Add a new workspace')
    parser_wspace_add.add_argument('name',help='New workspace name')
    parser_wspace_use = subparser_wspace.add_parser("use",help='Change current workspace')
    use_arg = parser_wspace_use.add_argument('name', help='Name of workspace to use', choices_method=getArgWorkspaces)

    parser_wspace_list.set_defaults(func=workspace_list)
    parser_wspace_add.set_defaults(func=workspace_add)
    parser_wspace_use.set_defaults(func=workspace_use)

    @cmd2.with_argparser(parser_wspace)
    def do_workspace(self, stmt):
        '''Manage workspaces'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.workspace_list(None)

#################################################################
###################           HOSTS           ###################
#################################################################

    def host_list(self,stmt):
        print("Current hosts in workspace:")
        hosts = self.workspace.getHosts()
        if not hosts:
            print("No hosts in current workspace")
            return
        data = []
        for host in hosts:
            endpoints = ""
            for e in host.getEndpoints():
                if endpoints == "":
                    endpoints = str(e)
                else:
                    endpoints = endpoints + ", "+str(e)
            data.append([host.getId(),host.getName(),endpoints])
        print(tabulate(data,headers=["ID","Hostname","Endpoints"]))
 
    parser_host = argparse.ArgumentParser(prog="host")
    subparser_host = parser_host.add_subparsers(title='Actions',help='Available actions')
    parser_host_list = subparser_host.add_parser("list",help='List hosts')

    parser_host_list.set_defaults(func=host_list)

    @cmd2.with_argparser(parser_host)
    def do_host(self, stmt):
        '''Manage hosts'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.host_list(None)

#################################################################
###################         ENDPOINTS         ###################
#################################################################
   
    def endpoint_list(self,stmt):
        print("Current endpoints in workspace:")
        endpoints = self.workspace.getEndpoints()
        if not endpoints:
            print("No endpoints in current workspace")
            return
        data = []
        for endpoint in endpoints:
            c = endpoint.getConnection()
            if c is None:
                c = ""
            h = endpoint.getHost()
            if h is None:
                h = ""
            data.append([endpoint,h,c])
        print(tabulate(data,headers=["Endpoint","Host","Working connection"]))
    
    def endpoint_add(self,stmt):
        ip = vars(stmt)['ip']
        port = str(vars(stmt)['port'])
        addDirectPath = yesNo("Add path from local host ?",True)
        try:
            self.workspace.addEndpoint_Manual(ip,port,addDirectPath)
        except Exception as e:
            print("Endpoint addition failed: "+str(e))
        else:
            print("Endpoint "+ip+":"+port+" added.")

    parser_endpoint = argparse.ArgumentParser(prog="endpoint")
    subparser_endpoint = parser_endpoint.add_subparsers(title='Actions',help='Available actions')
    parser_endpoint_list = subparser_endpoint.add_parser("list",help='List endpoints')
    parser_endpoint_add = subparser_endpoint.add_parser("add",help='Add a new endpoint')
    parser_endpoint_add.add_argument('ip',help='New endpoint ip')
    parser_endpoint_add.add_argument('port',help='New endpoint port', type=int, default=22, nargs='?')

    parser_endpoint_list.set_defaults(func=endpoint_list)
    parser_endpoint_add.set_defaults(func=endpoint_add)

    @cmd2.with_argparser(parser_endpoint)
    def do_endpoint(self, stmt):
        '''Manage endpoints'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.endpoint_list(None)

#################################################################
###################           USERS           ###################
#################################################################

    def user_list(self,stmt):
        print("Current users in workspace:")
        users = self.workspace.getUsers()
        if not users:
            print("No users in current workspace")
            return
        data = []
        for user in users:
            data.append([user])
        print(tabulate(data,headers=["Username"]))
    
    def user_add(self,stmt):
        name = vars(stmt)['name']
        try:
            self.workspace.addUser_Manual(name)
        except Exception as e:
            print("User addition failed: "+str(e))
        else:
            print("User "+name+" added.")

    parser_user = argparse.ArgumentParser(prog="user")
    subparser_user = parser_user.add_subparsers(title='Actions',help='Available actions')
    parser_user_list = subparser_user.add_parser("list",help='List users')
    parser_user_add = subparser_user.add_parser("add",help='Add a new user')
    parser_user_add.add_argument('name',help='New user name')

    parser_user_list.set_defaults(func=user_list)
    parser_user_add.set_defaults(func=user_add)

    @cmd2.with_argparser(parser_user)
    def do_user(self, stmt):
        '''Manage users'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.user_list(None)

#################################################################
###################           CREDS           ###################
#################################################################

    def creds_types(self,stmt):
        print("Supported credential types:")
        data = []
        for key in Extensions.authMethodsAvail():
            data.append([key,Extensions.getAuthMethod(key).descr()])
        print(tabulate(data,headers=["Key","Description"]))
    
    def creds_list(self,stmt):
        creds = self.workspace.getCreds()
        if not creds:
            print("No creds in current workspace")
            return
        data = []
        for cred in creds:
            data.append(["#"+str(cred.getId()),cred.obj.getKey(),cred.obj.toList()])
        print(tabulate(data,headers=["ID","Type","Value"]))

    def creds_show(self,stmt):
        credsId = vars(stmt)['id']
        self.workspace.showCreds(credsId)
        pass

    def creds_edit(self,stmt):
        credsId = vars(stmt)['id']
        self.workspace.editCreds(credsId)
        pass

    def creds_add(self,stmt):
        credsType = vars(stmt)['type']
        try:
            credsId = self.workspace.addCreds_Manual(credsType,stmt)
        except Exception as e:
            print("Credentials addition failed: "+str(e))
        else:
            print("Credentials #"+str(credsId)+" added.")

    def getOptionCreds(self):
        return self.workspace.getCreds()

    parser_creds = argparse.ArgumentParser(prog="creds")
    subparser_creds = parser_creds.add_subparsers(title='Actions',help='Available actions')
    parser_creds_list = subparser_creds.add_parser("list",help='List saved credentials')
    parser_creds_types = subparser_creds.add_parser("types",help='List available credentials types')
    parser_creds_show = subparser_creds.add_parser("show",help='Show credentials details')
    parser_creds_show.add_argument('id',help='Creds identifier',choices_method=getOptionCreds)
    parser_creds_edit = subparser_creds.add_parser("edit",help='Edit credentials details')
    parser_creds_edit.add_argument('id',help='Creds identifier',choices_method=getOptionCreds)
    parser_creds_add = subparser_creds.add_parser("add",help='Add a new credentials')
    subparser_creds_add = parser_creds_add.add_subparsers(title='Add creds',help='Available creds types')
    for methodName in Extensions.authMethodsAvail():
        method = Extensions.getAuthMethod(methodName)
        parser_method = subparser_creds_add.add_parser(methodName,help=method.descr())
        parser_method.set_defaults(type=methodName)
        method.buildParser(parser_method)

    parser_creds_list.set_defaults(func=creds_list)
    parser_creds_types.set_defaults(func=creds_types)
    parser_creds_show.set_defaults(func=creds_show)
    parser_creds_edit.set_defaults(func=creds_edit)
    parser_creds_add.set_defaults(func=creds_add)

    @cmd2.with_argparser(parser_creds)
    def do_creds(self, stmt):
        '''Manage credentials'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.creds_list(None)

#################################################################
###################          PAYLOADS         ###################
#################################################################

    def payload_list(self,stmt):
        print("Available payloads:")
        data = []
        for key in Extensions.payloadsAvail():
            data.append([key,Extensions.getPayload(key).descr()])
        print(tabulate(data,headers=["Key","Description"]))
    
    parser_payload = argparse.ArgumentParser(prog="payload")
    subparser_payload = parser_payload.add_subparsers(title='Actions',help='Available actions')
    parser_payload_list = subparser_payload.add_parser("list",help='List payloads')

    parser_payload_list.set_defaults(func=payload_list)

    @cmd2.with_argparser(parser_payload)
    def do_payload(self, stmt):
        '''Manage payloads'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.payload_list(None)

#################################################################
###################        CONNECTIONS        ###################
#################################################################

    def connection_list(self,stmt):
        print("Available connections:")
        tested = False
        working = False
        if stmt is not None:
            opt = vars(stmt)["opt"]
            tested = "tested" in opt
            working = "working" in opt
        connections = self.workspace.getConnections(tested=tested,working=working)
        if not connections:
            print("No connections in current workspace")
            return
        data = []
        for connection in connections:
            data.append([connection.getEndpoint(),connection.getUser(),connection.getCred(),connection.isTested(),connection.isWorking()])
        print(tabulate(data,headers=["Endpoint","User","Creds","Tested","Working"]))
    
    parser_connection = argparse.ArgumentParser(prog="connection")
    subparser_connection = parser_connection.add_subparsers(title='Actions',help='Available actions')
    parser_connection_list = subparser_connection.add_parser("list",help='List connections')
    parser_connection_list.add_argument('opt',help='Filter options',nargs=argparse.REMAINDER,choices=["working","tested"])

    parser_connection_list.set_defaults(func=connection_list)

    @cmd2.with_argparser(parser_connection)
    def do_connection(self, stmt):
        '''Manage connections'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.connection_list(None)


#################################################################
###################          OPTIONS          ###################
#################################################################

    def options_list(self):
        print("Current options:")
        for key,val in self.workspace.getOptionsValues():
            print("    - "+key+": "+str(val))
    
    def getOptionUser(self):
        return self.workspace.getUsers()

    def getOptionEndpoint(self):
        return self.workspace.getEndpoints()

    def getOptionWordlist(self):
        return self.workspace.getWordlists()

    def getOptionPayload(self):
        return Extensions.payloadsAvail()

    def getOptionValidConnection(self):
        return self.workspace.getTargetsValidList()

    def getOptionConnection(self):
        return self.workspace.getTargetsList()

    parser_option = argparse.ArgumentParser(prog="option")
    subparser_option = parser_option.add_subparsers(title='Actions',help='Available actions')
    parser_option_list = subparser_option.add_parser("list",help='List options')
    parser_option_user = subparser_option.add_parser("user",help='Set target user')
    parser_option_user.add_argument('username',help='User name',nargs="?",choices_method=getOptionUser)
    parser_option_creds = subparser_option.add_parser("creds",help='Set target creds')
    parser_option_creds.add_argument('id',help='Creds ID',nargs="?",choices_method=getOptionCreds)
    parser_option_endpoint = subparser_option.add_parser("endpoint",help='Set target endpoint')
    parser_option_endpoint.add_argument('endpoint',nargs="?",help='Endpoint',choices_method=getOptionEndpoint)
    parser_option_payload = subparser_option.add_parser("payload",help='Set target payload')
    parser_option_payload.add_argument('payload',nargs="?",help='Payload name',choices_method=getOptionPayload)
    parser_option_connection = subparser_option.add_parser("connection",help='Set target connection')
    parser_option_connection.add_argument('connection',nargs="?",help='Connection string',choices_method=getOptionConnection)
    parser_option_params = subparser_option.add_parser("params",help='Set payload params')
    parser_option_params.add_argument('params',nargs="*",help='Payload params')

    parser_option_list.set_defaults(option="list")
    parser_option_user.set_defaults(option="user")
    parser_option_creds.set_defaults(option="creds")
    parser_option_endpoint.set_defaults(option="endpoint")
    parser_option_payload.set_defaults(option="payload")
    parser_option_connection.set_defaults(option="connection")
    parser_option_params.set_defaults(option="params")

    @cmd2.with_argparser(parser_option)
    def do_set(self,stmt):
        '''Manage options'''
        if 'option' not in vars(stmt):
            self.options_list()
            return
        option = vars(stmt)['option']
        if option is not None:
            if option == "list":
                self.options_list()
                return
            elif option == "user":
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
                self.workspace.setOption(option,value)
            except ValueError:
                print("Invalid value for "+option)
        else:
            self.options_list()

#################################################################
###################           PATHS           ###################
#################################################################

    def path_list(self,stmt):
        print("Current paths in workspace:")
        paths = self.workspace.getPaths()
        if not paths:
            print("No paths in current workspace")
            return
        data = []
        for path in paths:
            src = path.src
            if src == None:
                src = "Local"
            data.append([src,path.dst])
        print(tabulate(data,headers=["Source","Destination"]))
    
    def path_get(self,stmt):
        endpoint = vars(stmt)['endpoint']
        self.workspace.getPathToDst(endpoint)

    def path_add(self,stmt):
        src = vars(stmt)['src']
        dst = vars(stmt)['dst']
        self.workspace.addPath(src,dst)

    def getEndpointOrLocal(self):
        endpoints = self.workspace.getEndpoints()
        endpoints.append("local")
        return endpoints

    def getEndpointOrHost(self):
        endpoints = self.workspace.getEndpoints()
        hosts = self.workspace.getHostsNames()
        return endpoints + hosts

    parser_path = argparse.ArgumentParser(prog="path")
    subparser_path = parser_path.add_subparsers(title='Actions',help='Available actions')
    parser_path_list = subparser_path.add_parser("list",help='List paths')
    parser_path_get = subparser_path.add_parser("get",help='Get path to endpoint')
    parser_path_get.add_argument('endpoint',help='Endpoint',choices_method=getEndpointOrHost)
    parser_path_add = subparser_path.add_parser("add",help='Add path to endpoint')
    parser_path_add.add_argument('src',help='Source endpoint',choices_method=getEndpointOrLocal)
    parser_path_add.add_argument('dst',help='Destination endpoint',choices_method=getOptionEndpoint)

    parser_path_list.set_defaults(func=path_list)
    parser_path_get.set_defaults(func=path_get)
    parser_path_add.set_defaults(func=path_add)

    @cmd2.with_argparser(parser_path)
    def do_path(self, stmt):
        '''Manage paths'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.path_list(None)

#################################################################
###################          CONNECT          ###################
#################################################################

    parser_connect = argparse.ArgumentParser(prog="connect")
    parser_connect.add_argument("-v", "--verbose", help="increase output verbosity",action="store_true")
    parser_connect.add_argument("-g", "--gateway", help="force specific gateway",choices_method=getOptionEndpoint)
    parser_connect.add_argument('connection',help='Connection string',nargs="?",choices_method=getOptionConnection)

    @cmd2.with_argparser(parser_connect)
    def do_connect(self,stmt):
        connect = vars(stmt)['connection']
        verbose = vars(stmt)['verbose']
        gw = getattr(stmt,'gateway',None)
        if connect != None:
            try:
                self.workspace.connectTarget(connect,verbose,gw)
            except Exception as e:
                print("Targeted connect failed : "+str(e))
            return
        try:
            endpoints,users,creds = self.workspace.parseOptionsTarget()
        except:
            return
        nbIter = len(endpoints)*len(users)*len(creds)
        if nbIter > 1:
            if not yesNo("This will attempt up to "+str(nbIter)+" connections. Proceed ?",False):
                return
        if len(endpoints)*len(users)*len(creds) > 1:
            self.workspace.massConnect(endpoints,users,creds,verbose)
        else:
            self.workspace.connect(endpoints[0],users[0],creds[0],verbose)

    def getRunTargets(self):
        connections = self.getOptionValidConnection()
        endpoints = self.getOptionEndpoint()
        hosts = self.workspace.getHostsNames()
        return connections + endpoints + hosts


    parser_run = argparse.ArgumentParser(prog="run")
    parser_run.add_argument('connection',help='Connection string',nargs="?",choices_method=getRunTargets)
    subparser_run = parser_run.add_subparsers(title='Actions',help='Available actions')
    for payloadName in Extensions.payloadsAvail():
        payload = Extensions.getPayload(payloadName)
        parser_payload = subparser_run.add_parser(payloadName,help=payload.descr())
        parser_payload.set_defaults(type=payloadName)
        payload.buildParser(parser_payload)

    @cmd2.with_argparser(parser_run)
    def do_run(self,stmt):
        connect = getattr(stmt,'connection',None)
        payload = getattr(stmt,'type',None)
        self._reset_completion_defaults()
        if connect != None and payload != None:
            try:
                self.workspace.runTarget(connect,payload,stmt)
            except Exception as e:
                print("Run failed : "+str(e))
            return
        payload = self.workspace.getOption("payload")
        if payload is None:
            print("Error : No payload specified")
            return
        params = self.workspace.getOption("params")

        parser = argparse.ArgumentParser(description='Params parser')
        payload.buildParser(parser)
        if params is None:
            params = ""
        stmt,unk= parser.parse_known_args(params.split())

        try:
            endpoints,users,creds = self.workspace.parseOptionsTarget()
        except:
            return
        nbIter = len(endpoints)*len(users)*len(creds)
        if nbIter > 1:
            if not yesNo("This will attempt up to "+str(nbIter)+" connections. Proceed ?",False):
                return
        for endpoint in endpoints:
            for user in users:
                for cred in creds:
                    if self.workspace.run(endpoint,user,cred,payload,stmt):
                        break;

#################################################################
###################          TUNNELS          ###################
#################################################################

    def tunnel_list(self,stmt):
        print("Current tunnels in workspace:")
        tunnels = self.workspace.getTunnels()
        if not tunnels:
            print("No tunnels in current workspace")
            return
        data = []
        for tunnel in tunnels:
            data.append([tunnel.port,tunnel.connection])
        print(tabulate(data,headers=["Local port","Destination"]))

    def tunnel_open(self,stmt):
        connectionStr = getattr(stmt, 'connection', None)
        port = getattr(stmt, 'port', None)
        self.workspace.openTunnel(connectionStr,port)

    def tunnel_close(self,stmt):
        port = getattr(stmt, 'port', None)
        self.workspace.closeTunnel(port)

    def getOpenTunnels(self):
        return self.workspace.getTunnelsPort()

    parser_tunnel = argparse.ArgumentParser(prog="tunnel")
    subparser_tunnel = parser_tunnel.add_subparsers(title='Actions',help='Available actions')
    parser_tunnel_list = subparser_tunnel.add_parser("list",help='List tunnels')
    parser_tunnel_open = subparser_tunnel.add_parser("open",help='Open tunnel')
    parser_tunnel_open.add_argument('connection',help='Connection string',choices_method=getOptionValidConnection)
    parser_tunnel_open.add_argument('port',help='Tunnel entry port', type=int, nargs='?')
    parser_tunnel_close = subparser_tunnel.add_parser("close",help='Close tunnel')
    parser_tunnel_close.add_argument('port',help='Tunnel entry port', type=int,choices_method=getOpenTunnels)

    parser_tunnel_list.set_defaults(func=tunnel_list)
    parser_tunnel_open.set_defaults(func=tunnel_open)
    parser_tunnel_close.set_defaults(func=tunnel_close)

    @cmd2.with_argparser(parser_tunnel)
    def do_tunnel(self, stmt):
        '''Manage tunnels'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.tunnel_list(None)

#################################################################
###################          EXPORTS          ###################
#################################################################


    parser_export = argparse.ArgumentParser(prog="export")
    subparser_export = parser_export.add_subparsers(title='Actions',help='Available exporters')
    parser_method = subparser_export.add_parser('list',help='List available exporters')
    for key in Extensions.exportsAvail():
        export = Extensions.getExport(key)
        parser_method = subparser_export.add_parser(key,help=export.descr())
        parser_method.set_defaults(exporter=key)
        export.buildParser(parser_method)

    @cmd2.with_argparser(parser_export)
    def do_export(self,stmt):
        '''Export workspace info'''
        key = getattr(stmt,'exporter','list')
        if key == 'list':
            print("Available exporters:")
            data = []
            for key in Extensions.exportsAvail():
                data.append([key,Extensions.getExport(key).descr()])
            print(tabulate(data,headers=["Key","Description"]))
            return
        try:
            exporter = Extensions.getExport(key)
        except Exception as e:
            print("Error: "+str(e))
            return
        exporter.run(stmt,self.workspace)

#################################################################
###################          IMPORTS          ###################
#################################################################
    
    parser_import = argparse.ArgumentParser(prog="import")
    subparser_import = parser_import.add_subparsers(title='Actions',help='Available importers')
    parser_method = subparser_import.add_parser('list',help='List available importers')
    for key in Extensions.importsAvail():
        importer = Extensions.getImport(key)
        parser_method = subparser_import.add_parser(key,help=importer.descr())
        parser_method.set_defaults(importer=key)
        importer.buildParser(parser_method)

    @cmd2.with_argparser(parser_import)
    def do_import(self,stmt):
        '''Import workspace info'''
        key = getattr(stmt,'importer','list')
        if key == 'list':
            print("Available importers:")
            data = []
            for key in Extensions.importsAvail():
                data.append([key,Extensions.getImport(key).descr()])
            print(tabulate(data,headers=["Key","Description"]))
            return
        try:
            importer = Extensions.getImport(key)
        except Exception as e:
            print("Error: "+str(e))
            return
        importer.run(stmt,self.workspace)

#################################################################
###################            CMD            ###################
#################################################################

    def do_exit(self, arg):
        'Quit Baboossh'
        self.workspace.close()
        print("Bye !")
        return True
    
    def initPrompt(self):
        newPrompt = "\033[1;33;40m"
        newPrompt = newPrompt+"["+self.workspace.getName()+"]\033[1;34m"
        if self.workspace.getOption("endpoint"):
            if self.workspace.getOption("user"):
                newPrompt = newPrompt+str(self.workspace.getOption("user"))
                if self.workspace.getOption("creds"):
                    newPrompt = newPrompt+":"+str(self.workspace.getOption("creds"))
                newPrompt = newPrompt+"@"
            newPrompt = newPrompt+str(self.workspace.getOption("endpoint"))
        elif self.workspace.getOption("user"):
            newPrompt = newPrompt+str(self.workspace.getOption("user"))
            if self.workspace.getOption("creds"):
                newPrompt = newPrompt+":"+str(self.workspace.getOption("creds"))
            newPrompt = newPrompt+"@..."
        if self.workspace.getOption("payload"):
            newPrompt = newPrompt+"\033[1;31;40m("+str(self.workspace.getOption("payload"))+")\033[0m"
        self.prompt = newPrompt+"\033[1;33;40m>\033[0m "

    def emptyline(self):
        pass

    def postcmd(self,stop,line):
        self.initPrompt()
        return stop
        

    def __init__(self):
        super().__init__()
        self.workspace = Workspace("default")
        self.initPrompt()
        #Removes cmd2 default commands
        self.disable_command("run_pyscript","disabled")
        self.disable_command("run_script","disabled")
        self.disable_command("alias","disabled")
        self.disable_command("edit","disabled")
        self.disable_command("quit","disabled")
        self.disable_command("macro","disabled")
        self.disable_command("shortcuts","disabled")
        self.quit_on_sigint = False
        #TODO remove debug
        self.debug=True



if __name__ == '__main__':
    if not os.path.exists(workspacesDir):
        print("> First run ? Creating workspaces directory")
        os.makedirs(workspacesDir)

    #Create default workspace if not exists
    if not os.path.exists(os.path.join(workspacesDir,'default')):
        Workspace.create('default')

    BaboosshShell().cmdloop()

