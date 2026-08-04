from baboossh import Endpoint, Host


def make_host_with_endpoint(name="h1", ip="1.2.3.4", port="22"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    endpoint = Endpoint(ip, port)
    endpoint.host = host
    endpoint.save()
    return host, endpoint


def test_host_del_unknown_name_returns_false(workspace):
    assert workspace.host_del("doesnotexist") is False


def test_host_del_known_name_removes_host(workspace):
    make_host_with_endpoint()
    assert workspace.host_del("h1") is True
    assert Host.find_all() == []


def test_host_tag_unknown_host_returns_false(workspace):
    assert workspace.host_tag("doesnotexist", "mytag") is False


def test_host_tag_adds_tag_to_all_host_endpoints(workspace):
    host, endpoint = make_host_with_endpoint()
    assert workspace.host_tag("h1", "mytag") is True
    assert "mytag" in endpoint.tags


def test_host_untag_unknown_host_returns_false(workspace):
    assert workspace.host_untag("doesnotexist", "mytag") is False


def test_host_untag_removes_tag_from_all_host_endpoints(workspace):
    host, endpoint = make_host_with_endpoint()
    endpoint.tag("mytag")
    assert workspace.host_untag("h1", "mytag") is True
    assert "mytag" not in endpoint.tags
