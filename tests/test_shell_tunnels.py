from baboossh import Connection, Creds, Endpoint, User


class FakeTunnel:
    def __init__(self, connection, port):
        self.connection = connection
        self.port = port if port is not None else 4242

    def close(self):
        pass


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


def test_tunnel_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("tunnel list")
    out = capsys.readouterr().out
    assert "No tunnels in current workspace" in out


def test_tunnel_open_dispatches_to_workspace(shell, monkeypatch, capsys):
    conn = make_connection()
    monkeypatch.setattr("baboossh.workspace.tunnels.Tunnel", FakeTunnel)
    shell.onecmd_plus_hooks(f"tunnel open tester:#{conn.creds.id}@1.2.3.4:22 9999")
    assert 9999 in shell.workspace.tunnels


def test_tunnel_close_dispatches_to_workspace(shell, monkeypatch, capsys):
    shell.workspace.tunnels[1234] = FakeTunnel("fake_connection", 1234)
    shell.onecmd_plus_hooks("tunnel close 1234")
    assert 1234 not in shell.workspace.tunnels
