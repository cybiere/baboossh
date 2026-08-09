from unittest.mock import MagicMock

import pytest

from baboossh.exceptions import ConnectionClosedError
from baboossh.ext_dir.payload_shell import BaboosshExt as PayloadShell


def test_getters():
    assert PayloadShell.getModType() == "payload"
    assert PayloadShell.getKey() == "shell"


def test_extstr():
    assert str(PayloadShell) == "shell"


def test_run_raises_when_connection_closed():
    connection = MagicMock()
    connection.transport = None
    with pytest.raises(ConnectionClosedError):
        PayloadShell.run(connection, "/tmp/wspace", MagicMock())
