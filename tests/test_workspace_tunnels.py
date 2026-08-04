from baboossh import Connection


class FakeTunnel:
    def __init__(self, connection, port):
        self.connection = connection
        self.port = port if port is not None else 4242
        self.closed = False

    def close(self):
        self.closed = True


class RaisingTunnel:
    def __init__(self, connection, port):
        raise RuntimeError("boom")


def test_tunnel_open_port_already_in_use_returns_false(workspace):
    workspace.tunnels[1234] = FakeTunnel("fake_connection", 1234)
    assert workspace.tunnel_open("whatever", port=1234) is False


def test_tunnel_open_target_not_found_returns_false(workspace, monkeypatch):
    monkeypatch.setattr(Connection, "from_target", staticmethod(lambda target: None))
    assert workspace.tunnel_open("whatever") is False


def test_tunnel_open_success_registers_tunnel(workspace, monkeypatch):
    monkeypatch.setattr(Connection, "from_target", staticmethod(lambda target: "fake_connection"))
    monkeypatch.setattr("baboossh.workspace.tunnels.Tunnel", FakeTunnel)
    assert workspace.tunnel_open("whatever", port=9999) is True
    assert 9999 in workspace.tunnels
    assert isinstance(workspace.tunnels[9999], FakeTunnel)


def test_tunnel_open_tunnel_construction_raises_returns_false(workspace, monkeypatch, capsys):
    monkeypatch.setattr(Connection, "from_target", staticmethod(lambda target: "fake_connection"))
    monkeypatch.setattr("baboossh.workspace.tunnels.Tunnel", RaisingTunnel)
    assert workspace.tunnel_open("whatever") is False
    assert "Error opening tunnel" in capsys.readouterr().out
    assert workspace.tunnels == {}


def test_tunnel_close_unknown_port_prints_message(workspace, capsys):
    result = workspace.tunnel_close(1234)
    assert result is None
    assert "No tunnel on port" in capsys.readouterr().out


def test_tunnel_close_removes_tunnel_and_calls_close(workspace):
    tun = FakeTunnel("fake_connection", 1234)
    workspace.tunnels[1234] = tun
    workspace.tunnel_close(1234)
    assert 1234 not in workspace.tunnels
    assert tun.closed is True


def test_tunnel_close_close_raises_exception_still_removed_from_dict(workspace, capsys):
    class BrokenTunnel(FakeTunnel):
        def close(self):
            raise RuntimeError("boom")

    tun = BrokenTunnel("fake_connection", 1234)
    workspace.tunnels[1234] = tun
    workspace.tunnel_close(1234)
    assert 1234 not in workspace.tunnels
    assert "Error closing tunnel" in capsys.readouterr().out
