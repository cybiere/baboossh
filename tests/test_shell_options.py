from baboossh import Creds, Endpoint, User


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def make_creds(content="secret"):
    creds = Creds("password", content)
    creds.save()
    return creds


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def test_set_no_args_lists_options(shell, capsys):
    shell.onecmd_plus_hooks("set")
    out = capsys.readouterr().out
    assert "Current options" in out


def test_set_list_lists_options(shell, capsys):
    shell.onecmd_plus_hooks("set list")
    out = capsys.readouterr().out
    assert "Current options" in out


def test_set_user(shell, capsys):
    make_user()
    shell.onecmd_plus_hooks("set user tester")
    assert str(shell.workspace.options["user"]) == "tester"


def test_set_creds(shell, capsys):
    creds = make_creds()
    shell.onecmd_plus_hooks(f"set creds #{creds.id}")
    assert shell.workspace.options["creds"] == creds


def test_set_endpoint(shell, capsys):
    endpoint = make_endpoint()
    shell.onecmd_plus_hooks("set endpoint 1.2.3.4:22")
    assert shell.workspace.options["endpoint"] == endpoint


def test_set_payload(shell, capsys):
    shell.onecmd_plus_hooks("set payload exec")
    assert shell.workspace.options["payload"] is not None


def test_set_params(shell, capsys):
    shell.onecmd_plus_hooks("set params foo bar")
    assert shell.workspace.options["params"] == "foo bar"


def test_set_invalid_value_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("set user doesnotexist")
    out = capsys.readouterr().out
    assert "Invalid value for user" in out
