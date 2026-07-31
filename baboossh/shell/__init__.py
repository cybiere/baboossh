"""BabooSSH interactive interface

This package contains the whole user interface for BabooSSH, extending
cmd2 and providing completion & command syntax help. It also loads the
extensions on startup.

Typical usage example:

    from baboossh.shell import Shell
    Shell().cmdloop()

`Shell`'s commands are split across mixins in this package, one per domain
(`hosts.py`, `endpoints.py`, `probe.py`, etc.), mirroring `baboossh.workspace`'s
own split — this file only keeps the shell lifecycle (this section) and the
top-level `yes_no()`/`main()` helpers.
"""

import os
import cmd2
from baboossh.utils import WORKSPACES_DIR
from baboossh.version import BABOOSSH_VERSION
from baboossh.extensions import Extensions
from baboossh.workspace import Workspace

from baboossh.shell.helpers import CMD_CAT_WSP
from baboossh.shell.workspace import WorkspaceCommands
from baboossh.shell.hosts import HostsCommands
from baboossh.shell.endpoints import EndpointsCommands
from baboossh.shell.users import UsersCommands
from baboossh.shell.creds import CredsCommands
from baboossh.shell.payloads import PayloadsCommands
from baboossh.shell.connections import ConnectionsCommands
from baboossh.shell.options import OptionsCommands
from baboossh.shell.tags import TagsCommands
from baboossh.shell.paths import PathsCommands
from baboossh.shell.probe import ProbeCommands
from baboossh.shell.connect import ConnectCommands
from baboossh.shell.tunnels import TunnelsCommands
from baboossh.shell.exports import ExportsCommands
from baboossh.shell.imports import ImportsCommands
from baboossh.shell.scope import ScopeCommands

__all__ = ["Shell", "main"]

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

class Shell(
        WorkspaceCommands,
        HostsCommands,
        EndpointsCommands,
        UsersCommands,
        CredsCommands,
        PayloadsCommands,
        ConnectionsCommands,
        OptionsCommands,
        TagsCommands,
        PathsCommands,
        ProbeCommands,
        ConnectCommands,
        TunnelsCommands,
        ExportsCommands,
        ImportsCommands,
        ScopeCommands,
        cmd2.Cmd,
    ):
    """BabooSSH Shell interface

    This class extends cmd2.Cmd to build the user interface.

    Attributes:
        intro (str): The banner printed on program start
        prompt (str): The default prompt
        workspace (Workspace): The current open baboossh.Workspace
        debug (bool): Boolean for debug output
    """

#################################################################
###################            CMD            ###################
#################################################################

    @cmd2.with_category(CMD_CAT_WSP)
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

    def do__eof(self, _):
        'Exit Baboossh on EOF (Ctrl-D or end of piped input)'

        return self.do_exit("")

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

def main():
    Shell().cmdloop()
