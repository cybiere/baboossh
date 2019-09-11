#!/usr/bin/env python3

from src.params import Extensions
from src.workspace import Workspace
from tabulate import tabulate
import configparser
import cmd2, sys, os
import re
import argparse
from cmd2 import with_argparser

config = configparser.ConfigParser()
config.read('config.ini')
if "DEFAULT" not in config or "workspaces" not in config['DEFAULT']:
    print("Invalid config file")
    exit()

def yesNo(prompt,default=None):
    if default is None:
        choices = "[y,n]"
    elif default:
        choices = "[Y,n]"
    else:
        choices = "[y,N]"
    a = ""
    while a not in ["y","n"]:
        a = input(prompt+" "+choices+" ")
        if a == "" and default is not None:
            a = "y" if default else "n"
    return a == "y"


class BaboosshShell(cmd2.Cmd):
    intro = '\nWelcome to baboossh. Type help or ? to list commands.\n'
    prompt = '> '

#################################################################
###################         WORKSPACE         ###################
#################################################################

    def workspace_help(self, params):
        self.do_help("workspace")

    def workspace_list(self, params):
        print("Existing workspaces :")
        workspaces = [name for name in os.listdir(config['DEFAULT']['workspaces'])
            if os.path.isdir(os.path.join(config['DEFAULT']['workspaces'], name))]
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
        if os.path.exists(os.path.join(config['DEFAULT']['workspaces'],name)):
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
        if not os.path.exists(os.path.join(config['DEFAULT']['workspaces'],name)):
            print("Workspace does not exist")
        try:
            newWorkspace = Workspace(name)
        except:
            print("Workspace change failed")
        else:
            self.workspace = newWorkspace

    def workspace_del(self, params):
        raise NotImplementedError

    def getArgWorkspaces(self):
        return [name for name in os.listdir(config['DEFAULT']['workspaces']) if os.path.isdir(os.path.join(config['DEFAULT']['workspaces'], name))]

    parser_wspace = argparse.ArgumentParser(prog="workspace")
    subparser_wspace = parser_wspace.add_subparsers(title='Actions',help='Available actions')
    parser_wspace_help = subparser_wspace.add_parser("help",help='Show workspace help')
    parser_wspace_list = subparser_wspace.add_parser("list",help='List workspaces')
    parser_wspace_add = subparser_wspace.add_parser("add",help='Add a new workspace')
    parser_wspace_add.add_argument('name',help='New workspace name')
    parser_wspace_use = subparser_wspace.add_parser("use",help='Change current workspace')
    use_arg = parser_wspace_use.add_argument('name', help='Name of workspace to use', choices_method=getArgWorkspaces)
    parser_wspace_del = subparser_wspace.add_parser("del",help='Delete workspace')
    del_arg = parser_wspace_del.add_argument('name', help='Name of workspace to delete', choices_method=getArgWorkspaces)

    parser_wspace_help.set_defaults(func=workspace_help)
    parser_wspace_list.set_defaults(func=workspace_list)
    parser_wspace_add.set_defaults(func=workspace_add)
    parser_wspace_use.set_defaults(func=workspace_use)
    parser_wspace_del.set_defaults(func=workspace_del)

    @cmd2.with_argparser(parser_wspace)
    def do_workspace(self, stmt):
        '''Manage workspaces'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            # No subcommand was provided, so call help
            self.workspace_list(None)

#################################################################
###################           HOSTS           ###################
#################################################################
    """
    def do_host(self, arg):
        '''HOST: Manage hosts
Available commands:
    - host help                 show this help
    - host list                 list existing hosts
