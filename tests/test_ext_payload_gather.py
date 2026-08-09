import os
from unittest.mock import MagicMock, patch

import pytest

from baboossh.exceptions import ConnectionClosedError
from baboossh.ext_dir.payload_gather import BaboosshExt as PayloadGather


def make_instance(connection=None, wspace_folder="/tmp/wspace"):
    g = object.__new__(PayloadGather)
    g.connection = connection or MagicMock()
    g.wspaceFolder = wspace_folder
    g.newCreds = []
    g.newUsers = []
    g.newEndpoints = []
    g.keysHash = {}
    g.sftp = MagicMock()
    return g


def test_getters():
    assert PayloadGather.getModType() == "payload"
    assert PayloadGather.getKey() == "gather"


def test_extstr():
    assert str(PayloadGather) == "gather"


def test_run_raises_when_connection_closed():
    connection = MagicMock()
    connection.transport = None
    with pytest.raises(ConnectionClosedError):
        PayloadGather.run(connection, "/tmp/wspace", MagicMock())


def test_run_bug7_exception_is_caught_not_reraised(capsys):
    connection = MagicMock()
    connection.transport = MagicMock()
    with patch.object(PayloadGather, "__init__", return_value=None):
        with patch.object(PayloadGather, "gather", side_effect=RuntimeError("boom")):
            result = PayloadGather.run(connection, "/tmp/wspace", MagicMock())
    assert result is False
    assert "Error : boom" in capsys.readouterr().out


def test_init_builds_keys_hash_and_sftp(tmp_path):
    creds = MagicMock()
    creds.creds_type = "privkey"
    creds.obj.keypath = "/some/key"
    other_creds = MagicMock()
    other_creds.creds_type = "password"

    connection = MagicMock()
    with patch("baboossh.ext_dir.payload_gather.Creds") as creds_cls, \
         patch("baboossh.ext_dir.payload_gather.subprocess.run") as run, \
         patch("baboossh.ext_dir.payload_gather.SFTPClient") as sftp_cls:
        creds_cls.find_all.return_value = [creds, other_creds]
        run.return_value = MagicMock(stdout=b"deadbeef  /some/key\n")
        sftp_cls.from_transport.return_value = MagicMock()
        g = PayloadGather(connection, str(tmp_path))

    assert g.keysHash == {"deadbeef": "/some/key"}
    assert g.newCreds == []
    assert g.newUsers == []
    assert g.newEndpoints == []
    sftp_cls.from_transport.assert_called_once_with(connection.transport)


# --- hostnameToIP ---

def test_hostnameToIP_direct_ip_new_endpoint(tmp_path):
    connection = MagicMock()
    connection.scope = True
    g = make_instance(connection, str(tmp_path))
    with patch("baboossh.ext_dir.payload_gather.Endpoint") as endpoint_cls, \
         patch("baboossh.ext_dir.payload_gather.Path") as path_cls:
        endpoint = MagicMock()
        endpoint.id = None
        endpoint_cls.return_value = endpoint
        path_cls.return_value = MagicMock()
        result = g.hostnameToIP("10.0.0.5")
    endpoint.save.assert_called_once()
    assert g.newEndpoints == [endpoint]
    assert result == [endpoint]


def test_hostnameToIP_loopback_ip_returns_empty(tmp_path):
    g = make_instance(wspace_folder=str(tmp_path))
    result = g.hostnameToIP("127.0.0.1")
    assert result == []


def test_hostnameToIP_hostname_resolves_via_channel(tmp_path):
    connection = MagicMock()
    connection.scope = True
    g = make_instance(connection, str(tmp_path))
    chan = MagicMock()
    chan.recv.side_effect = [b"10.0.0.9\n", b""]
    connection.transport.open_channel.return_value = chan
    with patch("baboossh.ext_dir.payload_gather.Endpoint") as endpoint_cls, \
         patch("baboossh.ext_dir.payload_gather.Path") as path_cls:
        endpoint = MagicMock()
        endpoint.id = None
        endpoint_cls.return_value = endpoint
        path_cls.return_value = MagicMock()
        result = g.hostnameToIP("somehost")
    assert result == [endpoint]
    endpoint.save.assert_called_once()


def test_hostnameToIP_out_of_scope_connection_marks_endpoint(tmp_path):
    connection = MagicMock()
    connection.scope = False
    g = make_instance(connection, str(tmp_path))
    with patch("baboossh.ext_dir.payload_gather.Endpoint") as endpoint_cls, \
         patch("baboossh.ext_dir.payload_gather.Path") as path_cls:
        endpoint = MagicMock()
        endpoint.id = None
        endpoint_cls.return_value = endpoint
        path_cls.return_value = MagicMock()
        g.hostnameToIP("10.0.0.5")
    assert endpoint.scope is False


# --- gatherFromConfig ---

def test_gatherFromConfig_no_sftp_config_file(tmp_path):
    g = make_instance(wspace_folder=str(tmp_path))
    g.sftp.get.side_effect = FileNotFoundError()
    result = g.gatherFromConfig()
    assert result is None


