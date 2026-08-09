from unittest.mock import MagicMock

import pytest

from baboossh.exceptions import ConnectionClosedError
from baboossh.ext_dir.payload_exec import BaboosshExt as PayloadExec


def make_stmt(cmd=None):
    stmt = MagicMock()
    stmt.cmd = cmd if cmd is not None else ["hostname"]
    return stmt


def test_getters():
    assert PayloadExec.getModType() == "payload"
    assert PayloadExec.getKey() == "exec"


def test_extstr():
    assert str(PayloadExec) == "exec"


def test_run_raises_when_connection_closed():
    connection = MagicMock()
    connection.transport = None
    with pytest.raises(ConnectionClosedError):
        PayloadExec.run(connection, "/tmp/wspace", make_stmt())


def test_run_success(capsys):
    connection = MagicMock()
    connection.transport = MagicMock()
    connection.exec_command.return_value = (0, "hello\n")
    result = PayloadExec.run(connection, "/tmp/wspace", make_stmt(["echo", "hello"]))
    assert result is True
    connection.exec_command.assert_called_once_with("echo hello")
    out = capsys.readouterr().out
    assert "Return code: 0" in out
    assert "hello" in out


def test_run_defaults_to_hostname_when_no_cmd():
    connection = MagicMock()
    connection.transport = MagicMock()
    connection.exec_command.return_value = (0, "myhost\n")
    stmt = MagicMock(spec=[])
    result = PayloadExec.run(connection, "/tmp/wspace", stmt)
    assert result is True
    connection.exec_command.assert_called_once_with("hostname")


def test_run_returns_false_on_exception(capsys):
    connection = MagicMock()
    connection.transport = MagicMock()
    connection.exec_command.side_effect = RuntimeError("boom")
    result = PayloadExec.run(connection, "/tmp/wspace", make_stmt())
    assert result is False
    assert "Error : boom" in capsys.readouterr().out
