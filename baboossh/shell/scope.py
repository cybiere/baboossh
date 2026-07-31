import cmd2
from baboossh.shell.helpers import CMD_CAT_WSP, get_all_objects


class ScopeCommands:
    """`Shell` command for toggling an object in/out of scope."""

    __parser_scope = cmd2.Cmd2ArgumentParser(prog="scope")
    __parser_scope.add_argument('target', help='Object to scope', choices_provider=get_all_objects)

    @cmd2.with_argparser(__parser_scope)
    @cmd2.with_category(CMD_CAT_WSP)
    def do_scope(self, stmt):
        '''Toggle object in/out of scope'''
        key = getattr(stmt, 'target', None)
        self.workspace.scope(key)
