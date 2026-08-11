from unittest.mock import MagicMock

import paramiko
from paramiko import ssh_exception
import pytest

from baboossh import Connection, Creds, Endpoint, Host, User
from baboossh.connection import DIRECT_TIMEOUT, RELAY_TIMEOUT
from baboossh.exceptions import ConnectionClosedError, NoHostError


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def make_creds(content="secret"):
    creds = Creds("password", content)
    creds.save()
    return creds


def make_connection(endpoint=None, user=None, creds=None):
    endpoint = endpoint or make_endpoint()
    user = user or make_user()
    creds = creds or make_creds()
    conn = Connection(endpoint, user, creds)
    conn.save()
    return conn


def make_host(name="h1"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    return host


# --- pure DB/logic ---

def test_get_id_is_stable_and_content_based(workspace):
    endpoint = make_endpoint()
    user = make_user()
    creds = make_creds()
    conn1_id = Connection.get_id(endpoint, user, creds)
    conn2_id = Connection.get_id(endpoint, user, creds)
    assert conn1_id == conn2_id


def test_save_then_find_one_by_id(workspace):
    conn = make_connection()
    found = Connection.find_one(connection_id=conn.id)
    assert found == conn


def test_delete_removes_connection(workspace):
    conn = make_connection()
    conn.delete()
    assert Connection.find_all() == []


def test_find_all_filters_by_user(workspace):
    user1 = make_user(name="alice")
    user2 = make_user(name="bob")
    creds = make_creds()
    conn1 = make_connection(user=user1, creds=creds)
    make_connection(endpoint=make_endpoint(ip="2.2.2.2"), user=user2, creds=creds)
    result = Connection.find_all(user=user1)
    assert result == [conn1]


def test_from_target_full_string_resolves_connection(workspace):
    creds = make_creds()
    make_user()
    make_endpoint()
    result = Connection.from_target(f"tester:#{creds.id}@1.2.3.4:22")
    assert result is not None
    assert result.user is not None and result.user.name == "tester"


def test_from_target_unknown_endpoint_raises_valueerror(workspace):
    make_user()
    make_creds()
    with pytest.raises(ValueError):
        Connection.from_target("tester:#1@1.2.3.4:22")


def test_scope_false_when_user_or_creds_missing(workspace):
    endpoint = make_endpoint()
    conn = Connection(endpoint, None, None)
    assert conn.scope is False


# --- open_transport ---

def test_open_transport_direct_constructs_transport(workspace, monkeypatch):
    conn = make_connection()
    fake_sock = MagicMock()
    monkeypatch.setattr("baboossh.connection.socket.socket", MagicMock(return_value=fake_sock))
    fake_transport = MagicMock()
    monkeypatch.setattr("baboossh.connection.paramiko.Transport", MagicMock(return_value=fake_transport))

    sock, transport, gateway = conn.open_transport(gateway=None)

    assert sock is fake_sock
    assert transport is fake_transport
    assert gateway is None
    fake_transport.start_client.assert_called_once()


def test_open_transport_via_gateway_uses_gateway_channel(workspace, monkeypatch):
    conn = make_connection()
    gateway_conn = make_connection(endpoint=make_endpoint(ip="9.9.9.9"))
    gateway_conn.transport = MagicMock()
    fake_channel = MagicMock()
    gateway_conn.transport.open_channel.return_value = fake_channel
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=True))
    fake_transport = MagicMock()
    monkeypatch.setattr("baboossh.connection.paramiko.Transport", MagicMock(return_value=fake_transport))

    sock, transport, gateway = conn.open_transport(gateway=gateway_conn)

    assert sock is fake_channel
    assert gateway is gateway_conn
    gateway_conn.transport.open_channel.assert_called_once()


def test_open_transport_via_gateway_passes_relay_timeout(workspace, monkeypatch):
    """A gateway-relayed channel-open must be bounded by RELAY_TIMEOUT, since
    paramiko's own default (channel_timeout, 1 hour) leaves it unbounded when a
    target is filtered/dropped rather than actively refused."""
    conn = make_connection()
    gateway_conn = make_connection(endpoint=make_endpoint(ip="9.9.9.9"))
    gateway_conn.transport = MagicMock()
    fake_channel = MagicMock()
    gateway_conn.transport.open_channel.return_value = fake_channel
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=True))
    fake_transport = MagicMock()
    monkeypatch.setattr("baboossh.connection.paramiko.Transport", MagicMock(return_value=fake_transport))

    conn.open_transport(gateway=gateway_conn)

    _, kwargs = gateway_conn.transport.open_channel.call_args
    assert kwargs["timeout"] == RELAY_TIMEOUT


