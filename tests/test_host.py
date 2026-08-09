import pytest

from baboossh import Endpoint, Host
from baboossh.exceptions import NoPathError


def make_host(hostname="h1.example.com", uname="uname", issue="issue", machine_id="machineid", macs=None):
    macs = macs if macs is not None else []
    host = Host(hostname, uname, issue, machine_id, macs)
    host.save()
    return host


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


# --- construction / get_id / naming ---

def test_get_id_is_stable_and_content_based(workspace):
    id1 = Host.get_id("h1", "uname", "issue", "machineid", [])
    id2 = Host.get_id("h1", "uname", "issue", "machineid", [])
    assert id1 == id2


def test_get_id_differs_on_any_field_change(workspace):
    base = Host.get_id("h1", "uname", "issue", "machineid", [])
    assert Host.get_id("h2", "uname", "issue", "machineid", []) != base
    assert Host.get_id("h1", "uname2", "issue", "machineid", []) != base
    assert Host.get_id("h1", "uname", "issue2", "machineid", []) != base
    assert Host.get_id("h1", "uname", "issue", "machineid2", []) != base
    assert Host.get_id("h1", "uname", "issue", "machineid", ["aa:bb"]) != base


def test_init_new_host_derives_name_from_hostname(workspace):
    host = Host("myserver.example.com", "uname", "issue", "machineid", [])
    assert host.name == "myserver"


def test_init_new_host_truncates_long_hostname_to_20_chars(workspace):
    host = Host("a"*30, "uname", "issue", "machineid", [])
    assert len(host.name) == 20


def test_init_empty_hostname_defaults_name_to_host_1(workspace):
    """Host.__init__'s empty-hostname branch starts incr at 1 (not 0, unlike the
    non-empty branch), so even the very first empty-hostname host gets "host_1"."""
    host = Host("", "uname", "issue", "machineid", [])
    assert host.name == "host_1"


def test_init_two_empty_hostnames_get_host_1_and_host_2(workspace):
    host1 = Host("", "uname1", "issue", "machineid", [])
    host1.save()
    host2 = Host("", "uname2", "issue", "machineid", [])
    host2.save()
    assert host1.name == "host_1"
    assert host2.name == "host_2"


def test_init_duplicate_name_gets_incrementing_suffix(workspace):
    host1 = Host("dup.example.com", "uname1", "issue", "machineid", [])
    host1.save()
    host2 = Host("dup.example.com", "uname2", "issue", "machineid", [])
    host2.save()
    assert host1.name == "dup"
    assert host2.name == "dup_1"


def test_init_bypassing_cache_adopts_existing_host_row(workspace):
    """Regression-style test for a Unique-caching pitfall: constructing Host(same args)
    twice in-process is a cache hit and never re-runs __init__, so it can't actually prove
    the "found existing row, adopt id/name" branch works. Bypass Unique.__call__ via
    Host.__new__ + an explicit __init__ call to genuinely re-run that branch."""
    original = make_host(hostname="findme.example.com", uname="u", issue="i", machine_id="m", macs=[])

    bypassed = Host.__new__(Host)
    Host.__init__(bypassed, "findme.example.com", "u", "i", "m", [])

    assert bypassed.id == original.id
    assert bypassed.name == original.name


# --- Unique caching (metaclass) ---

def test_unique_returns_cached_object_for_repeat_construction(workspace):
    h1 = Host("cached.example.com", "u", "i", "m", [])
    h2 = Host("cached.example.com", "u", "i", "m", [])
    assert h1 is h2


# --- scope ---