'''
        command,sep,params = arg.partition(" ")
        if command == "list" or command == "":
            self.host_list()
        else:
            if command != "help" and command != "?":
                print("Unrecognized command.")
            self.host_help()
    
    def host_list(self):
        print("Current hosts in workspace:")
        hosts = self.workspace.getHosts()
        if not hosts:
            print("No hosts in current workspace")
            return
        for host in hosts:
            print(host.toList())

    def host_help(self):
        print('''Available commands:
    - host help                 show this help
    - host list                 list existing hosts''')

    def complete_host(self, text, line, begidx, endidx):
        matches = []
        n = len(text)
        for word in ['list','help']:
            if word[:n] == text:
                matches.append(word)
        return matches
    """

#################################################################
###################         ENDPOINTS         ###################
#################################################################
   
    def endpoint_help(self, stmt):
        self.do_help("endpoint")

    def endpoint_list(self,stmt):
        print("Current endpoints in workspace:")
        endpoints = self.workspace.getEndpoints()
        if not endpoints:
            print("No endpoints in current workspace")
            return
        for endpoint in endpoints:
            print(endpoint.toList())
    
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
    parser_endpoint_help = subparser_endpoint.add_parser("help",help='Show endpoint help')
    parser_endpoint_list = subparser_endpoint.add_parser("list",help='List endpoints')
    parser_endpoint_add = subparser_endpoint.add_parser("add",help='Add a new endpoint')
    parser_endpoint_add.add_argument('ip',help='New endpoint ip')
    parser_endpoint_add.add_argument('port',help='New endpoint port', type=int, default=22, nargs='?')

    parser_endpoint_help.set_defaults(func=endpoint_help)
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
            # No subcommand was provided, so call help
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
        for user in users:
            print(user.toList())
    
    def user_add(self,stmt):
        name = vars(stmt)['name']
        try:
            self.workspace.addUser_Manual(name)
        except Exception as e:
            print("User addition failed: "+str(e))
        else:
            print("User "+name+" added.")

    def user_help(self,stmt):
        self.do_help("user")

    parser_user = argparse.ArgumentParser(prog="user")
    subparser_user = parser_user.add_subparsers(title='Actions',help='Available actions')
    parser_user_help = subparser_user.add_parser("help",help='Show user help')
    parser_user_list = subparser_user.add_parser("list",help='List users')
    parser_user_add = subparser_user.add_parser("add",help='Add a new user')
    parser_user_add.add_argument('name',help='New user name')

    parser_user_help.set_defaults(func=user_help)
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
            # No subcommand was provided, so call help
            self.user_list(None)

#################################################################
###################           CREDS           ###################
#################################################################

    def creds_types(self,stmt):
        print("Supported credential types:")
        for key in Extensions.authMethodsAvail():
            print("    - "+key+": "+Extensions.getAuthMethod(key).descr())
    
    def creds_list(self,stmt):
        creds = self.workspace.getCreds()
        if not creds:
            print("No creds in current workspace")
            return
        for cred in creds:
            print(cred.toList())

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
            self.workspace.addCreds_Manual(credsType)
        except Exception as e:
            print("Credentials addition failed: "+str(e))
        else:
            print("Credentials added.")

    def creds_help(self,stmt):
        self.do_help("creds")

    def getOptionCreds(self):
        return self.workspace.getCreds()

    parser_creds = argparse.ArgumentParser(prog="creds")
    subparser_creds = parser_creds.add_subparsers(title='Actions',help='Available actions')
    parser_creds_help = subparser_creds.add_parser("help",help='Show credentials help')
    parser_creds_list = subparser_creds.add_parser("list",help='List saved credentials')
    parser_creds_types = subparser_creds.add_parser("types",help='List available credentials types')
    parser_creds_show = subparser_creds.add_parser("show",help='Show credentials details')
    parser_creds_show.add_argument('id',help='Creds identifier',choices_method=getOptionCreds)
    parser_creds_edit = subparser_creds.add_parser("edit",help='Edit credentials details')
    parser_creds_edit.add_argument('id',help='Creds identifier',choices_method=getOptionCreds)
    parser_creds_add = subparser_creds.add_parser("add",help='Add a new credentials')
    parser_creds_add.add_argument('type',help='New credentials type',choices_function=Extensions.authMethodsAvail)

    parser_creds_help.set_defaults(func=creds_help)
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
            # No subcommand was provided, so call help
            self.creds_list(None)

#################################################################
###################          PAYLOADS         ###################
#################################################################

    def payload_list(self,stmt):
        print("Available payloads:")
        for key in Extensions.payloadsAvail():
            print("    - "+key+": "+Extensions.getPayload(key).descr())
    
    def payload_help(self,stmt):
        self.do_help("payload")

    parser_payload = argparse.ArgumentParser(prog="payload")
    subparser_payload = parser_payload.add_subparsers(title='Actions',help='Available actions')
    parser_payload_help = subparser_payload.add_parser("help",help='Show payload help')
    parser_payload_list = subparser_payload.add_parser("list",help='List payloads')

    parser_payload_help.set_defaults(func=payload_help)
    parser_payload_list.set_defaults(func=payload_list)

    @cmd2.with_argparser(parser_payload)
    def do_payload(self, stmt):
        '''Manage payloads'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            # No subcommand was provided, so call help
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
            print("No connetions in current workspace")
            return
        data = []
        for connection in connections:
            data.append([connection.getEndpoint(),connection.getUser(),connection.getCred(),connection.isTested(),connection.isWorking()])
        print(tabulate(data,headers=["Endpoint","User","Creds","Tested","Working"]))
    
    def connection_help(self,stmt):
        self.do_help("connection")

    parser_connection = argparse.ArgumentParser(prog="connection")
    subparser_connection = parser_connection.add_subparsers(title='Actions',help='Available actions')
    parser_connection_help = subparser_connection.add_parser("help",help='Show connection help')
    parser_connection_list = subparser_connection.add_parser("list",help='List connections')
    parser_connection_list.add_argument('opt',help='Filter options',nargs=argparse.REMAINDER,choices=["working","tested"])

    parser_connection_help.set_defaults(func=connection_help)
    parser_connection_list.set_defaults(func=connection_list)

    @cmd2.with_argparser(parser_connection)
    def do_connection(self, stmt):
        '''Manage connections'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            # No subcommand was provided, so call help
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

    def getOptionPayload(self):
        return Extensions.payloadsAvail()

    def getOptionValidConnection(self):
        return self.workspace.getTargetsValidList()

    def getOptionConnection(self):
        return self.workspace.getTargetsList()

    parser_option = argparse.ArgumentParser(prog="option")
    subparser_option = parser_option.add_subparsers(title='Actions',help='Available actions')
    parser_option_help = subparser_option.add_parser("help",help='Show option help')
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

    parser_option_help.set_defaults(option="help")
    parser_option_list.set_defaults(option="list")
    parser_option_user.set_defaults(option="user")
    parser_option_creds.set_defaults(option="creds")
    parser_option_endpoint.set_defaults(option="endpoint")
    parser_option_payload.set_defaults(option="payload")
    parser_option_connection.set_defaults(option="connection")

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
            elif option == "help":
                self.do_help("set")
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
            try:
                self.workspace.setOption(option,value)
            except ValueError:
                print("Invalid value for "+option)
        else:
            # No subcommand was provided, so call help
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
        for path in paths:
            print(path.toList())
    
    def path_get(self,stmt):
        endpoint = vars(stmt)['endpoint']
        self.workspace.getPathToDst(endpoint)

    def path_help(self,stmt):
        self.do_help('path')

    parser_path = argparse.ArgumentParser(prog="path")
    subparser_path = parser_path.add_subparsers(title='Actions',help='Available actions')
    parser_path_help = subparser_path.add_parser("help",help='Show path help')
    parser_path_list = subparser_path.add_parser("list",help='List paths')
    parser_path_get = subparser_path.add_parser("get",help='Get path to endpoint')
    parser_path_get.add_argument('endpoint',help='Endpoint',choices_method=getOptionEndpoint)

    parser_path_help.set_defaults(func=path_help)
    parser_path_list.set_defaults(func=path_list)
    parser_path_get.set_defaults(func=path_get)

    @cmd2.with_argparser(parser_path)
    def do_path(self, stmt):
        '''Manage paths'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            # No subcommand was provided, so call help
            self.path_list(None)



