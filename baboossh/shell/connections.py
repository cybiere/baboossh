import tabulate
import cmd2
from baboossh.shell.helpers import CMD_CAT_OBJ, get_option_connection


class ConnectionsCommands:
    """`Shell` commands for listing, closing and deleting working connections."""

    def __connection_list(self, stmt):
        print("Available connections:")
        show_all = getattr(stmt, 'all', False)
        connections = self.workspace.get_objects(connections=True, scope=None if show_all else True)
        if not connections:
            print("No connections in current workspace")
            return True
        data = []
        for connection in connections:
            if not show_all:
                if not connection.scope:
                    continue
            data.append([connection.endpoint, connection.user, connection.creds, "o" if connection.transport is not None else ""])
        print(tabulate.tabulate(data, headers=["Endpoint", "User", "Creds", "Open"]))
        return True

    def __connection_close(self, stmt):
        connection = getattr(stmt, "connection", None)
        return self.workspace.connection_close(connection)


    def __connection_del(self, stmt):
        connection = getattr(stmt, "connection", None)
        return self.workspace.connection_del(connection)

    __parser_connection = cmd2.Cmd2ArgumentParser(prog="connection")
    __subparser_connection = __parser_connection.add_subparsers(title='Actions', help='Available actions')
    __parser_connection_list = __subparser_connection.add_parser("list", help='List connections')
    __parser_connection_list.add_argument("-a", "--all", help="Show out of scope objects", action="store_true")
    __parser_connection_close = __subparser_connection.add_parser("close", help='Close connection')
    __parser_connection_close.add_argument('connection', help='Connection string', nargs="?", choices_provider=get_option_connection)
    __parser_connection_del = __subparser_connection.add_parser("delete", help='Delete connection')
    __parser_connection_del.add_argument('connection', help='Connection string', choices_provider=get_option_connection)

    __parser_connection_list.set_defaults(func=__connection_list)
    __parser_connection_close.set_defaults(func=__connection_close)
    __parser_connection_del.set_defaults(func=__connection_del)

    @cmd2.with_argparser(__parser_connection)
    @cmd2.with_category(CMD_CAT_OBJ)
    def do_connection(self, stmt):
        '''List and delete working connections.

        A connection object is saved whenever a user and a creds object work on
        an endpoint, as tested by the "connect" command. Once the object is
        created, it can be used with "set" and "run" to run payloads.
        '''
        func = getattr(stmt, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, stmt)
        else:
            self.__connection_list(stmt)
