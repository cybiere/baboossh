from baboossh import User


def make_user(name="tester"):
    user = User(name)
    user.save()
    return user


def test_user_add_creates_user(workspace):
    workspace.user_add("tester")
    assert len(User.find_all()) == 1


def test_user_del_unknown_returns_false(workspace):
    assert workspace.user_del("tester") is False


def test_user_del_removes_user(workspace):
    make_user()
    assert workspace.user_del("tester") is True
    assert User.find_all() == []


def test_user_del_clears_selected_user_option(workspace):
    make_user()
    workspace.set_option("user", "tester")
    assert workspace.options["user"] is not None
    workspace.user_del("tester")
    assert workspace.options["user"] is None
