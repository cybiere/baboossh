import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

from baboossh import Workspace

DOCKER_COMPOSE_FILE = Path(__file__).parent / "docker" / "compose.yml"

# Ports that must accept a TCP connection before the range is considered "up".
# Container D (deliberately unreachable) and C (reachable only via a pivot,
# not directly) are excluded on purpose.
DOCKER_RANGE_PORTS = [
    ("10.10.0.2", 22),  # A
    ("10.10.0.3", 22),  # B
    ("10.10.0.4", 22),  # E
]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr("baboossh.utils.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.db.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.workspace.WORKSPACES_DIR", str(tmp_path))
    ws = Workspace.create("testws")
    yield ws
    ws.close()


def pytest_addoption(parser):
    parser.addoption(
        "--run-docker",
        action="store_true",
        default=False,
        help="run tests marked 'docker' (needs Docker and builds the tests/docker/ range)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-docker"):
        return
    skip_docker = pytest.mark.skip(reason="needs --run-docker to run")
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip_docker)


@pytest.fixture(scope="session")
def docker_available():
    if shutil.which("docker") is None:
        pytest.skip("docker is not installed")
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        pytest.skip(f"docker daemon is not reachable: {exc}")


@pytest.fixture(scope="session")
def docker_range(docker_available):
    subprocess.run(
        ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "--build", "-d"],
        check=True,
    )
    try:
        deadline = time.monotonic() + 120
        for host, port in DOCKER_RANGE_PORTS:
            while True:
                try:
                    with socket.create_connection((host, port), timeout=2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(
                            f"{host}:{port} did not become reachable in time"
                        )
                    time.sleep(1)
        yield
    finally:
        subprocess.run(
            ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "down"],
            check=False,
        )


@pytest.fixture
def docker_workspace(docker_range, tmp_path, monkeypatch):
    monkeypatch.setattr("baboossh.utils.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.db.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.workspace.WORKSPACES_DIR", str(tmp_path))
    ws = Workspace.create("dockertestws")
    yield ws
    ws.close()
