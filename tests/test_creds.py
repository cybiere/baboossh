from unittest.mock import MagicMock

import pytest

from baboossh import Connection, Creds, Endpoint, User


def make_creds(content="secret"):
    creds = Creds("password", content)
    creds.save()
    return creds


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def make_connection(endpoint=None, user=None, creds=None):
    endpoint = endpoint or make_endpoint()
    user = user or make_user()
    creds = creds or make_creds()
    conn = Connection(endpoint, user, creds)
    conn.save()
    return conn


# --- construction / get_id ---

def test_get_id_is_stable_and_content_based(workspace):
    assert Creds.get_id("password", "secret") == Creds.get_id("password", "secret")


def test_get_id_differs_by_content(workspace):
    assert Creds.get_id("password", "secret") != Creds.get_id("password", "other")


def test_init_unregistered_type_raises_key_error(workspace):
    """Documents an existing, not-a-bug failure mode: an unregistered creds_type
    isn't caught/validated, it just propagates Extensions.auths' own KeyError."""
    with pytest.raises(KeyError):
        Creds("bogus_type", "x")


def test_unique_returns_cached_object_for_repeat_construction(workspace):
    c1 = Creds("password", "cached")
    c2 = Creds("password", "cached")
    assert c1 is c2


def test_init_bypassing_cache_adopts_existing_creds_row(workspace):
    """Same Unique-caching pitfall as Host/Endpoint/User: reconstructing Creds(same
    args) in-process is a cache hit, so bypass via Creds.__new__ + explicit __init__
    to genuinely re-run the "found existing row" branch - worth confirming here since
    Creds.__init__'s lookup key (type, obj.identifier) is structurally different from
    get_id's own independent re-instantiation of the extension object."""
    original = make_creds(content="findme")

    bypassed = Creds.__new__(Creds)
    Creds.__init__(bypassed, "password", "findme")

    assert bypassed.id == original.id


# --- save / delete ---

def test_save_new_creds_assigns_id(workspace):
    creds = make_creds()
    assert creds.id is not None


def test_save_existing_creds_updates_content(workspace):
    creds = make_creds()
    creds.creds_content = "newsecret"
    creds.save()
    reloaded = Creds.find_one(creds_id=creds.id)
    assert reloaded.creds_content == "newsecret"


def test_delete_no_id_returns_empty_dict(workspace):
    creds = Creds("password", "unsaved")
    assert creds.delete() == {}


def test_delete_removes_referencing_connections(workspace):
    creds = make_creds()
    conn = make_connection(creds=creds)
    creds.delete()
    assert Connection.find_one(connection_id=conn.id) is None


def test_delete_calls_extension_delete_before_removing_row(workspace, monkeypatch):
    """auth_password's own .delete() is a no-op, so spy on it to prove Creds.delete()
    actually invokes the extension's delete() rather than just asserting no crash."""
    creds = make_creds()
    spy = MagicMock()
    monkeypatch.setattr(creds.obj, "delete", spy)

    creds.delete()

    spy.assert_called_once()


def test_delete_removes_creds_row(workspace):
    creds = make_creds()
    creds_id = creds.id
    creds.delete()
    assert Creds.find_one(creds_id=creds_id) is None


# --- find_all ---

def test_find_all_returns_all_creds(workspace):
    make_creds(content="secret1")
    make_creds(content="secret2")
    assert len(Creds.find_all()) == 2


def test_find_all_scope_true_filters(workspace):
    in_scope = make_creds(content="in")
    out_of_scope = make_creds(content="out")
    out_of_scope.scope = False
    out_of_scope.save()

    assert Creds.find_all(scope=True) == [in_scope]


def test_find_all_scope_false_filters(workspace):
    in_scope = make_creds(content="in")
    out_of_scope = make_creds(content="out")
    out_of_scope.scope = False
    out_of_scope.save()

    assert Creds.find_all(scope=False) == [out_of_scope]


def test_find_all_found_filters(workspace):
    origin = make_endpoint()
    discovered = make_creds(content="found")
    discovered.found = origin
    discovered.save()
    other = make_creds(content="notfound")

    results = Creds.find_all(found=origin)
    assert results == [discovered]
    assert other not in results


def test_find_all_scope_and_found_combined(workspace):
    origin = make_endpoint()
    discovered_in_scope = make_creds(content="in")
    discovered_in_scope.found = origin
    discovered_in_scope.save()
    discovered_out_of_scope = make_creds(content="out")
    discovered_out_of_scope.found = origin
    discovered_out_of_scope.scope = False
    discovered_out_of_scope.save()

    results = Creds.find_all(scope=True, found=origin)
    assert results == [discovered_in_scope]


# --- find_one (bug 5) ---

def test_find_one_by_id_returns_creds(workspace):
    creds = make_creds()
    assert Creds.find_one(creds_id=creds.id) == creds


def test_find_one_unknown_id_returns_none(workspace):
    assert Creds.find_one(creds_id=99999) is None


def test_find_one_no_args_returns_none(workspace):
    """Regression: previously raised TypeError (missing required positional argument),
    unlike Host/Endpoint/User's find_one which all default to None and return None."""
    assert Creds.find_one() is None


# --- show / edit (thin delegation) ---

def test_show_prints_password(workspace, capsys):
    creds = make_creds(content="hunter2")
    creds.show()
    assert "hunter2" in capsys.readouterr().out


def test_edit_reserializes_and_saves(workspace):
    creds = make_creds(content="hunter2")
    creds.edit()  # auth_password.edit() just prints "Nothing to edit", content unchanged
    reloaded = Creds.find_one(creds_id=creds.id)
    assert reloaded.creds_content == "hunter2"


# --- __str__ ---

def test_str_returns_hash_id(workspace):
    creds = make_creds()
    assert str(creds) == "#"+str(creds.id)
