import cmd2

from baboossh.shell.helpers import CMD_CAT_CON, get_option_endpoint_tag, get_option_gateway


class ProbeCommands:
    """`Shell` command for probing endpoints through pivoting."""

    __parser_probe = cmd2.Cmd2ArgumentParser(prog="probe")
    __parser_probe.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    __parser_probe.add_argument("-a", "--again", help="include already probed endpoints", action="store_true")
    __parser_probe.add_argument("-n", "--new", help="try finding new shorter path", action="store_true")
    __parser_probe.add_argument("-g", "--gateway", help="force specific gateway", choices_provider=get_option_gateway)
    __parser_probe.add_argument('target', help='Endpoint to probe', nargs="?", choices_provider=get_option_endpoint_tag)

    @cmd2.with_argparser(__parser_probe)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_CON)
    def do_probe(self, stmt):
        '''Try to reach an endpoint through pivoting, using an existing path or finding a new one'''
        from baboossh.shell import yes_no
        target = getattr(stmt, 'target', None)
        verbose = getattr(stmt, 'verbose', False)
        again = getattr(stmt, 'again', False)
        new = getattr(stmt, 'new', False)
        gateway = getattr(stmt, 'gateway', "auto")
        if gateway is None:
            gateway = "auto"

        if new and gateway != "auto":
            print("Error: You cannot use both --new and --gateway options.")
            return

        targets = self.workspace.enum_probe(target, again)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
        nb_targets = len(targets)
        if nb_targets > 1:
            if not yes_no("This will probe "+str(nb_targets)+" endpoints. Proceed ?", False, list_val=targets):
                return

        self.workspace.probe(targets, gateway, verbose, find_new=new)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
