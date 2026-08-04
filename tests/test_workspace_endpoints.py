from baboossh import Endpoint


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def test_endpoint_add_creates_endpoint(workspace):
    workspace.endpoint_add("1.2.3.4", "22")
    assert len(Endpoint.find_all()) == 1


def test_endpoint_del_by_ip_port_removes_endpoint(workspace):
    make_endpoint()
    assert workspace.endpoint_del("1.2.3.4:22") is True
    assert Endpoint.find_all() == []


def test_endpoint_del_unknown_returns_false(workspace):
    assert workspace.endpoint_del("1.2.3.4:22") is False


def test_endpoint_del_invalid_format_returns_false(workspace):
    assert workspace.endpoint_del("badformat") is False


def test_endpoint_del_by_tag_removes_all_tagged(workspace):
    endpoint1 = make_endpoint(ip="1.1.1.1")
    endpoint2 = make_endpoint(ip="2.2.2.2")
    endpoint1.tag("mytag")
    endpoint2.tag("mytag")
    assert workspace.endpoint_del("!mytag") is True
    assert Endpoint.find_all() == []


def test_endpoint_del_clears_selected_endpoint_option(workspace):
    endpoint = make_endpoint()
    workspace.set_option("endpoint", "1.2.3.4:22")
    assert workspace.options["endpoint"] == endpoint
    workspace.endpoint_del("1.2.3.4:22")
    assert workspace.options["endpoint"] is None


def test_endpoint_tag_unknown_returns_false(workspace):
    assert workspace.endpoint_tag("1.2.3.4:22", "mytag") is False


def test_endpoint_tag_adds_tag(workspace):
    endpoint = make_endpoint()
    assert workspace.endpoint_tag("1.2.3.4:22", "mytag") is True
    assert "mytag" in endpoint.tags


def test_endpoint_untag_unknown_returns_false(workspace):
    assert workspace.endpoint_untag("1.2.3.4:22", "mytag") is False


def test_endpoint_untag_removes_tag(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    assert workspace.endpoint_untag("1.2.3.4:22", "mytag") is True
    assert "mytag" not in endpoint.tags