def test_gatherFromConfig_bug13_malformed_line_skipped(tmp_path):
    connection = MagicMock()
    connection.scope = True
    (tmp_path / "loot").mkdir()
    g = make_instance(connection, str(tmp_path))
    config_text = "Host myhost\nMALFORMEDLINE\n  HostName 10.0.0.5\n"

    def fake_get(remote, local):
        with open(local, "w") as f:
            f.write(config_text)

    g.sftp.get.side_effect = fake_get
    with patch.object(g, "hostnameToIP", return_value=[]) as hostname_to_ip:
        g.gatherFromConfig()
    hostname_to_ip.assert_called_once_with("10.0.0.5", None)


def test_gatherFromConfig_parses_user_and_identity(tmp_path):
    connection = MagicMock()
    connection.scope = True
    (tmp_path / "loot").mkdir()
    g = make_instance(connection, str(tmp_path))
    config_text = "Host myhost\n  HostName 10.0.0.5\n  User bob\n  IdentityFile ~/.ssh/id_rsa\n"

    def fake_get(remote, local):
        with open(local, "w") as f:
            f.write(config_text)

    g.sftp.get.side_effect = fake_get
    with patch.object(g, "hostnameToIP", return_value=[]), \
         patch.object(g, "getKeyToCreds", return_value=None) as get_key, \
         patch("baboossh.ext_dir.payload_gather.User") as user_cls:
        user = MagicMock()
        user.id = None
        user_cls.return_value = user
        g.gatherFromConfig()
    assert g.newUsers == [user]
    get_key.assert_called_once_with(".ssh/id_rsa", ".")


# --- gatherFromKnown ---

def test_gatherFromKnown_no_file(tmp_path):
    g = make_instance(wspace_folder=str(tmp_path))
    g.sftp.get.side_effect = FileNotFoundError()
    result = g.gatherFromKnown()
    assert result is None


def test_gatherFromKnown_skips_hashed_entries_and_removes_file(tmp_path):
    (tmp_path / "loot").mkdir()
    g = make_instance(wspace_folder=str(tmp_path))
    content = "|hashedentry ssh-rsa AAAA\n10.0.0.7,myhost ssh-rsa AAAA\n"
    written_paths = []

    def fake_get(remote, local):
        written_paths.append(local)
        with open(local, "w") as f:
            f.write(content)

    g.sftp.get.side_effect = fake_get
    with patch.object(g, "hostnameToIP", return_value=[]) as hostname_to_ip:
        g.gatherFromKnown()
    hostname_to_ip.assert_any_call("10.0.0.7")
    hostname_to_ip.assert_any_call("myhost")
    assert len(written_paths) == 1
    assert not os.path.exists(written_paths[0])


# --- gatherKeys ---

def test_gatherKeys_filters_by_name_and_calls_getKeyToCreds(tmp_path):
    connection = MagicMock()
    g = make_instance(connection, str(tmp_path))
    connection.transport.open_channel.return_value = MagicMock()

    rsa_file = MagicMock(filename="id_rsa", st_size=100)
    empty_file = MagicMock(filename="id_rsa_empty", st_size=0)
    irrelevant_file = MagicMock(filename="notes.txt", st_size=50)
    g.sftp.listdir_attr.return_value = [rsa_file, empty_file, irrelevant_file]

    with patch.object(g, "getKeyToCreds") as get_key:
        g.gatherKeys()
    get_key.assert_called_once_with("id_rsa")


def test_gatherKeys_missing_ssh_dir_is_swallowed(tmp_path):
    connection = MagicMock()
    g = make_instance(connection, str(tmp_path))
    connection.transport.open_channel.return_value = MagicMock()
    g.sftp.listdir_attr.side_effect = FileNotFoundError()
    g.gatherKeys()  # must not raise


# --- getKeyToCreds ---

def test_getKeyToCreds_sftp_get_failure_returns_none(tmp_path, capsys):
    g = make_instance(wspace_folder=str(tmp_path))
    g.sftp.get.side_effect = OSError("no such file")
    result = g.getKeyToCreds("id_rsa")
    assert result is None


def test_getKeyToCreds_duplicate_hash_removes_and_returns_none(tmp_path):
    connection = MagicMock()
    g = make_instance(connection, str(tmp_path))
    g.keysHash = {"deadbeef": "/other/path"}
    keys_folder = tmp_path / "keys"
    keys_folder.mkdir()

    def fake_get(remote, local):
        with open(local, "w") as f:
            f.write("dummy")

    g.sftp.get.side_effect = fake_get
    with patch("baboossh.ext_dir.payload_gather.subprocess.run") as run, \
         patch("baboossh.ext_dir.payload_gather.os.remove") as remove:
        run.return_value = MagicMock(stdout=b"deadbeef  ignored\n")
        result = g.getKeyToCreds("id_rsa")
    assert result is None
    remove.assert_called_once()


