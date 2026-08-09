import pytest

from baboossh import Connection, Creds, Endpoint, Host, User


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def make_host(hostname="h1.example.com", uname="uname", issue="issue", machine_id="machineid", macs=None):
    macs = macs if macs is not None else []
    host = Host(hostname, uname, issue, machine_id, macs)
    host.save()
    return host


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


# --- construction / validation (bug 4) ---

def test_init_invalid_ip_raises_value_error(workspace):
    with pytest.raises(ValueError):
        Endpoint("not-an-ip", "22")


def test_init_string_port_non_digit_raises_value_error(workspace):
    with pytest.raises(ValueError):
        Endpoint("1.2.3.4", "abc")


def test_init_negative_int_port_raises_value_error(workspace):
    """Regression: previously `isinstance(port, int)` short-circuited validation
    entirely for int ports, silently accepting negative values."""
    with pytest.raises(ValueError):
        Endpoint("1.2.3.4", -5)


def test_init_negative_string_port_raises_value_error(workspace):
    """Contrast test: the string path already correctly rejects negative ports."""
    with pytest.raises(ValueError):
        Endpoint("1.2.3.4", "-5")


def test_init_zero_port_is_accepted(workspace):
    """Documents the fix's leniency choice: port=0 stays legal, matching the
    string path's existing behavior ("0".isdigit() is True)."""
    endpoint = Endpoint("1.2.3.4", 0)
    assert endpoint.port == 0


# --- get_id / Unique caching ---

def test_get_id_is_stable_and_content_based(workspace):
    assert Endpoint.get_id("1.2.3.4", "22") == Endpoint.get_id("1.2.3.4", "22")


def test_get_id_differs_by_ip_or_port(workspace):
    base = Endpoint.get_id("1.2.3.4", "22")
    assert Endpoint.get_id("1.2.3.5", "22") != base
    assert Endpoint.get_id("1.2.3.4", "23") != base


def test_unique_returns_cached_object_for_repeat_construction(workspace):
    e1 = Endpoint("9.9.9.9", "22")
    e2 = Endpoint("9.9.9.9", "22")
    assert e1 is e2


def test_init_bypassing_cache_adopts_existing_endpoint_row(workspace):
    """Same Unique-caching pitfall as Host: reconstructing Endpoint(same args) in-process
    is a cache hit, so bypass via Endpoint.__new__ + explicit __init__ to genuinely
    re-run the "found existing row" branch."""
    original = make_endpoint(ip="8.8.8.8", port="53")

    bypassed = Endpoint.__new__(Endpoint)
    Endpoint.__init__(bypassed, "8.8.8.8", "53")

    assert bypassed.id == original.id


# --- port property ---

def test_port_getter_returns_int_for_string_input(workspace):
    endpoint = Endpoint("1.2.3.4", "22")
    assert endpoint.port == 22
    assert isinstance(endpoint.port, int)


def test_port_setter_casts_to_int(workspace):
    endpoint = make_endpoint()
    endpoint.port = "2222"
    assert endpoint.port == 2222
    assert isinstance(endpoint.port, int)


# --- save / delete ---

def test_save_new_endpoint_assigns_id(workspace):
    endpoint = make_endpoint()
    assert endpoint.id is not None


def test_save_existing_endpoint_updates_fields(workspace):
    endpoint = make_endpoint()
    endpoint.reachable = True
    endpoint.save()
    reloaded = Endpoint.find_one(endpoint_id=endpoint.id)
    assert reloaded.reachable is True


def test_delete_no_id_returns_empty_dict(workspace):
    endpoint = Endpoint("5.5.5.5", "22")
    assert endpoint.delete() == {}


def test_delete_last_endpoint_of_host_also_deletes_host(workspace):
    host = make_host()
    endpoint = make_endpoint(ip="1.1.1.1")
    endpoint.host = host
    endpoint.save()

    endpoint.delete()

    assert Host.find_one(host_id=host.id) is None


