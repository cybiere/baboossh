from baboossh import Endpoint, Tag


def make_tagged_endpoint(tagname="mytag", ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    endpoint.tag(tagname)
    return endpoint


def test_tag_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("tag list")
    out = capsys.readouterr().out
    assert "No tags in current workspace" in out


def test_tag_list_shows_tag(shell, capsys):
    make_tagged_endpoint()
    shell.onecmd_plus_hooks("tag list")
    out = capsys.readouterr().out
    assert "mytag" in out


def test_tag_show_lists_endpoints(shell, capsys):
    make_tagged_endpoint()
    shell.onecmd_plus_hooks("tag show mytag")
    out = capsys.readouterr().out
    assert "1.2.3.4:22" in out


def test_tag_delete_removes_tag(shell, capsys):
    make_tagged_endpoint()
    shell.onecmd_plus_hooks("tag delete mytag")
    assert Tag.find_one(name="mytag") is None