def test_scope_true_when_all_endpoints_in_scope(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.save()
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = host
    e2.save()
    assert host.scope is True


def test_scope_false_when_any_endpoint_out_of_scope(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.save()
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = host
    e2.scope = False
    e2.save()
    assert host.scope is False


def test_scope_true_vacuously_when_no_endpoints(workspace):
    """Host.scope's getter is `all(e.scope for e in self.endpoints)`, which is vacuously
    True for an empty iterable - surprising but correct, worth pinning explicitly."""
    host = make_host()
    assert host.scope is True


def test_scope_setter_propagates_to_all_endpoints_and_saves(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.save()
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = host
    e2.save()

    host.scope = False

    reloaded1 = Endpoint.find_one(ip_port="1.1.1.1:22")
    reloaded2 = Endpoint.find_one(ip_port="2.2.2.2:22")
    assert reloaded1.scope is False
    assert reloaded2.scope is False


# --- distance / closest_endpoint (bugs 1, 2) ---

def test_distance_returns_smallest_endpoint_distance(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.distance = 3
    e1.save()
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = host
    e2.distance = 1
    e2.save()
    assert host.distance == 1


def test_distance_zero_endpoints_returns_none(workspace):
    """Regression: previously raised TypeError (fetchone()[0] on None) for a Host with
    no endpoints - a reachable state, e.g. via a partial failure in Connection.identify()."""
    host = make_host()
    assert host.distance is None


def test_closest_endpoint_returns_smallest_distance_endpoint(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.distance = 3
    e1.save()
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = host
    e2.distance = 1
    e2.save()
    assert host.closest_endpoint.ip == "2.2.2.2"


def test_closest_endpoint_zero_endpoints_raises_value_error(workspace):
    """Regression: previously raised TypeError (row[1] on None) for a Host with no
    endpoints. Now raises a clear ValueError instead, since every caller of this
    property dereferences the result immediately with no None-check."""
    host = make_host()
    with pytest.raises(ValueError):
        host.closest_endpoint


# --- endpoints property ---

def test_endpoints_returns_empty_list_when_none_attached(workspace):
    host = make_host()
    assert host.endpoints == []


def test_endpoints_returns_all_attached_endpoints(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.save()
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = host
    e2.save()
    ips = {e.ip for e in host.endpoints}
    assert ips == {"1.1.1.1", "2.2.2.2"}


# --- save / delete ---

def test_save_new_host_assigns_id(workspace):
    host = make_host()
    assert host.id is not None


def test_save_existing_host_updates_fields(workspace):
    host = make_host()
    host.uname = "new-uname"
    host.save()
    reloaded = Host.find_one(host_id=host.id)
    assert reloaded.uname == "new-uname"


def test_delete_no_id_returns_empty_dict(workspace):
    host = Host("unsaved.example.com", "u", "i", "m", [])
    assert host.delete() == {}


def test_delete_disassociates_endpoints_without_deleting_them(workspace):
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.save()
    host.delete()
    reloaded = Endpoint.find_one(ip_port="1.1.1.1:22")
    assert reloaded is not None
    assert reloaded.host is None


def test_delete_removes_paths_sourced_from_host(workspace):
    from baboossh import Path
    host = make_host()
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = host
    e1.save()
    workspace.path_add(host.name, "1.1.1.1:22")
    assert len(Path.find_all(src=host)) == 1
    host.delete()
    assert Path.find_all(src=host) == []


def test_delete_removes_host_row(workspace):
    host = make_host()
    host_id = host.id
    host.delete()
    assert Host.find_one(host_id=host_id) is None


# --- find_all ---

def test_find_all_returns_all_hosts(workspace):
    make_host(hostname="h1.example.com", uname="u1")
    make_host(hostname="h2.example.com", uname="u2")
    assert len(Host.find_all()) == 2


def test_find_all_scope_true_filters_in_scope_only(workspace):
    in_scope = make_host(hostname="in.example.com", uname="u1")
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = in_scope
    e1.save()

    out_of_scope = make_host(hostname="out.example.com", uname="u2")
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = out_of_scope
    e2.scope = False
    e2.save()

    results = Host.find_all(scope=True)
    assert in_scope in results
    assert out_of_scope not in results


def test_find_all_scope_false_filters_out_of_scope_only(workspace):
    in_scope = make_host(hostname="in.example.com", uname="u1")
    e1 = make_endpoint(ip="1.1.1.1")
    e1.host = in_scope
    e1.save()

    out_of_scope = make_host(hostname="out.example.com", uname="u2")
    e2 = make_endpoint(ip="2.2.2.2")
    e2.host = out_of_scope
    e2.scope = False
    e2.save()

    results = Host.find_all(scope=False)
    assert out_of_scope in results
    assert in_scope not in results


def test_find_all_scope_none_returns_both(workspace):
    make_host(hostname="h1.example.com", uname="u1")
    make_host(hostname="h2.example.com", uname="u2")
    assert len(Host.find_all(scope=None)) == 2


# --- find_one ---

def test_find_one_by_host_id_returns_host(workspace):
    host = make_host()
    assert Host.find_one(host_id=host.id) == host


def test_find_one_by_name_returns_host(workspace):
    host = make_host()
    assert Host.find_one(name=host.name) == host


def test_find_one_unknown_id_returns_none(workspace):
    assert Host.find_one(host_id=99999) is None


def test_find_one_unknown_name_returns_none(workspace):
    assert Host.find_one(name="doesnotexist") is None


def test_find_one_no_args_returns_none(workspace):
    assert Host.find_one() is None


# --- find_one(prev_hop_to=...) ---

def make_pivoted_chain(workspace):
    h1 = make_host(hostname="h1.example.com", uname="u1")
    e1 = make_endpoint(ip="1.1.1.1", port="22")
    e1.host = h1
    e1.save()
    workspace.path_add("local", "1.1.1.1:22")

    h2 = make_host(hostname="h2.example.com", uname="u2")
    e2 = make_endpoint(ip="2.2.2.2", port="22")
    e2.host = h2
    e2.save()
    workspace.path_add(h1.name, "2.2.2.2:22")
    return h1, e1, h2, e2


def test_find_one_prev_hop_to_direct_path_returns_none(workspace):
    h1, e1, h2, e2 = make_pivoted_chain(workspace)
    assert Host.find_one(prev_hop_to=e1) is None


def test_find_one_prev_hop_to_no_path_raises_no_path_error(workspace):
    make_endpoint(ip="9.9.9.9")
    orphan = Endpoint.find_one(ip_port="9.9.9.9:22")
    with pytest.raises(NoPathError):
        Host.find_one(prev_hop_to=orphan)


def test_find_one_prev_hop_to_returns_closest_source_host(workspace):
    h1, e1, h2, e2 = make_pivoted_chain(workspace)
    assert Host.find_one(prev_hop_to=e2) == h1


def test_find_one_prev_hop_to_picks_min_distance_among_multiple_paths(workspace):
    h1, e1, h2, e2 = make_pivoted_chain(workspace)

    h3 = make_host(hostname="h3.example.com", uname="u3")
    e3 = make_endpoint(ip="3.3.3.3", port="22")
    e3.host = h3
    e3.distance = 5
    e3.save()
    workspace.path_add("local", "3.3.3.3:22")
    workspace.path_add(h3.name, "2.2.2.2:22")

    e1.distance = 1
    e1.save()

    assert Host.find_one(prev_hop_to=e2) == h1


# --- getNextId (dead code, trivial coverage) ---

def test_get_next_id_returns_1_when_no_hosts(workspace):
    assert Host.getNextId() == 1


def test_get_next_id_returns_max_plus_1(workspace):
    host = make_host()
    assert Host.getNextId() == host.id + 1


# --- search ---

def test_search_invalid_field_raises_value_error(workspace):
    with pytest.raises(ValueError):
        Host.search("hostname", "foo")


def test_search_by_name_returns_matches(workspace):
    host = make_host(hostname="findable.example.com", uname="u1")
    results = Host.search("name", "findable")
    assert host in results


def test_search_by_uname_returns_matches(workspace):
    host = make_host(uname="Linux debian 6.1")
    results = Host.search("uname", "debian")
    assert host in results


def test_search_excludes_out_of_scope_by_default(workspace):
    host = make_host(hostname="hidden.example.com", uname="u1")
    e = make_endpoint(ip="1.1.1.1")
    e.host = host
    e.scope = False
    e.save()
    results = Host.search("name", "hidden")
    assert host not in results


def test_search_show_all_includes_out_of_scope(workspace):
    host = make_host(hostname="hidden.example.com", uname="u1")
    e = make_endpoint(ip="1.1.1.1")
    e.host = host
    e.scope = False
    e.save()
    results = Host.search("name", "hidden", show_all=True)
    assert host in results


# --- __str__ ---

def test_str_returns_name(workspace):
    host = make_host(hostname="strme.example.com", uname="u1")
    assert str(host) == host.name
