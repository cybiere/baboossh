import argparse
from typing import TYPE_CHECKING, Protocol

import tabulate
import cmd2

from baboossh.shell.helpers import CMD_CAT_OBJ, get_tag

if TYPE_CHECKING:
    from baboossh.workspace import Workspace

    class _Shell(Protocol):
        workspace: Workspace


class TagsCommands:
    """`Shell` commands for listing, showing and deleting tags."""

    def __tag_list(self: "_Shell", stmt: argparse.Namespace) -> None:
        print("Current tags in workspace:")
        tags = self.workspace.get_objects(tags=True)
        if not tags:
            print("No tags in current workspace")
            return
        data = []
        for tag in tags:
            data.append([tag])
        print(tabulate.tabulate(data, headers=["Tag name"]))

    def __tag_show(self: "_Shell", stmt: argparse.Namespace) -> None:
        name = vars(stmt)['tagname']
        self.workspace.tag_show(name)

    def __tag_del(self: "_Shell", stmt: argparse.Namespace) -> None:
        name = vars(stmt)['tagname']
        self.workspace.tag_del(name)

    __parser_tag = cmd2.Cmd2ArgumentParser(prog="tag")
    __subparser_tag = __parser_tag.add_subparsers(title='Actions', help='Available actions')
    __parser_tag_list = __subparser_tag.add_parser("list", help='List tags')
    __parser_tag_show = __subparser_tag.add_parser("show", help='Show endpoints with tag')
    __parser_tag_show.add_argument('tagname', help='Tag name', choices_provider=get_tag)
    __parser_tag_del = __subparser_tag.add_parser("delete", help='Delete tag')
    __parser_tag_del.add_argument('tagname', help='Tag name', choices_provider=get_tag)

    __parser_tag_list.set_defaults(func=__tag_list)
    __parser_tag_show.set_defaults(func=__tag_show)
    __parser_tag_del.set_defaults(func=__tag_del)

    @cmd2.with_argparser(__parser_tag)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_OBJ)
    def do_tag(self, stmt):
        '''Manage tags'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__tag_list(stmt)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
