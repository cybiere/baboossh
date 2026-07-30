import pytest

from baboossh import Workspace
from baboossh.utils import is_workspace_compat
from baboossh.version import BABOOSSH_VERSION


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr("baboossh.utils.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.db.WORKSPACES_DIR", str(tmp_path))
    monkeypatch.setattr("baboossh.workspace.WORKSPACES_DIR", str(tmp_path))
    yield tmp_path


def test_create_empty_name_raises(isolated_dirs):
    with pytest.raises(ValueError):
        Workspace.create("")


def test_create_invalid_characters_raises(isolated_dirs):
    with pytest.raises(ValueError):
        Workspace.create("not a valid name!")


def test_create_duplicate_raises(isolated_dirs):
    ws = Workspace.create("dupws")
    try:
        with pytest.raises(ValueError):
            Workspace.create("dupws")
    finally:
        ws.close()


def test_create_sets_active_workspace(isolated_dirs):
    ws = Workspace.create("activews")
    try:
        assert Workspace.active is ws
    finally:
        ws.close()


def test_close_clears_active_workspace(isolated_dirs):
    ws = Workspace.create("closews")
    ws.close()
    assert Workspace.active is None


def test_init_missing_workspace_raises(isolated_dirs):
    with pytest.raises(ValueError):
        Workspace("doesnotexist")


def test_is_workspace_compat_matches_current_version():
    assert is_workspace_compat(BABOOSSH_VERSION) is True


def test_is_workspace_compat_rejects_different_major():
    assert is_workspace_compat("999.0.0") is False


def test_is_workspace_compat_accepts_same_major_minor_different_patch():
    major, minor, _patch = BABOOSSH_VERSION.split(".")
    other_patch_version = f"{major}.{minor}.999"
    assert is_workspace_compat(other_patch_version) is True
