"""Tests for Connection and ConnectionManager."""

from unittest.mock import MagicMock

import pytest

import esje
from esje.connection import Connection, ConnectionManager
from esje.drivers.base import BaseDriver
from esje.errors import ConfigurationError, ConnectionError


class DummyDriver(BaseDriver):
    def __init__(self, host="localhost", port=3306, user="admin", password="supersecretpassword", database="testdb"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.closed = False

    @property
    def dialect(self) -> str:
        return "mysql"

    def connect(self) -> None:
        pass

    def execute(self, query: str):
        return {"status": "ok"}

    def close(self) -> None:
        self.closed = True


def test_connection_repr_masks_password():
    driver = DummyDriver()
    conn = Connection("default", driver)
    repr_str = repr(conn)

    assert "supersecretpassword" not in repr_str
    assert "user='admin'" in repr_str
    assert "host='localhost:3306'" in repr_str
    assert "name='default'" in repr_str


def test_connection_manager_ops():
    cm = ConnectionManager()

    # Empty state raises ConnectionError
    with pytest.raises(ConnectionError):
        cm.get()

    d1 = DummyDriver()
    c1 = Connection("conn1", d1)
    cm.add(c1)

    assert cm.active_name == "conn1"
    assert cm.get().name == "conn1"

    d2 = DummyDriver(database="db2")
    c2 = Connection("conn2", d2)
    cm.add(c2, set_active=False)

    assert cm.active_name == "conn1"
    assert cm.get("conn2").name == "conn2"

    cm.use("conn2")
    assert cm.active_name == "conn2"

    conn_list = cm.list_connections()
    assert len(conn_list) == 2
    assert conn_list[1]["name"] == "conn2"
    assert conn_list[1]["active"] == "*"

    cm.close("conn1")
    assert d1.closed is True
    assert len(cm.list_connections()) == 1

    cm.close_all()
    assert d2.closed is True
    assert len(cm.list_connections()) == 0
    assert cm.active_name is None


def test_top_level_api_functions(monkeypatch):
    esje.close_all()
    mock_engine = MagicMock()

    c = esje.connect_mysql(name="test_conn", interactive_prompt=False, custom_engine=mock_engine)
    assert c.name == "test_conn"

    df_conns = esje.connections()
    assert len(df_conns) == 1
    assert df_conns.iloc[0]["name"] == "test_conn"

    msg = esje.use("test_conn")
    assert "test_conn" in msg

    esje.close("test_conn")
    assert len(esje.connections()) == 0
