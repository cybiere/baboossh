import tabulate
import cmd2

from baboossh.extensions import Extensions
from baboossh.shell.helpers import CMD_CAT_WSP


class ExportsCommands:
    """`Shell` command for exporting workspace info."""

    __parser_export = cmd2.Cmd2ArgumentParser(prog="export")
    __subparser_export = __parser_export.add_subparsers(title='Actions', help='Available exporters')
    __parser_method = __subparser_export.add_parser('list', help='List available exporters')
    for __key in Extensions.exports:
        __export = Extensions.exports[__key]
        __parser_method = __subparser_export.add_parser(__key, help=__export.descr())
        __parser_method.set_defaults(exporter=__key)
        __export.buildParser(__parser_method)

    @cmd2.with_argparser(__parser_export)  # pyright: ignore[reportArgumentType]  # self isn't cmd2.Cmd on a mixin, see plan
    @cmd2.with_category(CMD_CAT_WSP)
    def do_export(self, stmt):
        '''Export workspace info'''
        key = getattr(stmt, 'exporter', 'list')
        if key == 'list':
            print("Available exporters:")
            data = []
            for key in Extensions.exports:
                data.append([key, Extensions.exports[key].descr()])
            print(tabulate.tabulate(data, headers=["Key", "Description"]))
            return
        try:
            exporter = Extensions.exports[key]
        except Exception as exc:
            print("Error: "+str(exc))
            return
        exporter.run(stmt, self.workspace)  # pyright: ignore[reportAttributeAccessIssue]  # self isn't _Shell on a mixin, see plan
