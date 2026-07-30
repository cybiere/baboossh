import os
import sqlite3
import threading

import pytest

from baboossh.db import Db


@pytest.fixture
def db_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr("baboossh.db.WORKSPACES_DIR", str(tmp_path))
    name = "dbtestws"
    os.mkdir(os.path.join(tmp_path, name))
    Db.build(name)
    yield name
    try:
        Db.close()
    except (AttributeError, sqlite3.ProgrammingError):
        pass


def test_get_before_connect_raises(db_workspace):
    with pytest.raises(ValueError):
        Db.get()


def test_connect_then_get_returns_connection(db_workspace):
    Db.connect(db_workspace)
    conn = Db.get()
    assert isinstance(conn, sqlite3.Connection)


def test_connect_missing_workspace_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("baboossh.db.WORKSPACES_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        Db.connect("doesnotexist")


def test_close_then_get_raises(db_workspace):
    Db.connect(db_workspace)
    Db.get()
    Db.close()
    with pytest.raises(ValueError):
        Db.get()


def test_get_from_spawned_thread_uses_separate_connection(db_workspace):
    Db.connect(db_workspace)
    main_conn = Db.get()

    results = {}

    def worker():
        results["conn"] = Db.get()

    t = threading.Thread(target=worker, name="db-test-worker")
    t.start()
    t.join()

    assert isinstance(results["conn"], sqlite3.Connection)
    assert results["conn"] is not main_conn
