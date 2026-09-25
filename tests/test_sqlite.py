"""Tests for SQLiteDriver, SQLite prompt resolution, and top-level SQLite connection helpers."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import esje
from esje.drivers.sqlite import SQLiteDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_sqlite_credentials


def test_resolve_sqlite_credentials_explicit():
    creds = resolve_sqlite_credentials(
        database="custom.db",
        read_only=True,
        interactive_prompt=False,
    )

    assert creds["database"] == "custom.db"
    assert creds["read_only"] is True


def test_resolve_sqlite_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_SQLITE_DATABASE", "env_sqlite.db")
    monkeypatch.setenv("ESJE_SQLITE_READ_ONLY", "true")

    creds = resolve_sqlite_credentials(interactive_prompt=False)

    assert creds["database"] == "env_sqlite.db"
    assert creds["read_only"] is True


def test_resolve_sqlite_credentials_interactive():
    with patch("builtins.input", return_value="prompt_db.sqlite"):
        creds = resolve_sqlite_credentials(interactive_prompt=True)

    assert creds["database"] == "prompt_db.sqlite"


def test_sqlite_driver_dialect_and_url():
    driver_mem = SQLiteDriver(database=":memory:")
    assert driver_mem.dialect == "sqlite"
    assert driver_mem._build_connection_url() == "sqlite:///:memory:"

    driver_file = SQLiteDriver(database="test.db")
    url_file = driver_file._build_connection_url()
    assert "sqlite:///" in url_file
    assert "test.db" in url_file

    driver_ro = SQLiteDriver(database="test.db", read_only=True)
    url_ro = driver_ro._build_connection_url()
    assert "mode=ro" in url_ro


def test_sqlite_driver_connect_and_execute_memory():
    driver = SQLiteDriver(database=":memory:")
    driver.connect()

    # DDL
    create_res = driver.execute("CREATE TABLE users (id INT, name TEXT);")
    assert create_res["status"] == "Query executed successfully"

    # DML
    insert_res = driver.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');")
    assert insert_res["status"] == "Query executed successfully"
    assert insert_res["rowcount"] == 2

    # SELECT
    df = driver.execute("SELECT * FROM users ORDER BY id;")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df["name"]) == ["Alice", "Bob"]

    # PRAGMA
    df_pragma = driver.execute("PRAGMA table_info(users);")
    assert isinstance(df_pragma, pd.DataFrame)
    assert len(df_pragma) == 2

    driver.close()


def test_sqlite_driver_connect_file():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        driver = SQLiteDriver(database=tmp_path)
        driver.connect()

        driver.execute("CREATE TABLE test_table (val TEXT);")
        driver.execute("INSERT INTO test_table VALUES ('hello');")

        df = driver.execute("SELECT * FROM test_table;")
        assert len(df) == 1
        assert df.iloc[0]["val"] == "hello"

        driver.close()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_sqlite_driver_connect_error():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError(
        "statement", {}, Exception("unable to open database file")
    )

    driver = SQLiteDriver(database="/invalid_path/nonexistent.db", custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Unable to open SQLite database" in str(exc_info.value.hint)


def test_sqlite_driver_execute_sql_error():
    driver = SQLiteDriver(database=":memory:")
    driver.connect()

    with pytest.raises(QueryError):
        driver.execute("SELECT * FROM non_existent_table;")

    driver.close()


def test_top_level_sqlite_connect():
    esje.close_all()

    conn1 = esje.connect_sqlite(name="sq_memory", database=":memory:", interactive_prompt=False)
    assert conn1.name == "sq_memory"
    assert conn1.dialect == "sqlite"

    conn2 = esje.connect_sqlite3(name="sq_alias", database=":memory:", interactive_prompt=False)
    assert conn2.name == "sq_alias"

    conn3 = esje.connect(dialect="sqlite", name="sq_generic", database=":memory:", interactive_prompt=False)
    assert conn3.name == "sq_generic"

    conn4 = esje.connect(dialect="sqlite3", name="sq3_generic", database=":memory:", interactive_prompt=False)
    assert conn4.name == "sq3_generic"

    df_conns = esje.connections()
    assert len(df_conns) == 4

    esje.close_all()