def test_open_transport_direct_passes_direct_timeout(workspace, monkeypatch):
    conn = make_connection()
    fake_sock = MagicMock()
    monkeypatch.setattr("baboossh.connection.socket.socket", MagicMock(return_value=fake_sock))
    monkeypatch.setattr("baboossh.connection.paramiko.Transport", MagicMock(return_value=MagicMock()))

    conn.open_transport(gateway=None)

    fake_sock.settimeout.assert_called_once_with(DIRECT_TIMEOUT)


def test_open_transport_gateway_fails_to_open_raises_connectionclosederror(workspace, monkeypatch):
    conn = make_connection()
    gateway_conn = make_connection(endpoint=make_endpoint(ip="9.9.9.9"))
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=False))

    with pytest.raises(ConnectionClosedError):
        conn.open_transport(gateway=gateway_conn)


def test_open_transport_closes_socket_on_handshake_failure(workspace, monkeypatch):
    """Regression: a socket/channel opened by open_transport() was never closed if
    paramiko.Transport's handshake (start_client()) failed - e.g. an incompatible peer -
    leaking the underlying connection instead of cleaning it up before re-raising."""
    conn = make_connection()
    fake_sock = MagicMock()
    monkeypatch.setattr("baboossh.connection.socket.socket", MagicMock(return_value=fake_sock))
    fake_transport = MagicMock()
    fake_transport.start_client.side_effect = paramiko.SSHException("incompatible peer")
    monkeypatch.setattr("baboossh.connection.paramiko.Transport", MagicMock(return_value=fake_transport))

    with pytest.raises(paramiko.SSHException):
        conn.open_transport(gateway=None)

    fake_sock.close.assert_called_once()


# --- probe() ---

def test_probe_success_marks_endpoint_reachable(workspace, monkeypatch):
    conn = make_connection()
    fake_transport = MagicMock()
    monkeypatch.setattr(Connection, "open_transport", lambda self, gateway=None: (MagicMock(), fake_transport, None))
    assert conn.probe(gateway=None) is True
    assert conn.endpoint.reachable is True


def test_probe_timeout_returns_false(workspace, monkeypatch):
    conn = make_connection()
    def raise_timeout(self, gateway=None):
        raise TimeoutError
    monkeypatch.setattr(Connection, "open_transport", raise_timeout)
    assert conn.probe(gateway=None) is False


def test_probe_gateway_connectionclosederror_returns_false_not_uncaught(workspace, monkeypatch):
    """Regression: probe() previously didn't catch ConnectionClosedError from a failed gateway open."""
    conn = make_connection()
    def raise_closed(self, gateway=None):
        raise ConnectionClosedError("gateway is down")
    monkeypatch.setattr(Connection, "open_transport", raise_closed)
    assert conn.probe(gateway=None) is False


def test_probe_incompatible_peer_returns_false(workspace, monkeypatch):
    """Regression: probe() previously didn't catch paramiko.SSHException (e.g.
    IncompatiblePeer, raised against a ChaCha20-only server) - it propagated as an
    uncaught traceback instead of a clean False like every other connection failure."""
    conn = make_connection()
    def raise_incompatible(self, gateway=None):
        raise ssh_exception.IncompatiblePeer("no matching cipher")
    monkeypatch.setattr(Connection, "open_transport", raise_incompatible)
    assert conn.probe(gateway=None) is False


def test_probe_via_gateway_with_unknown_distance_does_not_crash(workspace, monkeypatch):
    """Regression: gateway.endpoint.distance can be None if the gateway was connected-to
    but never itself probed (e.g. via `connect`); probe() through it previously crashed
    with TypeError on `None + 1` instead of leaving the target's distance unset."""
    conn = make_connection()
    gateway_conn = make_connection(endpoint=make_endpoint(ip="9.9.9.9"))
    gateway_conn.endpoint.distance = None
    fake_transport = MagicMock()
    monkeypatch.setattr(Connection, "open_transport", lambda self, gateway=None: (MagicMock(), fake_transport, gateway_conn))
    assert conn.probe(gateway=gateway_conn) is True
    assert conn.endpoint.distance is None


