import os
import re
import shutil
import argparse
from typing import TYPE_CHECKING, Protocol

import cmd2

from baboossh.utils import WORKSPACES_DIR
from baboossh.workspace import Workspace
from baboossh.shell.helpers import CMD_CAT_WSP, get_arg_workspaces

if TYPE_CHECKING:
    class _Shell(Protocol):
        workspace: Workspace


class WorkspaceCommands:
    """`Shell` commands for creating, listing, using and deleting workspaces."""

    def __workspace_list(self: "_Shell", stmt: argparse.Namespace) -> None:
        print("Existing workspaces :")
        workspaces = [name for name in os.listdir(WORKSPACES_DIR) if os.path.isdir(os.path.join(WORKSPACES_DIR, name))]
        for workspace in workspaces:
            if workspace == self.workspace.name:
                print(" -["+workspace+"]")
            else:
                print(" - "+workspace)

    def __workspace_add(self: "_Shell", stmt: argparse.Namespace) -> None:
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

    def __workspace_use(self: "_Shell", stmt: argparse.Namespace) -> None:
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

    def __workspace_del(self: "_Shell", stmt: argparse.Namespace) -> None:
        from baboossh.shell import yes_no
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

    __parser_wspace = cmd2.Cmd2ArgumentParser(prog="workspace")
    __subparser_wspace = __parser_wspace.add_subparsers(title='Actions', help='Available actions')
    __parser_wspace_list = __subparser_wspace.add_parser("list", help='List workspaces')
    __parser_wspace_add = __subparser_wspace.add_parser("add", help='Add a new workspace')
    __parser_wspace_add.add_argument('name', help='New workspace name')
    __parser_wspace_use = __subparser_wspace.add_parser("use", help='Change current workspace')
    __parser_wspace_use.add_argument('name', help='Name of workspace to use', choices_provider=get_arg_workspaces)
    __parser_wspace_del = __subparser_wspace.add_parser("delete", help='Delete workspace')
    __parser_wspace_del.add_argument('name', help='Name of workspace to delete', choices_provider=get_arg_workspaces)

    __parser_wspace_list.set_defaults(func=__workspace_list)
    __parser_wspace_add.set_defaults(func=__workspace_add)
    __parser_wspace_use.set_defaults(func=__workspace_use)
    __parser_wspace_del.set_defaults(func=__workspace_del)

    @cmd2.with_argparser(__parser_wspace)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_WSP)
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
