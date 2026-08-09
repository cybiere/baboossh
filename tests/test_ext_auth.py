import json
from unittest.mock import MagicMock

import paramiko
import pytest

from baboossh.ext_dir.auth_password import BaboosshExt as AuthPassword
from baboossh.ext_dir.auth_privkey import BaboosshExt as AuthPrivkey


# --- auth_password ---

def test_password_getters():
    assert AuthPassword.getModType() == "auth"
    assert AuthPassword.getKey() == "password"


def test_password_extstr_regression():
    assert str(AuthPassword) == "password"


def test_password_fromStatement():
    stmt = MagicMock()
    vars_dict = {"value": "hunter2"}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("builtins.vars", lambda s: vars_dict)
        assert AuthPassword.fromStatement(stmt) == "hunter2"


def test_password_init_and_serialize():
    creds = AuthPassword("hunter2")
    assert creds.creds == "hunter2"
    assert creds.serialize() == "hunter2"
    assert creds.identifier == "hunter2"
    assert creds.toList() == "hunter2"


def test_password_auth_calls_transport():
    creds = AuthPassword("hunter2")
    transport = MagicMock()
    assert creds.auth("bob", transport) is True
    transport.auth_password.assert_called_once_with("bob", "hunter2")


def test_password_show_and_edit(capsys):
    creds = AuthPassword("hunter2")
    creds.show()
    assert "hunter2" in capsys.readouterr().out
    creds.edit()
    assert "Nothing to edit" in capsys.readouterr().out
    assert creds.delete() is None


# --- auth_privkey ---

def test_privkey_getters():
    assert AuthPrivkey.getModType() == "auth"
    assert AuthPrivkey.getKey() == "privkey"


def test_privkey_extstr_regression():
    assert str(AuthPrivkey) == "privkey"


@pytest.fixture
def keyfile_no_pass(tmp_path):
    key = paramiko.RSAKey.generate(1024)
    path = tmp_path / "id_rsa"
    key.write_private_key_file(str(path))
    return str(path)


@pytest.fixture
def keyfile_with_pass(tmp_path):
    key = paramiko.RSAKey.generate(1024)
    path = tmp_path / "id_rsa_pass"
    key.write_private_key_file(str(path), password="s3cret")
    return str(path)


def test_checkKeyfile_empty_file(tmp_path, capsys):
    path = tmp_path / "empty"
    path.write_text("")
    valid, haspass = AuthPrivkey.checkKeyfile(str(path))
    assert (valid, haspass) == (False, False)
    assert "Ignoring" in capsys.readouterr().out


def test_checkKeyfile_missing_file(capsys):
    valid, haspass = AuthPrivkey.checkKeyfile("/nonexistent/path/to/key")
    assert (valid, haspass) == (False, False)
    assert "could not open" in capsys.readouterr().out


def test_checkKeyfile_invalid_content(tmp_path):
    path = tmp_path / "garbage"
    path.write_text("not a key")
    valid, haspass = AuthPrivkey.checkKeyfile(str(path))
    assert (valid, haspass) == (False, False)


def test_checkKeyfile_valid_no_passphrase(keyfile_no_pass):
    valid, haspass = AuthPrivkey.checkKeyfile(keyfile_no_pass)
    assert (valid, haspass) == (True, False)


def test_checkKeyfile_valid_with_passphrase(keyfile_with_pass):
    valid, haspass = AuthPrivkey.checkKeyfile(keyfile_with_pass)
    assert (valid, haspass) == (True, True)


def test_checkPassphrase_correct(keyfile_with_pass):
    assert AuthPrivkey.checkPassphrase(keyfile_with_pass, "s3cret") is True


def test_checkPassphrase_incorrect(keyfile_with_pass):
    assert AuthPrivkey.checkPassphrase(keyfile_with_pass, "wrong") is False


def test_init_missing_keypath_raises():
    with pytest.raises(ValueError):
        AuthPrivkey(json.dumps({"nope": "value"}))


def test_init_defaults_without_haspass():
    creds = AuthPrivkey(json.dumps({"keypath": "/some/path"}))
    assert creds.keypath == "/some/path"
    assert creds.haspass is False
    assert creds.passphrase == ""


def test_init_with_haspass_no_passphrase_key():
    creds = AuthPrivkey(json.dumps({"keypath": "/some/path", "haspass": True}))
    assert creds.haspass is True
    assert creds.passphrase == ""


