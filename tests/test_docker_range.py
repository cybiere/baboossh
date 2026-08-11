"""Integration tests against the live SSH range in tests/docker/.

Opt-in only — run with `uv run pytest --run-docker tests/test_docker_range.py`.
See tests/docker/README.md for the range's topology and credentials, which
the constants below match exactly.
"""

import argparse
import json
from pathlib import Path

import pytest
from paramiko.ssh_exception import IncompatiblePeer

from baboossh import Connection, Creds, Endpoint, Extensions, Path as BPath, User
from baboossh.exceptions import NoPathError

pytestmark = pytest.mark.docker

KEYS_DIR = Path(__file__).parent / "docker" / "keys"
PRIVKEY_PATH = KEYS_DIR / "test_id_ed25519"
PASSWORD = "baboossh-test"

IP_A, IP_B, IP_C, IP_D, IP_E = "10.10.0.2", "10.10.0.3", "10.10.1.4", "10.10.2.2", "10.10.0.4"


def _privkey_creds():
    content = json.dumps({"passphrase": "", "keypath": str(PRIVKEY_PATH), "haspass": False})
    creds = Creds("privkey", content)
    creds.save()
    return creds


def test_identify_systemd_host(docker_workspace):
    ws = docker_workspace
    user = User("tester")
    user.save()
    ep = Endpoint(IP_A, "22")
    ep.save()
    creds = Creds("password", PASSWORD)
    creds.save()

    ws.probe([ep], gateway="auto", verbose=False)
    assert ep.reachable is True

    conn = Connection(ep, user, creds)
    assert ws.connect([conn], verbose=False) == 1
    assert ep.host is not None
    assert len(ep.host.machine_id) == 32
    int(ep.host.machine_id, 16)  # a real machine-id is a hex UUID with no dashes


def test_identify_absent_machine_id_is_empty(docker_workspace):
    ws = docker_workspace
    user = User("tester")
    user.save()
    ep = Endpoint(IP_B, "22")
    ep.save()
    creds = _privkey_creds()

    ws.probe([ep], gateway="auto", verbose=False)
    conn = Connection(ep, user, creds)
    ws.connect([conn], verbose=False)

    assert ep.host is not None
    assert ep.host.machine_id in (None, "")


def test_pivot_through_gateway_to_c(docker_workspace):
    ws = docker_workspace
    user = User("tester")
    user.save()
    creds = _privkey_creds()

    ep_b = Endpoint(IP_B, "22")
    ep_b.save()
    ws.probe([ep_b], gateway="auto", verbose=False)
    conn_b = Connection(ep_b, user, creds)
    assert ws.connect([conn_b], verbose=False) == 1

    ep_c = Endpoint(IP_C, "22")
    ep_c.save()
    ws.probe([ep_c], gateway="auto", verbose=False)
    assert ep_c.reachable is True  # reached via B as gateway

    conn_c = Connection(ep_c, user, creds)
    assert ws.connect([conn_c], verbose=False) == 1
    assert ep_c.host is not None
    assert ep_c.host.name == "c-openssh-devuan"


def test_nopatherror_against_unreachable_host(docker_workspace):
    ep_d = Endpoint(IP_D, "22")
    ep_d.save()
    with pytest.raises(NoPathError):
        BPath.get(ep_d)


def test_incompatible_ssh_server_fails_cleanly(docker_workspace):
    # probe() only catches TimeoutError/OSError/ConnectionRefusedError (see
    # baboossh/connection.py); a cipher mismatch raises paramiko's own
    # IncompatiblePeer instead of returning False. It's still a specific,
    # clear exception rather than a hang or a generic failure, but it is
    # NOT caught anywhere in baboossh itself — see todo.md.
    ws = docker_workspace
    ep_e = Endpoint(IP_E, "22")
    ep_e.save()

    with pytest.raises(IncompatiblePeer):
        ws.probe([ep_e], gateway="auto", verbose=False)
    assert ep_e.reachable is not True


def test_payload_exec_against_live_target(docker_workspace, capsys):
    ws = docker_workspace
    user = User("tester")
    user.save()
    ep = Endpoint(IP_A, "22")
    ep.save()
    creds = Creds("password", PASSWORD)
    creds.save()

    ws.probe([ep], gateway="auto", verbose=False)
    conn = Connection(ep, user, creds)
    assert ws.connect([conn], verbose=False) == 1

    payload = Extensions.payloads["exec"]
    stmt = argparse.Namespace(cmd=["hostname"])
    ws.run([conn], payload, stmt, verbose=False)

    captured = capsys.readouterr()
    assert "a-openssh-debian" in captured.out
