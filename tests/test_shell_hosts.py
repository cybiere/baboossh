from baboossh import Endpoint, Host


def make_host_with_endpoint(name="h1", ip="1.2.3.4", port="22"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    endpoint = Endpoint(ip, port)
    endpoint.host = host
    endpoint.save()
    return host, endpoint


def test_host_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("host list")
    out = capsys.readouterr().out
    assert "No hosts in current workspace" in out


def test_host_list_shows_host(shell, capsys):
    make_host_with_endpoint()
    shell.onecmd_plus_hooks("host list")
    out = capsys.readouterr().out
    assert "h1" in out


def test_host_search_invalid_field_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("host search notafield val")
    out = capsys.readouterr().out
    assert "Invalid field specified" in out


def test_host_search_by_name(shell, capsys):
    make_host_with_endpoint()
    shell.onecmd_plus_hooks("host search name h1")
    out = capsys.readouterr().out
    assert "h1" in out


def test_host_delete_removes_host(shell, capsys):
    make_host_with_endpoint()
    shell.onecmd_plus_hooks("host delete h1")
    assert Host.find_all() == []


def test_host_tag_adds_tag(shell, capsys):
    host, endpoint = make_host_with_endpoint()
    shell.onecmd_plus_hooks("host tag h1 mytag")
    assert "mytag" in endpoint.tags


def test_host_untag_removes_tag(shell, capsys):
    host, endpoint = make_host_with_endpoint()
    endpoint.tag("mytag")
    shell.onecmd_plus_hooks("host untag h1 mytag")
    assert "mytag" not in endpoint.tags
