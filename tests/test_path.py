from baboossh import Endpoint, Host, Path


def make_host(workspace, name="h1"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    return host


def make_endpoint(workspace, ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def test_path_add_invalid_dst_format_returns_none_and_creates_no_path(workspace):
    make_host(workspace)
    result = workspace.path_add("h1", "badformat")
    assert result is None
    assert Path.find_all() == []


def test_path_add_valid_creates_path(workspace):
    make_host(workspace)
    make_endpoint(workspace)
    workspace.path_add("h1", "1.2.3.4:22")
    paths = Path.find_all()
    assert len(paths) == 1


def test_path_del_invalid_dst_format_returns_false(workspace):
    make_host(workspace)
    result = workspace.path_del("h1", "badformat")
    assert result is False


def test_path_del_removes_existing_path(workspace):
    make_host(workspace)
    make_endpoint(workspace)
    workspace.path_add("h1", "1.2.3.4:22")
    assert len(Path.find_all()) == 1
    result = workspace.path_del("h1", "1.2.3.4:22")
    assert result is True
    assert Path.find_all() == []


def test_path_find_existing_invalid_format_returns_none(workspace):
    result = workspace.path_find_existing("badformat")
    assert result is None
