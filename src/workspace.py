import os
import re
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
if "DEFAULT" not in config or "workspaces" not in config['DEFAULT']:
    print("Invalid config file")
    exit()


class Workspace():
    @classmethod
    def create(cls,name):
        if name == "":
            print("Cannot use workspace with empty name")
            raise ValueError
        if re.match('^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        workspaceFolder = os.path.join(config['DEFAULT']['workspaces'],name)
        if not os.path.exists(workspaceFolder):
            try:
                os.mkdir(workspaceFolder)
            except OSError:
                print ("Creation of the directory %s failed" % workspaceFolder)
                raise OSError
            print("Workspace "+name+" created")
        else:
            print("Workspace already exists")
            raise ValueError
        return Workspace(name)

    def __init__(self,name):
        if name == "":
            print("Cannot use workspace with empty name")
            raise ValueError
        if re.match('^[\w_\.-]+$', name) is None:
            print('Invalid characters in workspace name. Allowed characters are letters, numbers and ._-')
            raise ValueError
        workspaceFolder = os.path.join(config['DEFAULT']['workspaces'],name)
        if not os.path.exists(workspaceFolder):
            print("Workspace "+name+" does not exist")
            raise ValueError
        self.name = name

    def getName(self):
        return self.name

    def close(self):
        print("Closing workspace "+self.name)


