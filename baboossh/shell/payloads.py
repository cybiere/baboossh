import argparse

import tabulate
import cmd2

from baboossh.extensions import Extensions
from baboossh.shell.helpers import CMD_CAT_WSP


class PayloadsCommands:
    """`Shell` commands for listing available payloads."""

    def __payload_list(self, stmt: argparse.Namespace | None) -> None:
        print("Available payloads:")
        data = []
        for key in Extensions.payloads:
            data.append([key, Extensions.payloads[key].descr()])
        print(tabulate.tabulate(data, headers=["Key", "Description"]))

    __parser_payload = cmd2.Cmd2ArgumentParser(prog="payload")
    __subparser_payload = __parser_payload.add_subparsers(title='Actions', help='Available actions')
    __parser_payload_list = __subparser_payload.add_parser("list", help='List payloads')

    __parser_payload_list.set_defaults(func=__payload_list)

    @cmd2.with_argparser(__parser_payload)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_WSP)
    def do_payload(self, stmt):
        '''List available payloads'''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__payload_list(None)
