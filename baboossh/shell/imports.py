import tabulate
import cmd2
from baboossh.extensions import Extensions
from baboossh.shell.helpers import CMD_CAT_WSP


class ImportsCommands:
    """`Shell` command for importing workspace info."""

    __parser_import = cmd2.Cmd2ArgumentParser(prog="import")
    __subparser_import = __parser_import.add_subparsers(title='Actions', help='Available importers')
    __parser_method = __subparser_import.add_parser('list', help='List available importers')
    for __key in Extensions.imports:
        __importer = Extensions.imports[__key]
        __parser_method = __subparser_import.add_parser(__key, help=__importer.descr())
        __parser_method.set_defaults(importer=__key)
        __importer.buildParser(__parser_method)

    @cmd2.with_argparser(__parser_import)
    @cmd2.with_category(CMD_CAT_WSP)
    def do_import(self, stmt):
        '''Import workspace info'''
        key = getattr(stmt, 'importer', 'list')
        if key == 'list':
            print("Available importers:")
            data = []
            for key in Extensions.imports:
                data.append([key, Extensions.imports[key].descr()])
            print(tabulate.tabulate(data, headers=["Key", "Description"]))
            return
        try:
            importer = Extensions.imports[key]
        except Exception as exc:
            print("Error: "+str(exc))
            return
        importer.run(stmt, self.workspace)
