from unittest.mock import MagicMock, patch

import pytest

from baboossh.exceptions import ConnectionClosedError
from baboossh.ext_dir.payload_getfile import BaboosshExt as PayloadGetfile
from baboossh.ext_dir.payload_putfile import BaboosshExt as PayloadPutfile


def make_connection(endpoint="1.2.3.4:22"):
    connection = MagicMock()
    connection.transport = MagicMock()
    connection.endpoint = endpoint
    return connection


def make_stmt(file=None):
    stmt = MagicMock()
    stmt.file = file
    return stmt


# --- payload_getfile ---

def test_getfile_getters():
    assert PayloadGetfile.getModType() == "payload"
    assert PayloadGetfile.getKey() == "getfile"


def test_getfile_extstr():
    assert str(PayloadGetfile) == "getfile"


def test_getfile_raises_when_connection_closed():
    connection = make_connection()
    connection.transport = None
    with pytest.raises(ConnectionClosedError):
        PayloadGetfile.run(connection, "/tmp/wspace", make_stmt("/etc/passwd"))


def test_getfile_missing_file_arg(tmp_path, capsys):
    (tmp_path / "loot").mkdir()
    connection = make_connection()
    stmt = MagicMock(spec=[])
    result = PayloadGetfile.run(connection, str(tmp_path), stmt)
    assert result is False
    assert "must specify a path" in capsys.readouterr().out


def test_getfile_creates_loot_folder_and_returns_true(tmp_path, capsys):
    (tmp_path / "loot").mkdir()
    connection = make_connection()
    sftp = MagicMock()
    with patch("baboossh.ext_dir.payload_getfile.SFTPClient") as sftp_client:
        sftp_client.from_transport.return_value = sftp
        result = PayloadGetfile.run(connection, str(tmp_path), make_stmt("/etc/passwd"))
    assert result is True
    loot_folder = tmp_path / "loot" / "1.2.3.4-22"
    assert loot_folder.is_dir()
    sftp.get.assert_called_once()
    out = capsys.readouterr().out
    assert "Done" in out
    assert "File saved as" in out


def test_getfile_sftp_error_returns_false(tmp_path, capsys):
    (tmp_path / "loot").mkdir()
    connection = make_connection()
    sftp = MagicMock()
    sftp.get.side_effect = OSError("no such file")
    with patch("baboossh.ext_dir.payload_getfile.SFTPClient") as sftp_client:
        sftp_client.from_transport.return_value = sftp
        result = PayloadGetfile.run(connection, str(tmp_path), make_stmt("/etc/passwd"))
    assert result is False
    assert "Error" in capsys.readouterr().out


# --- payload_putfile ---

def test_putfile_getters():
    assert PayloadPutfile.getModType() == "payload"
    assert PayloadPutfile.getKey() == "putfile"


def test_putfile_extstr():
    assert str(PayloadPutfile) == "putfile"


def test_putfile_raises_when_connection_closed():
    connection = make_connection()
    connection.transport = None
    with pytest.raises(ConnectionClosedError):
        PayloadPutfile.run(connection, "/tmp/wspace", make_stmt("/etc/passwd"))


def test_putfile_missing_file_arg(capsys):
    connection = make_connection()
    stmt = MagicMock(spec=[])
    result = PayloadPutfile.run(connection, "/tmp/wspace", stmt)
    assert result is False
    assert "must specify a path" in capsys.readouterr().out


def test_putfile_success_returns_true(tmp_path, capsys):
    connection = make_connection()
    local_file = tmp_path / "myfile.txt"
    local_file.write_text("data")
    sftp = MagicMock()
    with patch("baboossh.ext_dir.payload_putfile.SFTPClient") as sftp_client:
        sftp_client.from_transport.return_value = sftp
        result = PayloadPutfile.run(connection, "/tmp/wspace", make_stmt(str(local_file)))
    assert result is True
    sftp.put.assert_called_once_with(str(local_file), "myfile.txt")
    out = capsys.readouterr().out
    assert "Done" in out
    assert "File pushed as ~/myfile.txt" in out


def test_putfile_sftp_error_returns_false(tmp_path, capsys):
    connection = make_connection()
    local_file = tmp_path / "myfile.txt"
    local_file.write_text("data")
    sftp = MagicMock()
    sftp.put.side_effect = OSError("no such file")
    with patch("baboossh.ext_dir.payload_putfile.SFTPClient") as sftp_client:
        sftp_client.from_transport.return_value = sftp
        result = PayloadPutfile.run(connection, "/tmp/wspace", make_stmt(str(local_file)))
    assert result is False
    assert "Error" in capsys.readouterr().out
