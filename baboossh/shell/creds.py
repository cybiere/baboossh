import tabulate
import cmd2
from baboossh.extensions import Extensions
from baboossh.shell.helpers import CMD_CAT_OBJ, get_option_creds


class CredsCommands:
    """`Shell` commands for creating, listing, showing, editing and deleting credentials."""

    def __creds_types(self, stmt):
        print("Supported credential types:")
        data = []
        for key in Extensions.auths:
            data.append([key, Extensions.auths[key].descr()])
        print(tabulate.tabulate(data, headers=["Key", "Description"]))

    def __creds_list(self, stmt):
        show_all = getattr(stmt, 'all', False)
        creds = self.workspace.get_objects(creds=True, scope=None if show_all else True)
        if not creds:
            print("No creds in current workspace")
            return
        data = []
        for cred in creds:
            scope = "o" if cred.scope else ""
            data.append([scope, "#"+str(cred.id), cred.obj.getKey(), cred.obj.toList()])
        print(tabulate.tabulate(data, headers=["", "ID", "Type", "Value"]))

    def __creds_show(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.creds_show(creds_id)

    def __creds_edit(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.creds_edit(creds_id)

    def __creds_del(self, stmt):
        creds_id = vars(stmt)['id']
        self.workspace.creds_del(creds_id)

    def __creds_add(self, stmt):
        creds_type = vars(stmt)['type']
        try:
            creds_id = self.workspace.creds_add(creds_type, stmt)
        except Exception as exc:
            print("Credentials addition failed: "+str(exc))
        else:
            print("Credentials #"+str(creds_id)+" added.")

    __parser_creds = cmd2.Cmd2ArgumentParser(prog="creds")
    __subparser_creds = __parser_creds.add_subparsers(title='Actions', help='Available actions')
    __parser_creds_list = __subparser_creds.add_parser("list", help='List saved credentials')
    __parser_creds_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_creds_types = __subparser_creds.add_parser("types", help='List available credentials types')
    __parser_creds_show = __subparser_creds.add_parser("show", help='Show credentials details')
    __parser_creds_show.add_argument('id', help='Creds identifier', choices_provider=get_option_creds)
    __parser_creds_edit = __subparser_creds.add_parser("edit", help='Edit credentials details')
    __parser_creds_edit.add_argument('id', help='Creds identifier', choices_provider=get_option_creds)
    __parser_creds_add = __subparser_creds.add_parser("add", help='Add new credentials')
    __subparser_creds_add = __parser_creds_add.add_subparsers(title='Add creds', help='Available creds types')
    for __methodName in Extensions.auths:
        __method = Extensions.auths[__methodName]
        __parser_method = __subparser_creds_add.add_parser(__methodName, help=__method.descr())
        __parser_method.set_defaults(type=__methodName)
        __method.buildParser(__parser_method)
    __parser_creds_del = __subparser_creds.add_parser("delete", help='Delete credentials from workspace')
    __parser_creds_del.add_argument('id', help='Creds identifier', choices_provider=get_option_creds)

    __parser_creds_list.set_defaults(func=__creds_list)
    __parser_creds_types.set_defaults(func=__creds_types)
    __parser_creds_show.set_defaults(func=__creds_show)
    __parser_creds_edit.set_defaults(func=__creds_edit)
    __parser_creds_add.set_defaults(func=__creds_add)
    __parser_creds_del.set_defaults(func=__creds_del)

    @cmd2.with_argparser(__parser_creds)
    @cmd2.with_category(CMD_CAT_OBJ)
    def do_creds(self, stmt):
        '''Create, list, edit and delete credentials.

        Credentials are secrets used to authenticate. They can be of different
        types (see "creds types" to list supported types) and are used with "set"
        and "connect".

        The creds object provides a unified interface for the underlying types.
        '''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__creds_list(stmt)
