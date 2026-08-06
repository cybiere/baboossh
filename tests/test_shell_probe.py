from unittest.mock import MagicMock

from baboossh import Connection, Endpoint


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def test_probe_dispatches_to_workspace_probe(shell, monkeypatch, capsys):
    make_endpoint()
    monkeypatch.setattr(Connection, "probe", MagicMock(return_value=True))
    shell.onecmd_plus_hooks("probe 1.2.3.4:22")
    out = capsys.readouterr().out
    assert "OK" in out


def test_probe_new_and_gateway_together_rejected(shell, capsys):
    shell.onecmd_plus_hooks("probe -n -g local 1.2.3.4:22")
    out = capsys.readouterr().out
    assert "cannot use both" in out
