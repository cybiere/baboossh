from baboossh import Connection, Creds, Endpoint, User


def make_user(name="alice"):
    user = User(name)
    user.save()
    return user


def make_endpoint(ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    return endpoint


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


# --- construction / get_id / Unique caching ---

def test_get_id_is_stable_and_content_based(workspace):
    assert User.get_id("alice") == User.get_id("alice")


def test_get_id_differs_by_name(workspace):
    assert User.get_id("alice") != User.get_id("bob")


def test_unique_returns_cached_object_for_repeat_construction(workspace):
    u1 = User("cached")
    u2 = User("cached")
    assert u1 is u2


def test_init_new_user_defaults_scope_true_and_found_none(workspace):
    user = User("newuser")
    assert user.scope is True
    assert user.found is None
    assert user.id is None


def test_init_bypassing_cache_adopts_existing_user_row(workspace):
    """Same Unique-caching pitfall as Host/Endpoint: reconstructing User(same args)
    in-process is a cache hit, so bypass via User.__new__ + explicit __init__ to
    genuinely re-run the "found existing row" branch."""
    original = make_user(name="findme")

    bypassed = User.__new__(User)
    User.__init__(bypassed, "findme")

    assert bypassed.id == original.id


# --- save / delete ---

def test_save_new_user_assigns_id(workspace):
    user = make_user()
    assert user.id is not None


def test_save_existing_user_updates_scope(workspace):
    user = make_user()
    user.scope = False
    user.save()
    reloaded = User.find_one(user_id=user.id)
    assert reloaded.scope is False


def test_delete_no_id_returns_empty_dict(workspace):
    user = User("unsaved")
    assert user.delete() == {}


def test_delete_removes_referencing_connections(workspace):
    user = make_user()
    conn = make_connection(user=user)
    user.delete()
    assert Connection.find_one(connection_id=conn.id) is None


def test_delete_removes_user_row(workspace):
    user = make_user()
    user_id = user.id
    user.delete()
    assert User.find_one(user_id=user_id) is None


# --- find_all ---

def test_find_all_returns_all_users(workspace):
    make_user(name="alice")
    make_user(name="bob")
    assert len(User.find_all()) == 2


def test_find_all_scope_true_filters(workspace):
    in_scope = make_user(name="alice")
    out_of_scope = make_user(name="bob")
    out_of_scope.scope = False
    out_of_scope.save()

    assert User.find_all(scope=True) == [in_scope]


def test_find_all_scope_false_filters(workspace):
    in_scope = make_user(name="alice")
    out_of_scope = make_user(name="bob")
    out_of_scope.scope = False
    out_of_scope.save()

    assert User.find_all(scope=False) == [out_of_scope]


def test_find_all_found_filters(workspace):
    origin = make_endpoint()
    discovered = make_user(name="alice")
    discovered.found = origin
    discovered.save()
    other = make_user(name="bob")

    results = User.find_all(found=origin)
    assert results == [discovered]
    assert other not in results


def test_find_all_scope_and_found_combined(workspace):
    origin = make_endpoint()
    discovered_in_scope = make_user(name="alice")
    discovered_in_scope.found = origin
    discovered_in_scope.save()
    discovered_out_of_scope = make_user(name="bob")
    discovered_out_of_scope.found = origin
    discovered_out_of_scope.scope = False
    discovered_out_of_scope.save()

    results = User.find_all(scope=True, found=origin)
    assert results == [discovered_in_scope]


# --- find_one ---

def test_find_one_by_user_id_returns_user(workspace):
    user = make_user()
    assert User.find_one(user_id=user.id) == user


def test_find_one_by_name_returns_user(workspace):
    user = make_user()
    assert User.find_one(name=user.name) == user


def test_find_one_unknown_returns_none(workspace):
    assert User.find_one(user_id=99999) is None
    assert User.find_one(name="doesnotexist") is None


def test_find_one_no_args_returns_none(workspace):
    assert User.find_one() is None


# --- __str__ ---

def test_str_returns_name(workspace):
    user = make_user(name="strme")
    assert str(user) == "strme"