# --- open() ---

def test_open_already_active_returns_true(workspace):
    conn = make_connection()
    fake_transport = MagicMock()
    fake_transport.is_active.return_value = True
    conn.transport = fake_transport
    assert conn.open() is True


def test_open_bad_auth_type_returns_false(workspace, monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(Connection, "open_transport", lambda self, gateway="auto": (MagicMock(), MagicMock(), None))
    conn.creds.auth = MagicMock(side_effect=paramiko.BadAuthenticationType("nope", []))
    assert conn.open(target=True) is False


def test_open_authentication_exception_returns_false(workspace, monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(Connection, "open_transport", lambda self, gateway="auto": (MagicMock(), MagicMock(), None))
    conn.creds.auth = MagicMock(side_effect=paramiko.AuthenticationException("nope"))
    assert conn.open(target=True) is False


def test_open_ssh_exception_returns_false_with_clean_message(workspace, monkeypatch, capsys):
    conn = make_connection()
    monkeypatch.setattr(Connection, "open_transport", lambda self, gateway="auto": (MagicMock(), MagicMock(), None))
    conn.creds.auth = MagicMock(side_effect=paramiko.SSHException("boom"))
    assert conn.open(target=True) is False
    out = capsys.readouterr().out
    assert "Network error: boom" in out
    assert "Network error:  boom" not in out  # regression: no doubled space


def test_open_incompatible_peer_during_transport_returns_false(workspace, monkeypatch, capsys):
    """Regression: open()'s open_transport() call previously didn't catch
    paramiko.SSHException (e.g. IncompatiblePeer) - only the later auth-phase call did -
    so connecting to a ChaCha20-only server crashed with an uncaught traceback."""
    conn = make_connection()
    def raise_incompatible(self, gateway="auto"):
        raise ssh_exception.IncompatiblePeer("no matching cipher")
    monkeypatch.setattr(Connection, "open_transport", raise_incompatible)
    assert conn.open(target=True) is False
    assert "Network error:" in capsys.readouterr().out


def test_open_success_saves_connection_and_sets_transport(workspace, monkeypatch):
    conn = make_connection()
    fake_sock = MagicMock()
    fake_transport = MagicMock()
    monkeypatch.setattr(Connection, "open_transport", lambda self, gateway="auto": (fake_sock, fake_transport, None))
    conn.creds.auth = MagicMock(return_value=True)
    assert conn.open() is True
    assert conn.transport is fake_transport
    assert conn.sock is fake_sock
    assert conn.id is not None
    assert Connection.find_one(connection_id=conn.id) == conn


def test_open_gateway_with_unidentified_host_raises_nohosterror(workspace, monkeypatch):
    conn = make_connection()
    gateway_conn = make_connection(endpoint=make_endpoint(ip="9.9.9.9"))
    monkeypatch.setattr(Connection, "open_transport", lambda self, gateway="auto": (MagicMock(), MagicMock(), gateway_conn))
    conn.creds.auth = MagicMock(return_value=True)
    with pytest.raises(NoHostError):
        conn.open()


# --- exec_command() ---

def test_exec_command_closed_connection_raises_connectionclosederror(workspace):
    conn = make_connection()
    with pytest.raises(ConnectionClosedError):
        conn.exec_command("hostname")


def test_exec_command_drains_all_output_chunks(workspace):
    """Regression: previously only a single 1024-byte recv() was read, truncating longer output."""
    conn = make_connection()
    transport = MagicMock()
    chan = MagicMock()
    transport.open_session.return_value = chan
    conn.transport = transport

    remaining = {"n": 3}
    def recv_ready_side_effect():
        return remaining["n"] > 0
    def recv_side_effect(size):
        remaining["n"] -= 1
        return [b"hello ", b"world ", b"!"][2 - remaining["n"]]
    chan.recv_ready.side_effect = recv_ready_side_effect
    chan.recv.side_effect = recv_side_effect
    chan.exit_status_ready.return_value = True
    chan.recv_exit_status.return_value = 0

    code, output = conn.exec_command("echo hi")

    assert output == "hello world !"
    assert code == 0
    chan.get_pty.assert_called_once()
    chan.exec_command.assert_called_once_with("echo hi")


def test_exec_command_calls_recv_exit_status_only_once_and_after_ready(workspace):
    """Regression: recv_exit_status() (blocking) must only be called once the exit status
    is already known ready via non-blocking polling, not before draining output."""
    conn = make_connection()
    transport = MagicMock()
    chan = MagicMock()
    transport.open_session.return_value = chan
    conn.transport = transport

    chan.recv_ready.return_value = False
    chan.exit_status_ready.return_value = True
    chan.recv_exit_status.return_value = 42

    code, output = conn.exec_command("false")

    assert code == 42
    chan.recv_exit_status.assert_called_once()


# --- identify() ---

def test_identify_hostname_failure_falls_back_to_host_init_naming(workspace):
    """Regression: identify() used to compute a fallback name via Host.getNextId() and then
    discard it, constructing Host() with an empty hostname anyway. Confirm the resulting
    Host still gets a sane generated name (via Host.__init__'s own fallback)."""
    conn = make_connection()
    conn.transport = MagicMock()
    conn.transport.get_remote_server_key.return_value.asbytes.return_value = b"key"

    def fake_exec_command(command):
        if command == "hostname":
            return (1, "")  # non-zero exit: hostname command failed
        return (0, "")
    conn.exec_command = fake_exec_command

    assert conn.identify() is True
    assert conn.endpoint.host is not None
    assert conn.endpoint.host.name.startswith("host")


def test_identify_success_creates_host(workspace):
    conn = make_connection()
    conn.transport = MagicMock()
    conn.transport.get_remote_server_key.return_value.asbytes.return_value = b"key"

    responses = {
        "hostname": (0, "myhost"),
        "uname -a": (0, "Linux myhost 6.0"),
        "cat /etc/issue": (0, "Debian"),
        "cat /etc/machine-id": (0, "abc123"),
    }
    def fake_exec_command(command):
        for key, value in responses.items():
            if command.startswith(key):
                return value
        return (0, "")
    conn.exec_command = fake_exec_command

    assert conn.identify() is True
    assert conn.endpoint.host is not None
    assert conn.endpoint.host.name == "myhost"


# --- close() ---

def test_close_never_opened_is_a_no_op(workspace):
    conn = make_connection()
    conn.close()  # transport is None, should just return


def test_close_with_transport_but_no_sock_does_not_raise(workspace, capsys):
    """Regression: close() used to `assert self.sock is not None`, crashing if a transport
    was set without a matching sock. It should now close gracefully and still print."""
    conn = make_connection()
    conn.transport = MagicMock()
    conn.sock = None
    conn.close()
    assert conn.transport is None
    out = capsys.readouterr().out
    assert "Closed" in out


def test_close_with_transport_and_sock_closes_both(workspace):
    conn = make_connection()
    conn.transport = MagicMock()
    fake_sock = MagicMock()
    conn.sock = fake_sock
    conn.close()
    assert conn.transport is None
    assert conn.sock is None
    fake_sock.close.assert_called_once()


def test_close_with_open_tunnels_refuses_to_close(workspace, capsys):
    conn = make_connection()
    conn.transport = MagicMock()
    conn.used_by_tunnels = [object()]
    conn.close()
    assert conn.transport is not None


# --- run() ---

def test_run_dispatches_payload_when_open_succeeds(workspace, monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=True))
    payload = MagicMock()
    assert conn.run(payload, "/tmp/workspace", "stmt") is True
    payload.run.assert_called_once_with(conn, "/tmp/workspace", "stmt")


def test_run_returns_false_when_open_fails(workspace, monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=False))
    payload = MagicMock()
    assert conn.run(payload, "/tmp/workspace", "stmt") is False
    payload.run.assert_not_called()


def test_run_propagates_payload_exception(workspace, monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=True))
    payload = MagicMock()
    payload.run.side_effect = RuntimeError("payload crashed")
    with pytest.raises(RuntimeError):
        conn.run(payload, "/tmp/workspace", "stmt")
