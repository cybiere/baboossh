from unittest.mock import MagicMock

from baboossh import Connection, Creds, Endpoint, User


def make_endpoint(ip="1.2.3.4", port="22", reachable=False):
    endpoint = Endpoint(ip, port)
    endpoint.reachable = reachable
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


def make_connection(reachable=False):
    endpoint = make_endpoint(reachable=reachable)
    return Connection(endpoint, make_user(), make_creds())


def test_connect_unreachable_no_probe_auto_reports_error_and_skips(workspace, capsys):
    conn = make_connection(reachable=False)
    result = workspace.connect([conn], probe_auto=False)
    assert result == 0
    assert "Error" in capsys.readouterr().out


def test_connect_unreachable_probe_auto_calls_probe_then_retries(workspace, monkeypatch):
    conn = make_connection(reachable=False)

    def fake_probe(targets, verbose=False):
        conn.endpoint.reachable = True

    monkeypatch.setattr(workspace, "probe", fake_probe)
    monkeypatch.setattr(Connection, "open", lambda self, verbose=False, target=False: True)
    result = workspace.connect([conn], probe_auto=True)
    assert result == 1


def test_connect_reachable_calls_connection_open_and_counts_success(workspace, monkeypatch):
    conn = make_connection(reachable=True)
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=True))
    result = workspace.connect([conn])
    assert result == 1


def test_connect_reachable_open_fails_not_counted(workspace, monkeypatch):
    conn = make_connection(reachable=True)
    monkeypatch.setattr(Connection, "open", MagicMock(return_value=False))
    result = workspace.connect([conn])
    assert result == 0


def test_run_calls_connection_run_for_each_reachable_target(workspace, monkeypatch):
    conn = make_connection(reachable=True)
    mock_run = MagicMock()
    monkeypatch.setattr(Connection, "run", mock_run)
    workspace.run([conn], payload="fake_payload", stmt="fake_stmt")
    mock_run.assert_called_once_with("fake_payload", workspace.workspace_folder, "fake_stmt", verbose=False)
