import pytest

from baboossh import Creds, Endpoint, User


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
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


def test_set_option_connection_none_clears_all_three(workspace):
    workspace.options["endpoint"] = make_endpoint()
    workspace.options["user"] = make_user()
    workspace.options["creds"] = make_creds()
    workspace.set_option("connection", None)
    assert workspace.options["endpoint"] is None
    assert workspace.options["user"] is None
    assert workspace.options["creds"] is None


def test_set_option_connection_with_target_sets_endpoint_user_creds(workspace):
    endpoint = make_endpoint()
    user = make_user()
    creds = make_creds()
    workspace.set_option("connection", f"tester:#{creds.id}@1.2.3.4:22")
    assert workspace.options["endpoint"] == endpoint
    assert workspace.options["user"] == user
    assert workspace.options["creds"] == creds


def test_set_option_invalid_option_name_raises_valueerror(workspace):
    with pytest.raises(ValueError):
        workspace.set_option("notanoption", "value")


def test_set_option_endpoint_by_ip_port(workspace):
    endpoint = make_endpoint()
    workspace.set_option("endpoint", "1.2.3.4:22")
    assert workspace.options["endpoint"] == endpoint


def test_set_option_endpoint_by_tag(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    workspace.set_option("endpoint", "!mytag")
    assert workspace.options["endpoint"].name == "mytag"


def test_set_option_endpoint_invalid_raises_valueerror(workspace):
    with pytest.raises(ValueError):
        workspace.set_option("endpoint", "1.2.3.4:22")


def test_set_option_user_unknown_raises_valueerror(workspace):
    with pytest.raises(ValueError):
        workspace.set_option("user", "tester")


def test_set_option_creds_unknown_raises_valueerror(workspace):
    with pytest.raises(ValueError):
        workspace.set_option("creds", "#999")


def test_set_option_creds_by_hash_prefix(workspace):
    creds = make_creds()
    workspace.set_option("creds", "#" + str(creds.id))
    assert workspace.options["creds"] == creds


def test_set_option_value_none_clears_option(workspace):
    workspace.options["user"] = make_user()
    workspace.set_option("user", None)
    assert workspace.options["user"] is None
