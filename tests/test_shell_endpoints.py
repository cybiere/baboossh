from baboossh import Endpoint


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def test_endpoint_add_creates_endpoint(shell, capsys):
    shell.onecmd_plus_hooks("endpoint add 1.2.3.4 22")
    out = capsys.readouterr().out
    assert "added" in out
    assert len(Endpoint.find_all()) == 1


def test_endpoint_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("endpoint list")
    out = capsys.readouterr().out
    assert "No endpoints in current workspace" in out


def test_endpoint_list_shows_endpoint(shell, capsys):
    make_endpoint()
    shell.onecmd_plus_hooks("endpoint list")
    out = capsys.readouterr().out
    assert "1.2.3.4:22" in out


def test_endpoint_list_filters_by_reachable(shell, capsys):
    reachable = make_endpoint(ip="1.1.1.1")
    reachable.reachable = True
    reachable.save()
    make_endpoint(ip="2.2.2.2")
    shell.onecmd_plus_hooks("endpoint list -r true")
    out = capsys.readouterr().out
    assert "1.1.1.1:22" in out
    assert "2.2.2.2:22" not in out


def test_endpoint_search_invalid_field_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("endpoint search notafield val")
    out = capsys.readouterr().out
    assert "Invalid field specified" in out


def test_endpoint_search_by_ip(shell, capsys):
    make_endpoint()
    shell.onecmd_plus_hooks("endpoint search ip 1.2.3.4")
    out = capsys.readouterr().out
    assert "1.2.3.4:22" in out


def test_endpoint_delete_removes_endpoint(shell, capsys):
    make_endpoint()
    shell.onecmd_plus_hooks("endpoint delete 1.2.3.4:22")
    assert Endpoint.find_all() == []


def test_endpoint_tag_adds_tag(shell, capsys):
    endpoint = make_endpoint()
    shell.onecmd_plus_hooks("endpoint tag 1.2.3.4:22 mytag")
    assert "mytag" in endpoint.tags


def test_endpoint_untag_removes_tag(shell, capsys):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    shell.onecmd_plus_hooks("endpoint untag 1.2.3.4:22 mytag")
    assert "mytag" not in endpoint.tags
