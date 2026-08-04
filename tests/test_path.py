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


def test_path_find_existing_unknown_host_name_returns_none(workspace):
    result = workspace.path_find_existing("doesnotexist")
    assert result is None


def make_pivoted_chain(workspace):
    h1 = make_host(workspace, name="h1")
    e1 = make_endpoint(workspace, ip="1.1.1.1", port="22")
    e1.host = h1
    e1.save()
    workspace.path_add("local", "1.1.1.1:22")

    h2 = make_host(workspace, name="h2")
    e2 = make_endpoint(workspace, ip="2.2.2.2", port="22")
    e2.host = h2
    e2.save()
    workspace.path_add("h1", "2.2.2.2:22")
    return h1, e1, h2, e2


def test_path_find_existing_local_source_prints_local_chain(workspace, capsys):
    make_pivoted_chain(workspace)
    capsys.readouterr()
    workspace.path_find_existing("h2")
    out = capsys.readouterr().out
    assert out.strip() == "local > h1 > 2.2.2.2:22"


def test_path_find_existing_as_ip_true_prints_ip_chain(workspace, capsys):
    make_pivoted_chain(workspace)
    capsys.readouterr()
    workspace.path_find_existing("h2", as_ip=True)
    out = capsys.readouterr().out
    assert out.strip() == "local > 1.1.1.1:22 > 2.2.2.2:22"
