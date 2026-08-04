from baboossh import Creds, Endpoint, Host, User


def make_creds(content="secret"):
    creds = Creds("password", content)
    creds.save()
    return creds


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def make_host(name="h1"):
    host = Host(name, "uname", "issue", "machineid", [])
    host.save()
    return host


def test_identify_object_by_creds_hash(workspace):
    creds = make_creds()
    assert workspace.identify_object("#" + str(creds.id)) == creds


def test_identify_object_by_username(workspace):
    user = make_user()
    assert workspace.identify_object("tester") == user


def test_identify_object_by_endpoint_ip_port(workspace):
    endpoint = make_endpoint()
    assert workspace.identify_object("1.2.3.4:22") == endpoint


def test_identify_object_by_endpoint_invalid_format_falls_through(workspace):
    host = make_host(name="badformat")
    assert workspace.identify_object("badformat") == host


def test_identify_object_by_host_name(workspace):
    host = make_host()
    assert workspace.identify_object("h1") == host


def test_identify_object_unknown_returns_none(workspace):
    assert workspace.identify_object("doesnotexist") is None


def test_scope_toggles_and_saves(workspace):
    user = make_user()
    assert user.scope is True
    workspace.scope("tester")
    assert User.find_one(name="tester").scope is False


def test_scope_unknown_target_no_op(workspace):
    assert workspace.scope("doesnotexist") is None
