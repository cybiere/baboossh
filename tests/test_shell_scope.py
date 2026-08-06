from baboossh import User


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def test_scope_toggles_object(shell, capsys):
    make_user()
    shell.onecmd_plus_hooks("scope tester")
    assert User.find_one(name="tester").scope is False


def test_scope_unknown_target_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("scope doesnotexist")
    out = capsys.readouterr().out
    assert "Could not identify object" in out
