from baboossh import User


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def test_user_add_creates_user(shell, capsys):
    shell.onecmd_plus_hooks("user add tester")
    out = capsys.readouterr().out
    assert "added" in out
    assert len(User.find_all()) == 1


def test_user_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("user list")
    out = capsys.readouterr().out
    assert "No users in current workspace" in out


def test_user_list_shows_user(shell, capsys):
    make_user()
    shell.onecmd_plus_hooks("user list")
    out = capsys.readouterr().out
    assert "tester" in out


def test_user_delete_removes_user(shell, capsys):
    make_user()
    shell.onecmd_plus_hooks("user delete tester")
    assert User.find_all() == []
