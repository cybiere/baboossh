from baboossh import Endpoint, Tag


def make_tagged_endpoint(tagname="mytag", ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    endpoint.tag(tagname)
    return endpoint


def test_tag_show_unknown_prints_and_returns_none(workspace, capsys):
    result = workspace.tag_show("doesnotexist")
    assert result is None
    assert "No tag matching" in capsys.readouterr().out


def test_tag_show_known_lists_endpoints(workspace, capsys):
    make_tagged_endpoint()
    workspace.tag_show("mytag")
    assert "1.2.3.4:22" in capsys.readouterr().out


def test_tag_del_unknown_returns_none(workspace):
    assert workspace.tag_del("doesnotexist") is None


def test_tag_del_removes_tag(workspace):
    make_tagged_endpoint()
    workspace.tag_del("mytag")
    assert Tag.find_one(name="mytag") is None