def test_init_full_roundtrip_via_serialize(keyfile_with_pass):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass,
        "haspass": True,
        "passphrase": "s3cret",
    }))
    assert json.loads(creds.serialize()) == {
        "passphrase": "s3cret",
        "keypath": keyfile_with_pass,
        "haspass": True,
    }


def test_auth_no_passphrase_success(keyfile_no_pass):
    creds = AuthPrivkey(json.dumps({"keypath": keyfile_no_pass, "haspass": False}))
    transport = MagicMock()
    assert creds.auth("bob", transport) is True
    transport.auth_publickey.assert_called_once()
    assert transport.auth_publickey.call_args[0][0] == "bob"


def test_auth_with_correct_passphrase(keyfile_with_pass):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "s3cret",
    }))
    transport = MagicMock()
    assert creds.auth("bob", transport) is True


def test_auth_unknown_passphrase_raises(keyfile_with_pass):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "",
    }))
    transport = MagicMock()
    with pytest.raises(ValueError):
        creds.auth("bob", transport)


def test_auth_wrong_passphrase_returns_false(keyfile_with_pass):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "wrong",
    }))
    transport = MagicMock()
    assert creds.auth("bob", transport) is False
    transport.auth_publickey.assert_not_called()


def test_identifier_and_toList_no_pass(keyfile_no_pass):
    creds = AuthPrivkey(json.dumps({"keypath": keyfile_no_pass, "haspass": False}))
    assert creds.identifier == keyfile_no_pass
    assert creds.toList() == keyfile_no_pass


def test_toList_haspass_unknown_passphrase(keyfile_with_pass):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "",
    }))
    assert creds.toList() == keyfile_with_pass + " > [?]"


def test_toList_haspass_known_passphrase(keyfile_with_pass):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "s3cret",
    }))
    assert creds.toList() == keyfile_with_pass + " > s3cret"


def test_show_no_passphrase(keyfile_no_pass, capsys):
    creds = AuthPrivkey(json.dumps({"keypath": keyfile_no_pass, "haspass": False}))
    creds.show()
    out = capsys.readouterr().out
    assert keyfile_no_pass in out
    assert "Has passphrase? False" in out


def test_show_haspass_unknown(keyfile_with_pass, capsys):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "",
    }))
    creds.show()
    assert "Passphrase unknown" in capsys.readouterr().out


def test_show_haspass_known(keyfile_with_pass, capsys):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "s3cret",
    }))
    creds.show()
    assert "Passphrase: s3cret" in capsys.readouterr().out


def test_edit_no_haspass(keyfile_no_pass, capsys):
    creds = AuthPrivkey(json.dumps({"keypath": keyfile_no_pass, "haspass": False}))
    creds.edit()
    assert "doesn't have a passphrase" in capsys.readouterr().out


def test_edit_already_known(keyfile_with_pass, capsys):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "s3cret",
    }))
    creds.edit()
    assert "already defined" in capsys.readouterr().out


def test_edit_prompts_and_accepts_valid_passphrase(keyfile_with_pass, capsys, monkeypatch):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "",
    }))
    monkeypatch.setattr("builtins.input", lambda _: "s3cret")
    creds.edit()
    assert creds.passphrase == "s3cret"
    assert "Passphrase valid" in capsys.readouterr().out


def test_edit_prompts_and_rejects_invalid_passphrase(keyfile_with_pass, capsys, monkeypatch):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "",
    }))
    monkeypatch.setattr("builtins.input", lambda _: "wrong")
    creds.edit()
    assert creds.passphrase == ""
    assert "Invalid passphrase" in capsys.readouterr().out


def test_edit_empty_input_saves_nothing(keyfile_with_pass, capsys, monkeypatch):
    creds = AuthPrivkey(json.dumps({
        "keypath": keyfile_with_pass, "haspass": True, "passphrase": "",
    }))
    monkeypatch.setattr("builtins.input", lambda _: "")
    creds.edit()
    assert creds.passphrase == ""
    assert "No changes saved" in capsys.readouterr().out


def test_delete_is_noop(keyfile_no_pass):
    creds = AuthPrivkey(json.dumps({"keypath": keyfile_no_pass, "haspass": False}))
    assert creds.delete() is None
