import argparse
from typing import TYPE_CHECKING, Protocol, cast

import tabulate
import cmd2

from baboossh import Host
from baboossh.shell.helpers import CMD_CAT_OBJ, get_option_host, get_search_fields_host, get_tag

if TYPE_CHECKING:
    from baboossh.workspace import Workspace

    class _Shell(Protocol):
        workspace: Workspace


class HostsCommands:
    """`Shell` commands for listing, searching, tagging and deleting hosts."""

    @staticmethod
    def __host_print(hosts: "list[Host]") -> None:
        data = []
        for host in hosts:
            endpoints = ""
            for endpoint in host.endpoints:
                if endpoints == "":
                    endpoints = str(endpoint)
                else:
                    endpoints = endpoints + ", "+str(endpoint)
            scope = "o" if host.scope else ""
            data.append([scope, host.name, host.distance, endpoints])
        print(tabulate.tabulate(data, headers=["", "Name", "Dist", "Endpoints"]))

    def __host_list(self: "_Shell", stmt: argparse.Namespace) -> None:
        print("Current hosts in workspace:")
        show_all = getattr(stmt, 'all', False)
        hosts = cast("list[Host]", self.workspace.get_objects(hosts=True, scope=None if show_all else True))
        if not hosts:
            print("No hosts in current workspace")
            return
        HostsCommands.__host_print(hosts)

    def __host_search(self: "_Shell", stmt: argparse.Namespace) -> None:
        show_all = getattr(stmt, 'all', False)
        tag = getattr(stmt, 'tag', None)
        field = vars(stmt)['field']
        allowed_fields = get_search_fields_host(self)
        if field not in allowed_fields:
            print("Invalid field specified, use one of "+str(allowed_fields)+".")
            return
        val = vars(stmt)['val']
        hosts = self.workspace.host_search(field, val, show_all, add_tag=tag)
        print("Search result for hosts:")
        if not hosts:
            print("No results")
            return
        HostsCommands.__host_print(hosts)

    def __host_del(self: "_Shell", stmt: argparse.Namespace) -> None:
        host = vars(stmt)['host']
        self.workspace.host_del(host)

    def __host_tag(self: "_Shell", stmt: argparse.Namespace) -> None:
        host = vars(stmt)['host']
        tagname = vars(stmt)['tagname']
        self.workspace.host_tag(host, tagname)

    def __host_untag(self: "_Shell", stmt: argparse.Namespace) -> None:
        host = vars(stmt)['host']
        tagname = vars(stmt)['tagname']
        self.workspace.host_untag(host, tagname)

    __parser_host = cmd2.Cmd2ArgumentParser(prog="host")
    __subparser_host = __parser_host.add_subparsers(title='Actions', help='Available actions')
    __parser_host_list = __subparser_host.add_parser("list", help='List hosts')
    __parser_host_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_host_search = __subparser_host.add_parser("search", help='Search a host')
    __parser_host_search.add_argument('field', help='Field to search in', choices_provider=get_search_fields_host)
    __parser_host_search.add_argument('val', help='Value to search')
    __parser_host_search.add_argument("-t", "--tag", help="Add tag to search results", choices_provider=get_tag)
    __parser_host_del = __subparser_host.add_parser("delete", help='Delete host')
    __parser_host_del.add_argument('host', help='Host name', choices_provider=get_option_host)
    __parser_host_tag = __subparser_host.add_parser("tag", help='Tag an host')
    __parser_host_tag.add_argument('host', help='Host', choices_provider=get_option_host)
    __parser_host_tag.add_argument('tagname', help='The tag name to add', choices_provider=get_tag)
    __parser_host_untag = __subparser_host.add_parser("untag", help='Tag an host')
    __parser_host_untag.add_argument('host', help='Host', choices_provider=get_option_host)
    __parser_host_untag.add_argument('tagname', help='The tag name to add', choices_provider=get_tag)

    __parser_host_list.set_defaults(func=__host_list)
    __parser_host_search.set_defaults(func=__host_search)
    __parser_host_del.set_defaults(func=__host_del)
    __parser_host_tag.set_defaults(func=__host_tag)
    __parser_host_untag.set_defaults(func=__host_untag)

    @cmd2.with_argparser(__parser_host)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_OBJ)
    def do_host(self, stmt):
        '''Search, list and delete hosts.

        You can list or delete hosts, and use them as pivots to force using a
        specific path. Host addition is performed automatically when you
        successfully connect to an endpoint for the first time.
        '''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__host_list(stmt)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
