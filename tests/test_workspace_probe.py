from unittest.mock import MagicMock

from baboossh import Connection, Creds, Endpoint, Host, Path, User
from baboossh.exceptions import ConnectionClosedError


def make_endpoint(ip="1.2.3.4", port="22", reachable=False):
    endpoint = Endpoint(ip, port)
    endpoint.reachable = reachable
    endpoint.save()
    return endpoint


def make_host_with_endpoint(name="h1", ip="9.9.9.9", port="22"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    endpoint = Endpoint(ip, port)
    endpoint.host = host
    endpoint.distance = 1
    endpoint.save()
    return host, endpoint


def test_probe_gateway_named_unknown_host_prints_error_and_returns(workspace, capsys):
    endpoint = make_endpoint()
    workspace.probe([endpoint], gateway="doesnotexist")
    assert "unknown gateway" in capsys.readouterr().out


def test_probe_already_reachable_direct_probe_succeeds(workspace, monkeypatch):
    endpoint = make_endpoint(reachable=True)
    workspace.path_add("local", "1.2.3.4:22")
    monkeypatch.setattr(Connection, "probe", MagicMock(return_value=True))
    workspace.probe([endpoint])
    assert len(Path.find_all()) == 1


def test_probe_falls_back_to_direct_from_local_success(workspace, capsys):
    endpoint = make_endpoint(reachable=False)

    def fake_probe(self, gateway="auto", verbose=False):
        return gateway is None

    Connection.probe = fake_probe
    try:
        workspace.probe([endpoint])
    finally:
        del Connection.probe
    assert "OK" in capsys.readouterr().out
    assert len(Path.find_all()) == 1


def test_probe_falls_back_to_every_known_host_success(workspace, capsys):
    host, gateway_endpoint = make_host_with_endpoint()
    target = make_endpoint(ip="1.2.3.4", reachable=False)
    user = User("tester")
    user.save()
    creds = Creds("password", "secret")
    creds.save()
    gateway_conn = Connection(gateway_endpoint, user, creds)
    gateway_conn.save()

    call_count = {"n": 0}

    def fake_probe(self, gateway="auto", verbose=False):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return False  # direct-from-local fails
        return gateway is not None  # succeeds via the known host as gateway

    Connection.probe = fake_probe
    try:
        workspace.probe([target])
    finally:
        del Connection.probe

    out = capsys.readouterr().out
    assert "OK" in out
    assert "h1" in out
    saved = Path.find_all()
    assert len(saved) == 1
    assert saved[0].src == host


def test_probe_all_strategies_fail_no_hosts_known(workspace, capsys):
    endpoint = make_endpoint(reachable=False)
    monkeypatch_probe = MagicMock(return_value=False)
    Connection.probe = monkeypatch_probe
    try:
        workspace.probe([endpoint])
    finally:
        del Connection.probe
    assert "KO" in capsys.readouterr().out
    assert Path.find_all() == []


def test_probe_all_strategies_fail_with_known_host(workspace, capsys):
    make_host_with_endpoint()
    endpoint = make_endpoint(reachable=False)
    Connection.probe = MagicMock(return_value=False)
    try:
        workspace.probe([endpoint])
    finally:
        del Connection.probe
    assert "KO" in capsys.readouterr().out
    assert Path.find_all() == []


def test_probe_skips_host_with_no_known_gateway_connection(workspace, capsys):
    # h1 has no saved Connection to its closest_endpoint: it can't be used as a
    # gateway, and trying anyway would just repeat the already-failed direct probe.
    make_host_with_endpoint(name="h1", ip="9.9.9.9")
    target = make_endpoint(ip="1.2.3.4", reachable=False)

    call_count = {"n": 0}

    def fake_probe(self, gateway="auto", verbose=False):
        call_count["n"] += 1
        return False

    Connection.probe = fake_probe
    try:
        workspace.probe([target])
    finally:
        del Connection.probe

    # only the direct-from-local attempt should have run; h1 must be skipped
    assert call_count["n"] == 1
    assert "KO" in capsys.readouterr().out


def test_probe_skips_dead_gateway_across_bulk_endpoints(workspace, capsys):
    host, gateway_endpoint = make_host_with_endpoint(name="h1", ip="9.9.9.9")
    user = User("tester")
    user.save()
    creds = Creds("password", "secret")
    creds.save()
    gateway_conn = Connection(gateway_endpoint, user, creds)
    gateway_conn.save()

    target1 = make_endpoint(ip="1.2.3.4", reachable=False)
    target2 = make_endpoint(ip="1.2.3.5", reachable=False)

    gateway_attempts = {"n": 0}

    def fake_probe(self, gateway="auto", verbose=False):
        if gateway is not None:
            gateway_attempts["n"] += 1
        return False  # gateway itself never opens (transport stays None)

    Connection.probe = fake_probe
    try:
        workspace.probe([target1, target2])
    finally:
        del Connection.probe

    # h1 is proven dead on the first endpoint; the second endpoint must not retry it.
    assert gateway_attempts["n"] == 1
    assert Path.find_all() == []


def test_probe_gateway_connectionclosederror_prints_and_returns(workspace, capsys):
    host, gateway_endpoint = make_host_with_endpoint()
    endpoint = make_endpoint(reachable=False)

    def raising_probe(self, gateway="auto", verbose=False):
        raise ConnectionClosedError("closed")

    Connection.probe = raising_probe
    try:
        workspace.probe([endpoint], gateway="h1")
    finally:
        del Connection.probe
    assert "Error" in capsys.readouterr().out
