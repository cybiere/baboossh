from baboossh import Endpoint, Host, Path


def make_host(name="h1"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    return host


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def test_path_list_empty(shell, capsys):
    shell.onecmd_plus_hooks("path list")
    out = capsys.readouterr().out
    assert "No paths in current workspace" in out


def test_path_add_and_list(shell, capsys):
    make_host()
    make_endpoint()
    shell.onecmd_plus_hooks("path add h1 1.2.3.4:22")
    shell.onecmd_plus_hooks("path list")
    out = capsys.readouterr().out
    assert "h1" in out
    assert "1.2.3.4:22" in out
    assert len(Path.find_all()) == 1


def test_path_delete_removes_path(shell, capsys):
    make_host()
    make_endpoint()
    shell.onecmd_plus_hooks("path add h1 1.2.3.4:22")
    shell.onecmd_plus_hooks("path delete h1 1.2.3.4:22")
    assert Path.find_all() == []


def test_path_get_invalid_format_prints_error(shell, capsys):
    shell.onecmd_plus_hooks("path get badformat")
    out = capsys.readouterr().out
    assert "valid endpoint" in out
