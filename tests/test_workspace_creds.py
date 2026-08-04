import types

from baboossh import Creds, Extensions


def make_creds(content="secret"):
    creds = Creds("password", content)
    creds.save()
    return creds


def test_creds_add_password_creates_creds(workspace):
    Extensions.load()
    stmt = types.SimpleNamespace(value="secret")
    creds_id = workspace.creds_add("password", stmt)
    assert creds_id is not None
    assert len(Creds.find_all()) == 1


def test_creds_show_unknown_id_prints_and_returns_none(workspace, capsys):
    result = workspace.creds_show("#999")
    assert result is None
    assert "not found" in capsys.readouterr().out


def test_creds_show_known_id(workspace, capsys):
    creds = make_creds()
    workspace.creds_show("#" + str(creds.id))
    assert "secret" in capsys.readouterr().out


def test_creds_edit_unknown_id_returns_none(workspace):
    assert workspace.creds_edit("#999") is None


def test_creds_del_unknown_returns_false(workspace):
    assert workspace.creds_del("#999") is False


def test_creds_del_removes_creds(workspace):
    creds = make_creds()
    assert workspace.creds_del("#" + str(creds.id)) is True
    assert Creds.find_all() == []


def test_creds_del_clears_selected_creds_option(workspace):
    creds = make_creds()
    workspace.options["creds"] = creds
    workspace.creds_del("#" + str(creds.id))
    assert workspace.options["creds"] is None
