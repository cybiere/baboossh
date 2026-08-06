import argparse
from typing import TYPE_CHECKING, Protocol, cast

import tabulate
import cmd2

from baboossh import User
from baboossh.shell.helpers import CMD_CAT_OBJ, get_option_user

if TYPE_CHECKING:
    from baboossh.workspace import Workspace

    class _Shell(Protocol):
        workspace: Workspace


class UsersCommands:
    """`Shell` commands for creating, listing and deleting users."""

    def __user_list(self: "_Shell", stmt: argparse.Namespace) -> None:
        print("Current users in workspace:")
        show_all = getattr(stmt, 'all', False)
        users = cast("list[User]", self.workspace.get_objects(users=True, scope=None if show_all else True))
        if not users:
            print("No users in current workspace")
            return
        data = []
        for user in users:
            scope = "o" if user.scope else ""
            data.append([scope, user])
        print(tabulate.tabulate(data, headers=["", "Username"]))

    def __user_add(self: "_Shell", stmt: argparse.Namespace) -> None:
        name = vars(stmt)['name']
        try:
            self.workspace.user_add(name)
        except Exception as exc:
            print("User addition failed: "+str(exc))
        else:
            print("User "+name+" added.")

    def __user_del(self: "_Shell", stmt: argparse.Namespace) -> None:
        name = vars(stmt)['name']
        self.workspace.user_del(name)

    __parser_user = cmd2.Cmd2ArgumentParser(prog="user")
    __subparser_user = __parser_user.add_subparsers(title='Actions', help='Available actions')
    __parser_user_list = __subparser_user.add_parser("list", help='List users')
    __parser_user_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_user_add = __subparser_user.add_parser("add", help='Add a new user')
    __parser_user_add.add_argument('name', help='New user name')
    __parser_user_del = __subparser_user.add_parser("delete", help='Delete a user')
    __parser_user_del.add_argument('name', help='User name', choices_provider=get_option_user)

    __parser_user_list.set_defaults(func=__user_list)
    __parser_user_add.set_defaults(func=__user_add)
    __parser_user_del.set_defaults(func=__user_del)

    @cmd2.with_argparser(__parser_user)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_OBJ)
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
            self.__user_list(stmt)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
