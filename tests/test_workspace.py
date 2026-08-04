import pytest

from baboossh import Endpoint, Host, Workspace
from baboossh.utils import is_workspace_compat
from baboossh.version import BABOOSSH_VERSION


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def make_host(name="h1"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    return host


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


def test_get_objects_local_flag_prepends_local_string(workspace):
    result = workspace.get_objects(local=True)
    assert result == ["local"]


def test_get_objects_combines_multiple_flags(workspace):
    endpoint = make_endpoint()
    host = make_host()
    result = workspace.get_objects(hosts=True, endpoints=True)
    assert host in result
    assert endpoint in result


def test_get_objects_scope_filter(workspace):
    in_scope = make_endpoint(ip="1.1.1.1")
    out_scope = make_endpoint(ip="2.2.2.2")
    out_scope.scope = False
    out_scope.save()
    result = workspace.get_objects(endpoints=True, scope=True)
    assert result == [in_scope]


def test_get_objects_tags(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    result = workspace.get_objects(tags=True)
    assert len(result) == 1
    assert str(result[0]) == "!mytag"


def test_endpoint_search_by_field(workspace):
    endpoint = make_endpoint()
    result = workspace.endpoint_search("ip", "1.2.3.4")
    assert result == [endpoint]


def test_endpoint_search_add_tag_tags_matches(workspace):
    endpoint = make_endpoint()
    workspace.endpoint_search("ip", "1.2.3.4", add_tag="mytag")
    assert "mytag" in endpoint.tags


def test_host_search_by_field(workspace):
    host = make_host()
    result = workspace.host_search("name", "h1")
    assert result == [host]


def test_host_search_add_tag_tags_all_matched_hosts_endpoints(workspace):
    host = make_host()
    endpoint = make_endpoint()
    endpoint.host = host
    endpoint.save()
    workspace.host_search("name", "h1", add_tag="mytag")
    assert "mytag" in endpoint.tags


def test_search_fields_endpoint(workspace):
    assert workspace.search_fields("Endpoint") == Endpoint.search_fields


def test_search_fields_host(workspace):
    assert workspace.search_fields("Host") == Host.search_fields


def test_search_fields_unknown_returns_empty_list(workspace):
    assert workspace.search_fields("NotAType") == []


def test_unstore_removes_matching_stored_object_and_prints(workspace, capsys):
    workspace.store["Host"]["h1"] = make_host()
    workspace.unstore({"Host": ["h1"]})
    assert "h1" not in workspace.store["Host"]
    assert "Removed" in capsys.readouterr().out


def test_unstore_missing_key_no_op(workspace, capsys):
    workspace.unstore({"Host": ["doesnotexist"]})
    assert capsys.readouterr().out == ""