def test_delete_non_last_endpoint_keeps_host(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.save()
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = host
    e2.save()

    e1.delete()

    assert Host.find_one(host_id=host.id) is not None


def test_delete_removes_referencing_connections(workspace):
    endpoint = make_endpoint()
    conn = make_connection(endpoint=endpoint)
    endpoint.delete()
    assert Connection.find_one(connection_id=conn.id) is None


def test_delete_removes_referencing_paths(workspace):
    from baboossh import Path
    host = make_host()
    src_endpoint = make_endpoint(ip="1.1.1.1")
    src_endpoint.host = host
    src_endpoint.save()
    dst_endpoint = make_endpoint(ip="2.2.2.2")
    workspace.path_add(host.name, "2.2.2.2:22")
    assert len(Path.find_all(dst=dst_endpoint)) == 1

    dst_endpoint.delete()

    assert Path.find_all(dst=dst_endpoint) == []


def test_delete_removes_tags(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    endpoint.delete()
    from baboossh import Tag
    assert Tag.find_all(endpoint=endpoint) == []


# --- find_all ---

def test_find_all_returns_all_endpoints(workspace):
    make_endpoint(ip="1.1.1.1")
    make_endpoint(ip="2.2.2.2")
    assert len(Endpoint.find_all()) == 2


def test_find_all_scope_filters(workspace):
    in_scope = make_endpoint(ip="1.1.1.1")
    out_of_scope = make_endpoint(ip="2.2.2.2")
    out_of_scope.scope = False
    out_of_scope.save()

    assert Endpoint.find_all(scope=True) == [in_scope]
    assert Endpoint.find_all(scope=False) == [out_of_scope]


def test_find_all_found_filters(workspace):
    origin = make_endpoint(ip="1.1.1.1")
    discovered = make_endpoint(ip="2.2.2.2")
    discovered.found = origin
    discovered.save()
    other = make_endpoint(ip="3.3.3.3")

    results = Endpoint.find_all(found=origin)
    assert results == [discovered]
    assert other not in results


def test_find_all_scope_and_found_combined(workspace):
    origin = make_endpoint(ip="1.1.1.1")
    discovered_in_scope = make_endpoint(ip="2.2.2.2")
    discovered_in_scope.found = origin
    discovered_in_scope.save()
    discovered_out_of_scope = make_endpoint(ip="3.3.3.3")
    discovered_out_of_scope.found = origin
    discovered_out_of_scope.scope = False
    discovered_out_of_scope.save()

    results = Endpoint.find_all(scope=True, found=origin)
    assert results == [discovered_in_scope]


# --- find_one ---

def test_find_one_by_id_returns_endpoint(workspace):
    endpoint = make_endpoint()
    assert Endpoint.find_one(endpoint_id=endpoint.id) == endpoint


def test_find_one_id_zero_returns_none_without_query(workspace):
    """Dedicated test for the deliberate "id 0 means unset" sentinel."""
    assert Endpoint.find_one(endpoint_id=0) is None


def test_find_one_by_ip_port_returns_endpoint(workspace):
    endpoint = make_endpoint()
    assert Endpoint.find_one(ip_port="1.2.3.4:22") == endpoint


def test_find_one_ip_port_missing_colon_raises_value_error(workspace):
    with pytest.raises(ValueError):
        Endpoint.find_one(ip_port="1.2.3.4")


def test_find_one_unknown_returns_none(workspace):
    assert Endpoint.find_one(endpoint_id=99999) is None
    assert Endpoint.find_one(ip_port="9.9.9.9:22") is None


def test_find_one_no_args_returns_none(workspace):
    assert Endpoint.find_one() is None


# --- tag / untag ---

def test_tag_adds_tag(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    assert "mytag" in endpoint.tags


def test_tag_duplicate_is_idempotent(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    endpoint.tag("mytag")
    assert endpoint.tags == {"mytag"}


def test_untag_removes_tag(workspace):
    endpoint = make_endpoint()
    endpoint.tag("mytag")
    endpoint.untag("mytag")
    assert "mytag" not in endpoint.tags


def test_untag_not_present_is_idempotent(workspace):
    endpoint = make_endpoint()
    endpoint.untag("neverdadded")  # must not raise
    assert endpoint.tags == set()


# --- search ---

def test_search_invalid_field_raises_value_error(workspace):
    with pytest.raises(ValueError):
        Endpoint.search("host", "foo")


def test_search_by_ip_returns_matches(workspace):
    endpoint = make_endpoint(ip="10.20.30.40")
    results = Endpoint.search("ip", "20.30")
    assert endpoint in results


def test_search_by_port_returns_matches(workspace):
    endpoint = make_endpoint(port="2222")
    results = Endpoint.search("port", "222")
    assert endpoint in results


def test_search_excludes_out_of_scope_by_default(workspace):
    endpoint = make_endpoint(ip="10.20.30.40")
    endpoint.scope = False
    endpoint.save()
    results = Endpoint.search("ip", "20.30")
    assert endpoint not in results


def test_search_show_all_includes_out_of_scope(workspace):
    endpoint = make_endpoint(ip="10.20.30.40")
    endpoint.scope = False
    endpoint.save()
    results = Endpoint.search("ip", "20.30", show_all=True)
    assert endpoint in results


# --- __str__ ---

def test_str_returns_ip_colon_port(workspace):
    endpoint = make_endpoint(ip="1.2.3.4", port="22")
    assert str(endpoint) == "1.2.3.4:22"
