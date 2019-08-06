#!/usr/bin/env python3

from src.params import Extensions
from src.workspace import Workspace
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
            self.do_help('workspace')

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
   
    def endpoint_help(self, params):
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
            self.do_help('endpoint')

#################################################################
###################           USERS           ###################
#################################################################

    def do_user(self, arg):
        '''USER: Manage users
Available commands:
    - user help                 show this help
    - user list                 list existing users
    - user add USERNAME         create new user
'''
        command,sep,params = arg.partition(" ")
        if command == "list" or command == "":
            self.user_list()
        elif command == "add":
            self.user_add(params)
        else:
            if command != "help" and command != "?":
                print("Unrecognized command.")
            self.user_help()
    
    def user_list(self):
        print("Current users in workspace:")
        users = self.workspace.getUsers()
        if not users:
            print("No users in current workspace")
            return
        for user in users:
            print(user.toList())
    
    def user_add(self,params):
        if params == "":
            self.user_help()
            return
        params = params.split(' ')
        if len(params) != 1:
            self.user_help()
            return
        name = params[0]
        try:
            self.workspace.addUser_Manual(name)
        except Exception as e:
            print("User addition failed: "+str(e))
        else:
            print("User "+name+" added.")

    def user_help(self):
        print('''Available commands:
    - user help                 show this help
    - user list                 list existing users
    - user add USERNAME         create new user''')

    def complete_user(self, text, line, begidx, endidx):
        matches = []
        n = len(text)
        for word in ['add','list','help']:
            if word[:n] == text:
                matches.append(word)
        return matches

#################################################################
###################           CREDS           ###################
#################################################################

    def do_creds(self, arg):
        '''CREDS: Manage creds
Available commands:
    - creds help                 show this help
    - creds list                 list existing creds
    - creds types                list available credential types
    - creds add TYPE             create new cred
'''
        command,sep,params = arg.partition(" ")
        if command == "list" or command == "":
            self.creds_list()
        elif command == "types":
            self.creds_types()
        elif command == "add":
            self.creds_add(params)
        else:
            if command != "help" and command != "?":
                print("Unrecognized command.")
            self.creds_help()

    def creds_types(self):
        print("Supported credential types:")
        for key in Extensions.authMethodsAvail():
            print("    - "+key+": "+Extensions.getAuthMethod(key).descr())
    
    def creds_list(self):
        creds = self.workspace.getCreds()
        if not creds:
            print("No creds in current workspace")
            return
        for cred in creds:
            print(cred.toList())

    def creds_show(self,credId):
        #TODO
        pass

    
    def creds_add(self,params):
        if params == "":
            self.creds_help()
            return
        if params not in Extensions.authMethodsAvail():
            print(params+" is not a valid credentials type.")
            return
        try:
            self.workspace.addCreds_Manual(params)
        except Exception as e:
            print("Credentials addition failed: "+str(e))
        else:
            print("Credentials added.")

    def creds_help(self):
        print('''Available commands:
    - creds help                 show this help
    - creds list                 list existing creds
    - creds types                list available credential types
    - creds add TYPE             create new cred''')

    def complete_creds(self, text, line, begidx, endidx):
        matches = []
        n = len(text)
        for word in ['add','list','types','help']:
            if word[:n] == text:
                matches.append(word)
        #TODO autocomplete creds types on ADD
        return matches


#################################################################
###################          PAYLOADS         ###################
#################################################################

    def do_payload(self, arg):
        '''PAYLOAD: Manage payload
Available commands:
    - payload help                 show this help
    - payload list                 list existing payload
'''
        command,sep,params = arg.partition(" ")
        if command == "list" or command == "":
            self.payload_list()
        else:
            if command != "help" and command != "?":
                print("Unrecognized command.")
            self.payload_help()

    def payload_list(self):
        print("Available payloads:")
        for key in Extensions.payloadsAvail():
            print("    - "+key+": "+Extensions.getPayload(key).descr())
    
    def payload_help(self):
        print('''Available commands:
    - payload help                 show this help
    - payload list                 list existing payload''')

    def complete_payload(self, text, line, begidx, endidx):
        matches = []
        n = len(text)
        for word in ['list','help']:
            if word[:n] == text:
                matches.append(word)
        return matches

