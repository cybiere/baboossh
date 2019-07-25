#!/usr/bin/env python3

from src.workspace import Workspace

import configparser
import cmd, sys, os
import sqlite3
import re


class SshpreadShell(cmd.Cmd):
    intro = '\nWelcome to SSHpread. Type help or ? to list commands.\n'
    prompt = '> '

#################################################################
###################         WORKSPACE         ###################
#################################################################

    def do_workspace(self, arg):
        '''WORKSPACE: Manage workspaces
Available commands:
    - workspace help        show this help
    - workspace list        list existing workspaces
    - workspace add <name>  create new workspace
    - workspace use <name>  change current workspace
    - workspace del <name>  delete workspace
'''
        command,sep,params = arg.partition(" ")
        if command == "list" or command == "":
            self.workspace_list()
        elif command == "add":
            self.workspace_add(params)
        elif command == "use":
            self.workspace_use(params)
        elif command == "del":
            #TODO
            print("Del workspace")
        else:
            if command != "help" and command != "?":
                print("Unrecognized command.")
            self.workspace_help()

    def workspace_list(self):
        print("Existing workspaces :")
        workspaces = [name for name in os.listdir(config['DEFAULT']['workspaces'])
            if os.path.isdir(os.path.join(config['DEFAULT']['workspaces'], name))]
        for workspace in workspaces:
            if workspace == self.workspace.getName():
                print(" -["+workspace+"]")
            else:
                print(" - "+workspace)

    def workspace_add(self, params):
        #Check if name was given
        if params == "":
            self.workspace_help()
            return
        if re.match('^[\w_\.-]+$', params) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            return
        #Check if workspace already exists
        if os.path.exists(os.path.join(config['DEFAULT']['workspaces'],params)):
            print("Workspace already exists")
            return
        try:
            newWorkspace = Workspace.create(params)
        except:
            print("Workspace creation failed")
        else:
            self.workspace.close()
            self.workspace = newWorkspace

    def workspace_use(self,params):
        #Check if workspace already exists
        if not os.path.exists(os.path.join(config['DEFAULT']['workspaces'],params)):
            print("Workspace does not exist")
        try:
            newWorkspace = Workspace(params)
        except:
            print("Workspace change failed")
        else:
            self.workspace.close()
            self.workspace = newWorkspace

    def workspace_help(self):
        print('''Available commands:
    - workspace help        show this help
    - workspace list        list existing workspaces
    - workspace add <name>  create new workspace
    - workspace use <name>  change current workspace
    - workspace del <name>  delete workspace''')

    def complete_workspace(self, text, line, begidx, endidx):
        matches = []
        n = len(text)
        for word in ['add','list','use','del','help']:
            if word[:n] == text:
                matches.append(word)
        return matches

#################################################################
###################          TARGETS          ###################
#################################################################

    def do_target(self, arg):
        'Set target'
        print("Set target")

#################################################################
###################           USERS           ###################
#################################################################

    def do_user(self, arg):
        'Set user'
        print("Set user")

#################################################################
###################            CMD            ###################
#################################################################

    def do_exit(self, arg):
        'Quit SSHpread'
        return True
    
    def initPrompt(self):
        newPrompt = ""
        newPrompt = newPrompt+"["+self.workspace.getName()+"]"
        self.prompt = newPrompt+"> "

    def postcmd(self,stop,line):
        self.initPrompt()
        if line == "exit":
            return stop

    def __init__(self):
        super().__init__()
        self.workspace = Workspace("default")
        self.initPrompt()

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')
    if "DEFAULT" not in config or "workspaces" not in config['DEFAULT']:
        print("Invalid config file")
        exit()
    
    if not os.path.exists(config['DEFAULT']['workspaces']):
        print("> First run ? Creating workspaces directory")
        os.makedirs(config['DEFAULT']['workspaces'])

    SshpreadShell().cmdloop()
