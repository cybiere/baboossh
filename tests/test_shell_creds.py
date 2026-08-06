from baboossh import Creds


def make_creds(content="secret"):
    creds = Creds("password", content)
    creds.save()
    return creds


def test_creds_types_lists_available_types(shell, capsys):
    shell.onecmd_plus_hooks("creds types")
    out = capsys.readouterr().out
    assert "password" in out


def test_creds_add_password_creates_creds(shell, capsys):
    shell.onecmd_plus_hooks("creds add password secret")
    out = capsys.readouterr().out
    assert "added" in out
    assert len(Creds.find_all()) == 1


def test_creds_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("creds list")
    out = capsys.readouterr().out
    assert "No creds in current workspace" in out


def test_creds_list_shows_creds(shell, capsys):
    make_creds()
    shell.onecmd_plus_hooks("creds list")
    out = capsys.readouterr().out
    assert "secret" in out


def test_creds_show_prints_details(shell, capsys):
    creds = make_creds()
    shell.onecmd_plus_hooks(f"creds show #{creds.id}")
    out = capsys.readouterr().out
    assert "secret" in out


def test_creds_delete_removes_creds(shell, capsys):
    creds = make_creds()
    shell.onecmd_plus_hooks(f"creds delete #{creds.id}")
    assert Creds.find_all() == []