#################################################################
###################          CONNECT          ###################
#################################################################

    def parseOptionsTarget(self):
        user = self.workspace.getOption("user")
        if user is None:
            users = self.workspace.getUsers()
            if len(users) > 1:
                if not yesNo("Try with all ("+str(len(users))+") users in scope ?",False):
                    raise ValueError
            users = self.workspace.getUsers()
        else:
            users = [user]
        endpoint = self.workspace.getOption("endpoint")
        if endpoint is None:
            endpoints = self.workspace.getEndpoints()
            if len(endpoints) > 1:
                if not yesNo("Try with all ("+str(len(endpoints))+") endpoints in scope ?",False):
                    raise ValueError
            endpoints = self.workspace.getEndpoints()
        else:
            endpoints = [endpoint]
        cred = self.workspace.getOption("creds")
        if cred is None:
            creds = self.workspace.getCreds()
            if len(creds) > 1:
                if not yesNo("Try with all ("+str(len(creds))+") credentials in scope ?",False):
                    raise ValueError
            creds = self.workspace.getCreds()
        else:
            creds = [cred]
        nbIter = len(endpoints)*len(users)*len(creds)
        if nbIter > 1:
            if not yesNo("This will attempt up to "+str(nbIter)+" connections. Proceed ?",False):
                raise ValueError
        return (endpoints,users,creds)

    parser_connect = argparse.ArgumentParser(prog="connect")
    parser_connect.add_argument('connection',help='Connection string',nargs="?",choices_method=getOptionConnection)

    @cmd2.with_argparser(parser_connect)
    def do_connect(self,stmt):
        connect = vars(stmt)['connection']
        if connect != None:
            try:
                self.workspace.connectTarget(connect)
            except Exception as e:
                print("Targeted connect failed : "+str(e))
            return
        try:
            endpoints,users,creds = self.parseOptionsTarget()
        except:
            return
        for endpoint in endpoints:
            for user in users:
                for cred in creds:
                    if self.workspace.connect(endpoint,user,cred):
                        break;

    parser_run = argparse.ArgumentParser(prog="run")
    parser_run.add_argument('connection',help='Connection string',nargs="?",choices_method=getOptionConnection)
    parser_run.add_argument('payload',help='Payload name',nargs="?",choices_method=getOptionPayload)

    @cmd2.with_argparser(parser_run)
    def do_run(self,stmt):
        connect = vars(stmt)['connection']
        payload = vars(stmt)['payload']
        self._reset_completion_defaults()
        if connect != None and payload != None:
            try:
                self.workspace.runTarget(connect,payload)
            except Exception as e:
                print("Run failed : "+str(e))
            return
        payload = self.workspace.getOption("payload")
        if payload is None:
            print("Error : No payload specified")
            return
        try:
            endpoints,users,creds = self.parseOptionsTarget()
        except:
            return
        for endpoint in endpoints:
            for user in users:
                for cred in creds:
                    if self.workspace.run(endpoint,user,cred,payload):
                        break;

#################################################################
###################            CMD            ###################
#################################################################

    def do_exit(self, arg):
        'Quit Baboossh'
        self.workspace.close()
        print("Bye !")
        return True
    
    def initPrompt(self):
        newPrompt = ""
        newPrompt = newPrompt+"["+self.workspace.getName()+"]"
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
            newPrompt = newPrompt+"("+str(self.workspace.getOption("payload"))+")"
        self.prompt = newPrompt+"> "

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
    Extensions.load()
    
    if not os.path.exists(config['DEFAULT']['workspaces']):
        print("> First run ? Creating workspaces directory")
        os.makedirs(config['DEFAULT']['workspaces'])

    #Create default workspace if not exists
    if not os.path.exists(os.path.join(config['DEFAULT']['workspaces'],'default')):
        Workspace.create('default')

    BaboosshShell().cmdloop()

