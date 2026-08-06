from baboossh import Connection, Creds, Endpoint, User


def make_connection(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    user = User("tester")
    user.save()
    creds = Creds("password", "secret")
    creds.save()
    conn = Connection(endpoint, user, creds)
    conn.save()
    return conn


def test_connection_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("connection list")
    out = capsys.readouterr().out
    assert "No connections in current workspace" in out


def test_connection_list_shows_connection(shell, capsys):
    make_connection()
    shell.onecmd_plus_hooks("connection list")
    out = capsys.readouterr().out
    assert "1.2.3.4:22" in out
    assert "tester" in out


def test_connection_close_no_arg_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("connection close")
    out = capsys.readouterr().out
    assert "No connection specified" in out


def test_connection_close_never_opened_closes_cleanly(shell, capsys):
    conn = make_connection()
    shell.onecmd_plus_hooks(f"connection close tester:#{conn.creds.id}@1.2.3.4:22")
    # should not raise


def test_connection_delete_removes_connection(shell, capsys):
    conn = make_connection()
    shell.onecmd_plus_hooks(f"connection delete tester:#{conn.creds.id}@1.2.3.4:22")
    assert Connection.find_all() == []
