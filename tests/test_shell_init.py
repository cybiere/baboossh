from baboossh import Host


def test_store_lists_stored_objects(shell, capsys):
    shell.onecmd_plus_hooks("store")
    out = capsys.readouterr().out
    assert "Connection" in out
    assert "Host" in out


def test_exit_closes_workspace_and_returns_true(shell, capsys):
    result = shell.onecmd_plus_hooks("exit")
    out = capsys.readouterr().out
    assert "Bye" in out
    assert result is True


def test_eof_closes_workspace_and_returns_true(shell, capsys):
    result = shell.do__eof("")
    out = capsys.readouterr().out
    assert "Bye" in out
    assert result is True


def test_postcmd_refreshes_prompt(shell):
    host = Host("h1", "uname", "issue", "machineid", [])
    host.save()
    shell.workspace.options["user"] = None
    shell.postcmd(False, "host list")
    assert "[default]" in shell.prompt
