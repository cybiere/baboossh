import argparse
from typing import TYPE_CHECKING, Protocol, cast

import tabulate
import cmd2

from baboossh import Path
from baboossh.shell.helpers import CMD_CAT_OBJ, get_endpoint_or_host, get_host_or_local, get_option_endpoint

if TYPE_CHECKING:
    from baboossh.workspace import Workspace

    class _Shell(Protocol):
        workspace: Workspace


class PathsCommands:
    """`Shell` commands for listing, adding, getting and deleting paths."""

    def __path_list(self: "_Shell", stmt: argparse.Namespace) -> None:
        print("Current paths in workspace:")
        show_all = getattr(stmt, 'all', False)
        paths = cast("list[Path]", self.workspace.get_objects(paths=True))
        if not paths:
            print("No paths in current workspace")
            return
        data = []
        for path in paths:
            if not path.scope and not show_all:
                continue
            src: object = path.src
            if src is None:
                src = "Local"
            data.append([src, path.dst])
        print(tabulate.tabulate(data, headers=["Source", "Destination"]))

    def __path_get(self: "_Shell", stmt: argparse.Namespace) -> None:
        endpoint = vars(stmt)['endpoint']
        as_ip = getattr(stmt, "numeric", False)
        self.workspace.path_find_existing(endpoint, as_ip)

    def __path_add(self: "_Shell", stmt: argparse.Namespace) -> None:
        src = vars(stmt)['src']
        dst = vars(stmt)['dst']
        self.workspace.path_add(src, dst)

    def __path_del(self: "_Shell", stmt: argparse.Namespace) -> None:
        src = vars(stmt)['src']
        dst = vars(stmt)['dst']
        self.workspace.path_del(src, dst)

    __parser_path = cmd2.Cmd2ArgumentParser(prog="path")
    __subparser_path = __parser_path.add_subparsers(title='Actions', help='Available actions')
    __parser_path_list = __subparser_path.add_parser("list", help='List paths')
    __parser_path_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_path_get = __subparser_path.add_parser("get", help='Get path to endpoint')
    __parser_path_get.add_argument("-n", "--numeric", help="Show Endpoint instead of Host", action="store_true")
    __parser_path_get.add_argument('endpoint', help='Endpoint', choices_provider=get_endpoint_or_host)
    __parser_path_add = __subparser_path.add_parser("add", help='Add path to endpoint')
    __parser_path_add.add_argument('src', help='Source host', choices_provider=get_host_or_local)
    __parser_path_add.add_argument('dst', help='Destination endpoint', choices_provider=get_option_endpoint)
    __parser_path_del = __subparser_path.add_parser("delete", help='Delete path to endpoint')
    __parser_path_del.add_argument('src', help='Source host', choices_provider=get_host_or_local)
    __parser_path_del.add_argument('dst', help='Destination endpoint', choices_provider=get_option_endpoint)

    __parser_path_list.set_defaults(func=__path_list)
    __parser_path_get.set_defaults(func=__path_get)
    __parser_path_add.set_defaults(func=__path_add)
    __parser_path_del.set_defaults(func=__path_del)

    @cmd2.with_argparser(__parser_path)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_OBJ)
    def do_path(self, stmt):
        '''Manage paths'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__path_list(stmt)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
