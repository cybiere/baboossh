import pytest

from baboossh import Workspace


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr("baboossh.utils.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.db.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.workspace.WORKSPACES_DIR", str(tmp_path))
    ws = Workspace.create("testws")
    yield ws
    ws.close()
