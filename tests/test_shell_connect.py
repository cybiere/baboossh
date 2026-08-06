from unittest.mock import MagicMock

from baboossh import Connection, Creds, Endpoint, User


def make_connection(ip="1.2.3.4", port="22", reachable=True):
    endpoint = Endpoint(ip, port)
    endpoint.reachable = reachable
    endpoint.save()
    user = User("tester")
    user.save()
    creds = Creds("password", "secret")
    creds.save()
    conn = Connection(endpoint, user, creds)
    conn.save()
    return conn


def test_connect_dispatches_to_workspace_connect(shell, monkeypatch, capsys):
    conn = make_connection()
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=True))
    shell.onecmd_plus_hooks(f"connect tester:#{conn.creds.id}@1.2.3.4:22")
    out = capsys.readouterr().out
    assert "1/1" in out


def test_connect_no_targets_reports_zero_working(shell, capsys):
    shell.onecmd_plus_hooks("connect")
    out = capsys.readouterr().out
    assert "0/0" in out


def test_run_no_targets_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("run *:*@* exec hostname")
    out = capsys.readouterr().out
    assert "No valid targets found" in out


def test_run_dispatches_to_workspace_run(shell, monkeypatch, capsys):
    conn = make_connection()
    mock_run = MagicMock()
    monkeypatch.setattr(Connection, "run", mock_run)
    shell.onecmd_plus_hooks(f"run tester:#{conn.creds.id}@1.2.3.4:22 exec hostname")
    mock_run.assert_called_once()
