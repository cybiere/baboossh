import argparse

import cmd2

from baboossh.extensions import Extensions
from baboossh.shell.helpers import CMD_CAT_CON, get_option_connection, get_run_targets


class ConnectCommands:
    """`Shell` commands for connecting to endpoints and running payloads."""

    __parser_connect = cmd2.Cmd2ArgumentParser(prog="connect")
    __parser_connect.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_connect.add_argument("-f", "--force", help="force connection even if already existing", action="store_true")
    __parser_connect.add_argument("-p", "--probe", help="Automatically probe the endpoint if it wasn't yet", action="store_true")
    __parser_connect.add_argument('connection', help='Connection string', nargs="?", choices_provider=get_option_connection)

    @cmd2.with_argparser(__parser_connect)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_CON)
    def do_connect(self, stmt):
        '''Try to authenticate on an Enpoint using a User and Creds'''
        from baboossh.shell import yes_no
        connection = getattr(stmt, 'connection', None)
        verbose = getattr(stmt, 'verbose', False)
        force = getattr(stmt, 'force', False)
        probe_auto = getattr(stmt, 'probe', False)

        targets = self.workspace.enum_connect(connection, force=force, unprobed=probe_auto)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
        nb_targets = len(targets)
        if nb_targets > 1:
            if not yes_no("This will attempt up to "+str(nb_targets)+" connections. Proceed ?", False, list_val=targets):
                return

        nb_working = self.workspace.connect(targets, verbose, probe_auto)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
        print("\033[1;32m"+str(nb_working)+"/"+str(nb_targets)+"\033[0m working.")


    __parser_run = cmd2.Cmd2ArgumentParser(prog="run")
    __parser_run.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_run.add_argument('connection', help='Connection string', nargs="?", choices_provider=get_run_targets)
    __subparser_run = __parser_run.add_subparsers(title='Actions', help='Available actions')
    for __payloadName in Extensions.payloads:
        __payload = Extensions.payloads[__payloadName]
        __parser_payload = __subparser_run.add_parser(__payloadName, help=__payload.descr())
        __parser_payload.set_defaults(type=__payloadName)
        __payload.buildParser(__parser_payload)

    @cmd2.with_argparser(__parser_run)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_CON)
    def do_run(self, stmt):
        '''Run a payload on a connection'''
        from baboossh.shell import yes_no
        connection = getattr(stmt, 'connection', None)
        payload = getattr(stmt, 'type', None)
        verbose = getattr(stmt, 'verbose', False)

        if payload is not None:
            payload = Extensions.payloads[payload]
        else:
            payload = self.workspace.options["payload"]  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
            if payload is None:
                print("Error : No payload specified")
                return
            params = self.workspace.options["params"]  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
            __parser = argparse.ArgumentParser(description='Params __parser')
            payload.buildParser(__parser)
            if params is None:
                params = ""
            stmt, junk = __parser.parse_known_args(params.split())

        targets = self.workspace.enum_run(connection)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
        nb_targets = len(targets)
        if nb_targets == 0:
            print("No valid targets found.")
            return
        if nb_targets > 1:
            if not yes_no("The payload will be run on "+str(nb_targets)+" connections. Proceed ?", False, list_val=targets):
                return

        self.workspace.run(targets, payload, stmt, verbose=verbose)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