#################################################################
###################          OPTIONS          ###################
#################################################################

    def do_use(self,arg):
        '''USE: Manage options
Available commands:
    - use help                 show this help
    - use                      list current options' values
    - use OPTION VALUE         change an option's value
'''
        command,sep,params = arg.partition(" ")
        if command == "":
            self.options_list()
        elif command in list(self.workspace.getOptions())+['target']:
            try:
                self.workspace.setOption(command,params)
            except ValueError:
                print("Invalid value for "+command)
        else:
            if command != "help" and command != "?":
                print("Unrecognized command.")
            self.options_help()

    def options_list(self):
        print("Current options:")
        for key,val in self.workspace.getOptionsValues():
            print("    - "+key+": "+str(val))
    
    def options_help(self):
        print('''Available commands:
    - use help                 show this help
    - use                      list current options' values
    - use OPTION VALUE         change an option's value''')

    def complete_use(self, text, line, begidx, endidx):
        matches = []
        if len(line) != endidx:
            #Complete only at the end of commands
            return []
        command = line.split()
        if len(command) < 2 or len(command) == 2 and begidx != endidx:
            compKey = "cmd"
        elif text == "":
            if command[-1] == "#":
                compKey = command[-2]
            else:
                compKey = command[-1]

        elif command[-2]:
            compKey = command[-2]
        else:
            compKey = "none"
        n = len(text)
        if compKey == "cmd":
            comp = list(self.workspace.getOptions())+['target']
        elif compKey == "endpoint":
            comp = self.workspace.getEndpointsList()
        elif compKey == "user":
            comp = self.workspace.getUsersList()
        elif compKey == "creds":
            comp = self.workspace.getCredsIdList()
        elif compKey == "target":
            comp = self.workspace.getTargetsValidList()
        elif compKey == "payload":
            comp = Extensions.payloadsAvail()
        else:
            comp = []
        for word in comp:
            if word[:n] == text:
                matches.append(word)
        return matches

#################################################################
###################           PATHS           ###################
#################################################################Q

    def do_path(self,arg):
        '''USER: Manage paths
Available commands:
    - path help                 show this help
    - path list                 list existing paths
    - path get ENDPOINT         get path to ENDPOINT
'''
        command,sep,params = arg.partition(" ")
        if command == "list" or command == "":
            self.path_list()
        elif command == "get":
            self.path_get(params)
        else:
            if command != "help" and command != "?":
                print("Unrecognized command.")
            self.path_help()
    
    def path_list(self):
        print("Current paths in workspace:")
        paths = self.workspace.getPaths()
        if not paths:
            print("No paths in current workspace")
            return
        for path in paths:
            print(path.toList())
    
    def path_get(self,params):
        if params == "":
            self.path_help()
            return
        params = params.split(' ')
        if len(params) != 1:
            self.path_help()
            return
        self.workspace.getPathToDst(params[0])

    def path_help(self):
        print('''Available commands:
    - path help                 show this help
    - path list                 list existing paths
    - path get ENDPOINT         get path to ENDPOINT''')

    def complete_path(self, text, line, begidx, endidx):
        matches = []
        if len(line) != endidx:
            #Complete only at the end of commands
            return []
        command = line.split()
        if len(command) < 2 or len(command) == 2 and begidx != endidx:
            compKey = "cmd"
        elif text == "":
            if command[-1] == "#":
                compKey = command[-2]
            else:
                compKey = command[-1]

        elif command[-2]:
            compKey = command[-2]
        else:
            compKey = "none"
        n = len(text)
        if compKey == "cmd":
            comp = ['help','list','get']
        elif compKey == "get":
            comp = self.workspace.getEndpointsList()
        else:
            comp = []
        for word in comp:
            if word[:n] == text:
                matches.append(word)
        return matches


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

    def do_connect(self,arg):
        if arg != "":
            try:
                self.workspace.connectTarget(arg)
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
                    #TODO re-enable ^C to cancel
                    if self.workspace.connect(endpoint,user,cred):
                        break;

    def complete_connect(self, text, line, begidx, endidx):
        matches = []
        n = len(text)
        for word in self.workspace.getTargetsValidList():
            if word[:n] == text:
                matches.append(word)
        return matches

    def do_run(self,arg):
        if arg != "":
            if len(arg.split()) == 2:
                target,payload = arg.split()
                try:
                    self.workspace.runTarget(target,payload)
                except Exception as e:
                    print("Run failed : "+str(e))
            else:
                #TODO print help
                pass
            return
        try:
            endpoints,users,creds = self.parseOptionsTarget()
        except:
            return
        payload = self.workspace.getOption("payload")
        if payload is None:
            raise ValueError("You must specify a payload")
        for endpoint in endpoints:
            for user in users:
                for cred in creds:
                    #TODO re-enable ^C to cancel
                    if self.workspace.run(endpoint,user,cred,payload):
                        break;

    def complete_run(self, text, line, begidx, endidx):
        matches = []
        if len(line) != endidx:
            #Complete only at the end of commands
            return []
        command = line.split()
        
        if len(command) < 2 or len(command) == 2 and begidx != endidx:
            comp = self.workspace.getTargetsValidList()
        else:
            comp = Extensions.payloadsAvail()
        n = len(text)
        for word in comp:
            if word[:n] == text:
                matches.append(word)
        return matches

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



if __name__ == '__main__':
    Extensions.load()
    
    if not os.path.exists(config['DEFAULT']['workspaces']):
        print("> First run ? Creating workspaces directory")
        os.makedirs(config['DEFAULT']['workspaces'])

    #Create default workspace if not exists
    if not os.path.exists(os.path.join(config['DEFAULT']['workspaces'],'default')):
        Workspace.create('default')

    BaboosshShell().cmdloop()