def test_getKeyToCreds_valid_key_creates_creds(tmp_path):
    connection = MagicMock()
    connection.scope = True
    connection.endpoint = "1.2.3.4:22"
    connection.user = "bob"
    g = make_instance(connection, str(tmp_path))
    keys_folder = tmp_path / "keys"
    keys_folder.mkdir()

    def fake_get(remote, local):
        with open(local, "w") as f:
            f.write("dummy")

    g.sftp.get.side_effect = fake_get
    with patch("baboossh.ext_dir.payload_gather.subprocess.run") as run, \
         patch("baboossh.extensions.Extensions") as extensions, \
         patch("baboossh.ext_dir.payload_gather.Creds") as creds_cls:
        run.return_value = MagicMock(stdout=b"deadbeef  ignored\n")
        extensions.auths = {"privkey": MagicMock()}
        extensions.auths["privkey"].checkKeyfile.return_value = (True, False)
        cred = MagicMock()
        cred.id = None
        creds_cls.return_value = cred
        result = g.getKeyToCreds("id_rsa")
    assert result is cred
    assert g.newCreds == [cred]
    expected_filepath = str(keys_folder / "1.2.3.4-22_bob_.ssh_id_rsa")
    assert g.keysHash["deadbeef"] == expected_filepath


def test_getKeyToCreds_invalid_key_removed(tmp_path):
    connection = MagicMock()
    g = make_instance(connection, str(tmp_path))
    keys_folder = tmp_path / "keys"
    keys_folder.mkdir()

    def fake_get(remote, local):
        with open(local, "w") as f:
            f.write("dummy")

    g.sftp.get.side_effect = fake_get
    with patch("baboossh.ext_dir.payload_gather.subprocess.run") as run, \
         patch("baboossh.extensions.Extensions") as extensions, \
         patch("baboossh.ext_dir.payload_gather.os.remove") as remove:
        run.return_value = MagicMock(stdout=b"deadbeef  ignored\n")
        extensions.auths = {"privkey": MagicMock()}
        extensions.auths["privkey"].checkKeyfile.return_value = (False, False)
        result = g.getKeyToCreds("id_rsa")
    assert result is None
    remove.assert_called_once()


# --- listHistoryFiles ---

def test_listHistoryFiles_filters_history_and_nonempty(tmp_path):
    g = make_instance(wspace_folder=str(tmp_path))
    bash_history = MagicMock(filename=".bash_history", st_size=200)
    empty_history = MagicMock(filename=".zsh_history", st_size=0)
    other_file = MagicMock(filename=".bashrc", st_size=50)
    g.sftp.listdir_attr.return_value = [bash_history, empty_history, other_file]
    result = g.listHistoryFiles()
    assert result == [".bash_history"]


# --- gatherFromHistory ---

def test_gatherFromHistory_get_failure_returns_none(tmp_path):
    g = make_instance(wspace_folder=str(tmp_path))
    g.sftp.get.side_effect = OSError("no such file")
    result = g.gatherFromHistory(".bash_history")
    assert result is None


def test_gatherFromHistory_parses_ssh_command_line(tmp_path):
    connection = MagicMock()
    connection.scope = True
    (tmp_path / "loot").mkdir()
    g = make_instance(connection, str(tmp_path))
    history_text = "ls -la\nssh -i ~/.ssh/id_rsa -p 2222 bob@10.0.0.9\n"

    def fake_get(remote, local):
        with open(local, "w") as f:
            f.write(history_text)

    g.sftp.get.side_effect = fake_get
    with patch.object(g, "hostnameToIP", return_value=[]) as hostname_to_ip, \
         patch.object(g, "getKeyToCreds", return_value=None) as get_key, \
         patch("baboossh.ext_dir.payload_gather.User") as user_cls:
        user = MagicMock()
        user.id = None
        user_cls.return_value = user
        g.gatherFromHistory(".bash_history")
    hostname_to_ip.assert_called_once_with("10.0.0.9", "2222")
    get_key.assert_called_once_with(".ssh/id_rsa", ".")
    assert g.newUsers == [user]


def test_gatherFromHistory_ignores_non_ssh_lines(tmp_path):
    g = make_instance(wspace_folder=str(tmp_path))
    history_text = "ls -la\ncat file.txt\n"

    def fake_get(remote, local):
        with open(local, "w") as f:
            f.write(history_text)

    g.sftp.get.side_effect = fake_get
    with patch.object(g, "hostnameToIP") as hostname_to_ip:
        g.gatherFromHistory(".bash_history")
    hostname_to_ip.assert_not_called()


# --- gather() orchestration ---

def test_gather_calls_all_phases_and_closes_sftp(tmp_path, capsys):
    connection = MagicMock()
    g = make_instance(connection, str(tmp_path))
    with patch.object(g, "gatherFromConfig") as from_config, \
         patch.object(g, "listHistoryFiles", return_value=[]) as list_history, \
         patch.object(g, "gatherKeys") as gather_keys, \
         patch.object(g, "gatherFromKnown") as from_known:
        g.gather()
    from_config.assert_called_once()
    list_history.assert_called_once()
    gather_keys.assert_called_once()
    from_known.assert_called_once()
    g.sftp.close.assert_called_once()
    assert "Done !" in capsys.readouterr().out
