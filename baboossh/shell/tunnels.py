import argparse
from typing import TYPE_CHECKING, Protocol

import tabulate
import cmd2

from baboossh.shell.helpers import CMD_CAT_CON, get_open_tunnels, get_run_targets

if TYPE_CHECKING:
    from baboossh.workspace import Workspace

    class _Shell(Protocol):
        workspace: Workspace


class TunnelsCommands:
    """`Shell` commands for opening, listing and closing SOCKS tunnels."""

    def __tunnel_list(self: "_Shell", stmt: argparse.Namespace | None) -> None:
        print("Current tunnels in workspace:")
        tunnels = self.workspace.tunnels.values()
        if not tunnels:
            print("No tunnels in current workspace")
            return
        data = []
        for tunnel in tunnels:
            data.append([tunnel.port, tunnel.connection])
        print(tabulate.tabulate(data, headers=["Local port", "Destination"]))

    def __tunnel_open(self: "_Shell", stmt: argparse.Namespace) -> None:
        connection_str = vars(stmt)['connection']
        port = getattr(stmt, 'port', None)
        self.workspace.tunnel_open(connection_str, port)

    def __tunnel_close(self: "_Shell", stmt: argparse.Namespace) -> None:
        port = vars(stmt)['port']
        self.workspace.tunnel_close(port)

    __parser_tunnel = cmd2.Cmd2ArgumentParser(prog="tunnel")
    __subparser_tunnel = __parser_tunnel.add_subparsers(title='Actions', help='Available actions')
    __parser_tunnel_list = __subparser_tunnel.add_parser("list", help='List tunnels')
    __parser_tunnel_open = __subparser_tunnel.add_parser("open", help='Open tunnel')
    __parser_tunnel_open.add_argument('connection', help='Connection string', choices_provider=get_run_targets)
    __parser_tunnel_open.add_argument('port', help='Tunnel entry port', type=int, nargs='?')
    __parser_tunnel_close = __subparser_tunnel.add_parser("close", help='Close tunnel')
    __parser_tunnel_close.add_argument('port', help='Tunnel entry port', type=int, choices_provider=get_open_tunnels)

    __parser_tunnel_list.set_defaults(func=__tunnel_list)
    __parser_tunnel_open.set_defaults(func=__tunnel_open)
    __parser_tunnel_close.set_defaults(func=__tunnel_close)

    @cmd2.with_argparser(__parser_tunnel)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_CON)
    def do_tunnel(self, stmt):
        '''Manage tunnels'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__tunnel_list(None)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
