"""Tests for DuckDBDriver, DuckDB prompt resolution, and top-level DuckDB connection helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import esje
from esje.drivers.duckdb import DuckDBDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_duckdb_credentials


def test_resolve_duckdb_credentials_explicit():
    creds = resolve_duckdb_credentials(
        database="analytics.duckdb",
        read_only=True,
        interactive_prompt=False,
    )

    assert creds["database"] == "analytics.duckdb"
    assert creds["read_only"] is True


def test_resolve_duckdb_credentials_defaults():
    creds = resolve_duckdb_credentials(interactive_prompt=False)

    assert creds["database"] == ":memory:"
    assert creds["read_only"] is False


def test_resolve_duckdb_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_DUCKDB_DATABASE", "env_duck.db")
    monkeypatch.setenv("ESJE_DUCKDB_READ_ONLY", "true")

    creds = resolve_duckdb_credentials(interactive_prompt=False)

    assert creds["database"] == "env_duck.db"
    assert creds["read_only"] is True


def test_resolve_duckdb_credentials_interactive():
    with patch("builtins.input", return_value="interactive.duckdb"):
        creds = resolve_duckdb_credentials(interactive_prompt=True)

    assert creds["database"] == "interactive.duckdb"


def test_duckdb_driver_dialect_and_host():
    driver = DuckDBDriver(database=":memory:")
    assert driver.dialect == "duckdb"
    assert driver.host == ":memory:"
    assert driver.user == "duckdb"


def test_duckdb_driver_connect_success():
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_conn.execute.return_value = mock_res

    driver = DuckDBDriver(custom_connection=mock_conn)
    driver.connect()

    mock_conn.execute.assert_called_once_with("SELECT 1")


def test_duckdb_driver_execute_select():
    mock_conn = MagicMock()
    mock_res = MagicMock()
    expected_df = pd.DataFrame({"id": [101, 102], "name": ["Widget A", "Widget B"]})
    mock_res.df.return_value = expected_df
    mock_conn.execute.return_value = mock_res

    driver = DuckDBDriver(custom_connection=mock_conn)
    result = driver.execute("SELECT * FROM widgets")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    mock_conn.execute.assert_called_with("SELECT * FROM widgets")


def test_duckdb_driver_execute_dml():
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_res.rowcount = 5
    mock_conn.execute.return_value = mock_res

    driver = DuckDBDriver(custom_connection=mock_conn)
    res = driver.execute("CREATE TABLE t (id INT)")

    assert res["status"] == "Query executed successfully"
    assert res["rowcount"] == 5


def test_duckdb_driver_execute_query_error():
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("Catalog Error: Table does not exist")

    driver = DuckDBDriver(custom_connection=mock_conn)

    with pytest.raises(QueryError):
        driver.execute("SELECT * FROM missing_table")


def test_duckdb_driver_close():
    mock_conn = MagicMock()
    driver = DuckDBDriver(custom_connection=mock_conn)
    driver.close()

    mock_conn.close.assert_called_once()
    assert driver._conn is None


def test_top_level_duckdb_connect():
    esje.close_all()
    mock_conn = MagicMock()

    conn1 = esje.connect_duckdb(name="duck_test", interactive_prompt=False, custom_connection=mock_conn)
    assert conn1.name == "duck_test"
    assert conn1.dialect == "duckdb"

    conn2 = esje.connect(dialect="duckdb", name="duck_generic", interactive_prompt=False, custom_connection=mock_conn)
    assert conn2.name == "duck_generic"

    conn3 = esje.connect(dialect="duck", name="duck_alias", interactive_prompt=False, custom_connection=mock_conn)
    assert conn3.name == "duck_alias"

    df_conns = esje.connections()
    assert len(df_conns) == 3

    esje.close_all()
