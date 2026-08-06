import argparse
from typing import TYPE_CHECKING, Protocol, cast

import tabulate
import cmd2

from baboossh import Endpoint
from baboossh.shell.helpers import (
    CMD_CAT_OBJ,
    get_option_endpoint,
    get_option_endpoint_tag,
    get_search_fields_endpoint,
    get_tag,
)

if TYPE_CHECKING:
    from baboossh.workspace import Workspace

    class _Shell(Protocol):
        workspace: Workspace


class EndpointsCommands:
    """`Shell` commands for creating, listing, searching, tagging and deleting endpoints."""

    @staticmethod
    def __endpoint_print(endpoints: "list[Endpoint]") -> None:
        data = []
        for endpoint in endpoints:
            scope = "o" if endpoint.scope else ""
            conn = endpoint.connection
            if conn is None:
                conn = ""
            host = endpoint.host
            if host is None:
                host = ""
            if endpoint.reachable is None:
                reachable = "?"
            else:
                reachable = str(endpoint.reachable)
            if endpoint.distance is None:
                distance = ""
            else:
                distance = str(endpoint.distance)
            first = True
            taglist = ""
            for tag in endpoint.tags:
                taglist = taglist + ("!"+tag if first else ", !"+tag)
                first = False

            data.append([scope, endpoint, host, reachable, distance, conn, taglist])
        print(tabulate.tabulate(data, headers=["", "Endpoint", "Host", "Reachable", "Dist", "Working connection", "Tags"]))

    def __endpoint_list(self: "_Shell", stmt: argparse.Namespace) -> None:
        print("Current endpoints in workspace:")
        show_all = getattr(stmt, 'all', False)
        reachable = getattr(stmt, 'reachable', None)
        conn = getattr(stmt, 'conn', None)
        endpoints = cast("list[Endpoint]", self.workspace.get_objects(endpoints=True, scope=None if show_all else True))
        if not endpoints:
            print("No endpoints in current workspace")
            return

        endpoint_list = []
        for endpoint in endpoints:
            if reachable is not None:
                flag_reachable = reachable == "true"
                if endpoint.reachable != flag_reachable:
                    continue
            if conn is not None:
                flag_conn = conn == "true"
                if (endpoint.connection is None) == flag_conn:
                    continue
            endpoint_list.append(endpoint)
        EndpointsCommands.__endpoint_print(endpoint_list)

    def __endpoint_add(self: "_Shell", stmt: argparse.Namespace) -> None:
        ip_add = vars(stmt)['ip']
        port = str(vars(stmt)['port'])
        try:
            self.workspace.endpoint_add(ip_add, port)
        except Exception as exc:
            print("Endpoint addition failed: "+str(exc))
        else:
            print("Endpoint "+ip_add+":"+port+" added.")

    def __endpoint_del(self: "_Shell", stmt: argparse.Namespace) -> None:
        endpoint = vars(stmt)['endpoint']
        self.workspace.endpoint_del(endpoint)

    def __endpoint_tag(self: "_Shell", stmt: argparse.Namespace) -> None:
        endpoint = vars(stmt)['endpoint']
        tagname = vars(stmt)['tagname']
        self.workspace.endpoint_tag(endpoint, tagname)

    def __endpoint_untag(self: "_Shell", stmt: argparse.Namespace) -> None:
        endpoint = vars(stmt)['endpoint']
        tagname = vars(stmt)['tagname']
        self.workspace.endpoint_untag(endpoint, tagname)


    def __endpoint_search(self: "_Shell", stmt: argparse.Namespace) -> None:
        show_all = getattr(stmt, 'all', False)
        tag = getattr(stmt, 'tag', None)
        field = vars(stmt)['field']
        allowed_fields = get_search_fields_endpoint(self)
        if field not in allowed_fields:
            print("Invalid field specified, use one of "+str(allowed_fields)+".")
            return
        val = vars(stmt)['val']
        endpoints = self.workspace.endpoint_search(field, val, show_all, add_tag=tag)
        print("Search result for endpoints:")
        if not endpoints:
            print("No results")
            return
        EndpointsCommands.__endpoint_print(endpoints)


    __parser_endpoint = cmd2.Cmd2ArgumentParser(prog="endpoint")
    __subparser_endpoint = __parser_endpoint.add_subparsers(title='Actions', help='Available actions')
    __parser_endpoint_list = __subparser_endpoint.add_parser("list", help='List endpoints')
    __parser_endpoint_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_endpoint_list.add_argument("-r", "--reachable", help="Show only reachable endpoints", nargs='?', choices=["true", "false"], const="true")
    __parser_endpoint_list.add_argument("-c", "--conn", help="Show only endpoints with connection", nargs='?', choices=["true", "false"], const="true")
    __parser_endpoint_add = __subparser_endpoint.add_parser("add", help='Add a new endpoint')
    __parser_endpoint_add.add_argument('ip', help='New endpoint ip')
    __parser_endpoint_add.add_argument('port', help='New endpoint port', type=int, default=22, nargs='?')
    __parser_endpoint_search = __subparser_endpoint.add_parser("search", help='Search an endpoint')
    __parser_endpoint_search.add_argument("-a", "--all", help="Include out of scope elements in search", action="store_true")
    __parser_endpoint_search.add_argument('field', help='Field to search in', choices_provider=get_search_fields_endpoint)
    __parser_endpoint_search.add_argument('val', help='Value to search')
    __parser_endpoint_search.add_argument("-t", "--tag", help="Add tag to search results", choices_provider=get_tag)
    __parser_endpoint_del = __subparser_endpoint.add_parser("delete", help='Set target endpoint')
    __parser_endpoint_del.add_argument('endpoint', help='Endpoint', choices_provider=get_option_endpoint_tag)
    __parser_endpoint_tag = __subparser_endpoint.add_parser("tag", help='Tag an endpoint')
    __parser_endpoint_tag.add_argument('endpoint', help='Endpoint', choices_provider=get_option_endpoint)
    __parser_endpoint_tag.add_argument('tagname', help='The tag name to add', choices_provider=get_tag)
    __parser_endpoint_untag = __subparser_endpoint.add_parser("untag", help='Tag an endpoint')
    __parser_endpoint_untag.add_argument('endpoint', help='Endpoint', choices_provider=get_option_endpoint)
    __parser_endpoint_untag.add_argument('tagname', help='The tag name to add', choices_provider=get_tag)

    __parser_endpoint_list.set_defaults(func=__endpoint_list)
    __parser_endpoint_add.set_defaults(func=__endpoint_add)
    __parser_endpoint_search.set_defaults(func=__endpoint_search)
    __parser_endpoint_del.set_defaults(func=__endpoint_del)
    __parser_endpoint_tag.set_defaults(func=__endpoint_tag)
    __parser_endpoint_untag.set_defaults(func=__endpoint_untag)

    @cmd2.with_argparser(__parser_endpoint)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_OBJ)
    def do_endpoint(self, stmt):
        '''Create, list, search and delete endpoints.

        An endpoint is a couple of an IP and a port on which a SSH service
        should be running. Once added, an endpoint must be reached using "probe"
        and then connected using "connect".
        '''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__endpoint_list(stmt)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
