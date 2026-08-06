def test_workspace_list_shows_current_and_others(shell, capsys):
    shell.onecmd_plus_hooks("workspace list")
    out = capsys.readouterr().out
    assert "-[default]" in out


def test_workspace_add_creates_and_switches(shell, capsys):
    shell.onecmd_plus_hooks("workspace add extra")
    assert shell.workspace.name == "extra"


def test_workspace_add_invalid_name_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("workspace add 'bad name!'")
    out = capsys.readouterr().out
    assert "Invalid characters" in out
    assert shell.workspace.name == "default"


def test_workspace_use_switches_workspace(shell, capsys):
    shell.onecmd_plus_hooks("workspace add extra")
    shell.onecmd_plus_hooks("workspace use default")
    assert shell.workspace.name == "default"


def test_workspace_use_unknown_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("workspace use doesnotexist")
    out = capsys.readouterr().out
    assert "does not exist" in out


def test_workspace_del_current_workspace_refused(shell, capsys):
    shell.onecmd_plus_hooks("workspace delete default")
    out = capsys.readouterr().out
    assert "Cannot delete current workspace" in out


def test_workspace_del_confirmed_removes_workspace(shell, monkeypatch, capsys):
    shell.onecmd_plus_hooks("workspace add extra")
    shell.onecmd_plus_hooks("workspace use default")
    monkeypatch.setattr("baboossh.shell.yes_no", lambda *a, **kw: True)
    shell.onecmd_plus_hooks("workspace delete extra")
    out = capsys.readouterr().out
    assert "Workspace deleted" in out


def test_workspace_del_declined_keeps_workspace(shell, monkeypatch, capsys):
    shell.onecmd_plus_hooks("workspace add extra")
    shell.onecmd_plus_hooks("workspace use default")
    monkeypatch.setattr("baboossh.shell.yes_no", lambda *a, **kw: False)
    shell.onecmd_plus_hooks("workspace delete extra")
    shell.onecmd_plus_hooks("workspace use extra")
    assert shell.workspace.name == "extra"
