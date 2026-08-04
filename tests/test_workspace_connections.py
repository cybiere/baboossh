import pytest

from baboossh import Connection, Creds, Endpoint, Host, User
from baboossh.exceptions import NoPathError


def make_endpoint(ip="1.2.3.4", port="22", reachable=None):
    endpoint = Endpoint(ip, port)
    endpoint.reachable = reachable
    endpoint.save()
    return endpoint


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def make_creds(content="secret"):
    creds = Creds("password", content)
    creds.save()
    return creds


def make_connection(endpoint=None, user=None, creds=None):
    endpoint = endpoint or make_endpoint()
    user = user or make_user()
    creds = creds or make_creds()
    conn = Connection(endpoint, user, creds)
    conn.save()
    return conn


def make_host(name="h1"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    return host


def test_connection_close_unknown_endpoint_raises_valueerror(workspace):
    make_user()
    make_creds()
    with pytest.raises(ValueError):
        workspace.connection_close("tester:#1@1.2.3.4:22")


def test_connection_close_never_opened_returns_none_cleanly(workspace):
    creds = make_creds()
    make_connection(creds=creds)
    result = workspace.connection_close(f"tester:#{creds.id}@1.2.3.4:22")
    assert result is None


def test_connection_del_unknown_endpoint_raises_valueerror(workspace):
    make_user()
    make_creds()
    with pytest.raises(ValueError):
        workspace.connection_del("tester:#1@1.2.3.4:22")


def test_connection_del_removes_connection(workspace):
    creds = make_creds()
    make_connection(creds=creds)
    assert workspace.connection_del(f"tester:#{creds.id}@1.2.3.4:22") is True
    assert Connection.find_all() == []


def test_enum_probe_target_star_returns_all_scoped_endpoints(workspace):
    make_endpoint(ip="1.1.1.1")
    make_endpoint(ip="2.2.2.2")
    result = workspace.enum_probe(target="*")
    assert len(result) == 2


def test_enum_probe_target_tag_returns_tagged_endpoints(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    make_endpoint(ip="2.2.2.2")
    result = workspace.enum_probe(target="!mytag")
    assert result == [endpoint]


def test_enum_probe_target_ip_port_returns_single_endpoint(workspace):
    endpoint = make_endpoint()
    result = workspace.enum_probe(target="1.2.3.4:22")
    assert result == [endpoint]


def test_enum_probe_target_invalid_format_raises_valueerror(workspace):
    with pytest.raises(ValueError):
        workspace.enum_probe(target="doesnotexist:22")


def test_enum_probe_uses_option_endpoint_when_target_none(workspace):
    endpoint = make_endpoint()
    workspace.options["endpoint"] = endpoint
    result = workspace.enum_probe()
    assert result == [endpoint]


def test_enum_probe_excludes_already_reachable_unless_again(workspace):
    make_endpoint(ip="1.1.1.1", reachable=True)
    unreached = make_endpoint(ip="2.2.2.2", reachable=False)
    result = workspace.enum_probe(target="*")
    assert result == [unreached]
    result_again = workspace.enum_probe(target="*", again=True)
    assert len(result_again) == 2


def test_enum_connect_by_hostname_no_connection_raises_valueerror(workspace):
    host = make_host()
    endpoint = make_endpoint()
    endpoint.host = host
    endpoint.save()
    with pytest.raises(ValueError):
        workspace.enum_connect(target="h1")


def test_enum_connect_by_hostname_returns_existing_connection(workspace):
    host = make_host()
    endpoint = make_endpoint()
    endpoint.host = host
    endpoint.save()
    conn = make_connection(endpoint=endpoint)
    result = workspace.enum_connect(target="h1")
    assert result == [conn]


def test_enum_connect_target_with_wildcards_builds_cartesian_product(workspace):
    make_endpoint(reachable=True)
    make_user()
    make_creds()
    result = workspace.enum_connect(target="*:*@*")
    assert len(result) == 1


def test_enum_connect_no_credentials_supplied_raises_valueerror(workspace):
    with pytest.raises(ValueError):
        workspace.enum_connect(target="tester@1.2.3.4:22")


def test_enum_connect_force_flag_returns_existing_plus_new(workspace):
    endpoint = make_endpoint(reachable=True)
    user = make_user()
    creds = make_creds()
    make_connection(endpoint=endpoint, user=user, creds=creds)
    result = workspace.enum_connect(force=True)
    assert len(result) == 1


def test_enum_run_by_hostname_no_connection_raises_valueerror(workspace):
    host = make_host()
    endpoint = make_endpoint()
    endpoint.host = host
    endpoint.save()
    with pytest.raises(ValueError):
        workspace.enum_run(target="h1")


def test_enum_run_wildcard_target_returns_matching_connections(workspace):
    conn = make_connection()
    result = workspace.enum_run(target="*:*@*")
    assert result == [conn]


def test_enum_run_tagged_endpoint_target_returns_matching_connections(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    conn = make_connection(endpoint=endpoint)
    result = workspace.enum_run(target="*:*@!mytag")
    assert result == [conn]


def test_run_unreachable_endpoint_raises_nopatherror(workspace):
    conn = make_connection()
    with pytest.raises(NoPathError):
        workspace.run([conn], payload=None, stmt=None)
