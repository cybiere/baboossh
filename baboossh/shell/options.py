import cmd2
from baboossh.shell.helpers import (
    CMD_CAT_WSP,
    get_option_creds,
    get_option_connection,
    get_option_endpoint_tag,
    get_option_payload,
    get_option_user,
)


class OptionsCommands:
    """`Shell` commands for setting the workspace's active target options."""

    def __options_list(self):
        print("Current options:")
        for key, val in self.workspace.options.items():
            print("    - "+key+": "+str(val))

    __parser_option = cmd2.Cmd2ArgumentParser(prog="option")
    __subparser_option = __parser_option.add_subparsers(title='Actions', help='Available actions')
    __parser_option_list = __subparser_option.add_parser("list", help='List options')
    __parser_option_user = __subparser_option.add_parser("user", help='Set target user')
    __parser_option_user.add_argument('username', help='User name', nargs="?", choices_provider=get_option_user)
    __parser_option_creds = __subparser_option.add_parser("creds", help='Set target creds')
    __parser_option_creds.add_argument('id', help='Creds ID', nargs="?", choices_provider=get_option_creds)
    __parser_option_endpoint = __subparser_option.add_parser("endpoint", help='Set target endpoint')
    __parser_option_endpoint.add_argument('endpoint', nargs="?", help='Endpoint', choices_provider=get_option_endpoint_tag)
    __parser_option_payload = __subparser_option.add_parser("payload", help='Set target payload')
    __parser_option_payload.add_argument('payload', nargs="?", help='Payload name', choices_provider=get_option_payload)
    __parser_option_connection = __subparser_option.add_parser("connection", help='Set target connection')
    __parser_option_connection.add_argument('connection', nargs="?", help='Connection string', choices_provider=get_option_connection)
    __parser_option_params = __subparser_option.add_parser("params", help='Set payload params')
    __parser_option_params.add_argument('params', nargs="*", help='Payload params')

    __parser_option_list.set_defaults(option="list")
    __parser_option_user.set_defaults(option="user")
    __parser_option_creds.set_defaults(option="creds")
    __parser_option_endpoint.set_defaults(option="endpoint")
    __parser_option_payload.set_defaults(option="payload")
    __parser_option_connection.set_defaults(option="connection")
    __parser_option_params.set_defaults(option="params")

    @cmd2.with_argparser(__parser_option)
    @cmd2.with_category(CMD_CAT_WSP)
    def do_set(self, stmt):
        '''Set the workspace active options.

        Once set, the options will be used when running "probe", "connect" and
        "run" without parameters to define which connections to target and
        which payload to run with which options.
        '''
        if 'option' not in vars(stmt):
            self.__options_list()
            return
        option = vars(stmt)['option']
        if option is not None:
            if option == "list":
                self.__options_list()
                return
            if option == "user":
                value = vars(stmt)['username']
            elif option == "creds":
                value = vars(stmt)['id']
            elif option == "endpoint":
                value = vars(stmt)['endpoint']
            elif option == "payload":
                value = vars(stmt)['payload']
            elif option == "connection":
                value = vars(stmt)['connection']
            elif option == "params":
                value = " ".join(vars(stmt)['params'])
            try:
                self.workspace.set_option(option, value)
            except (ValueError, IndexError, KeyError):
                print("Invalid value for "+option)

        else:
            self.__options_list()
