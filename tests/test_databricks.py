"""Tests for DatabricksDriver, Databricks prompt resolution, and top-level Databricks connection helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import esje
from esje.drivers.databricks import DatabricksDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_databricks_credentials


def test_resolve_databricks_credentials_explicit():
    creds = resolve_databricks_credentials(
        host="adb-123456.cloud.databricks.com",
        token="dapi12345",
        http_path="/sql/1.0/warehouses/abc",
        catalog="main",
        schema="default",
        port=443,
        interactive_prompt=False,
    )

    assert creds["host"] == "adb-123456.cloud.databricks.com"
    assert creds["token"] == "dapi12345"
    assert creds["http_path"] == "/sql/1.0/warehouses/abc"
    assert creds["catalog"] == "main"
    assert creds["schema"] == "default"
    assert creds["port"] == 443


def test_resolve_databricks_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_DATABRICKS_HOST", "env_host")
    monkeypatch.setenv("ESJE_DATABRICKS_TOKEN", "env_token")
    monkeypatch.setenv("ESJE_DATABRICKS_HTTP_PATH", "env_path")
    monkeypatch.setenv("ESJE_DATABRICKS_CATALOG", "env_catalog")
    monkeypatch.setenv("ESJE_DATABRICKS_SCHEMA", "env_schema")
    monkeypatch.setenv("ESJE_DATABRICKS_PORT", "444")

    creds = resolve_databricks_credentials(interactive_prompt=False)

    assert creds["host"] == "env_host"
    assert creds["token"] == "env_token"
    assert creds["http_path"] == "env_path"
    assert creds["catalog"] == "env_catalog"
    assert creds["schema"] == "env_schema"
    assert creds["port"] == 444


def test_resolve_databricks_credentials_interactive():
    inputs = ["prompt_host", "prompt_path", "prompt_catalog", "prompt_schema", "445"]
    with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="prompt_token"):
        creds = resolve_databricks_credentials(interactive_prompt=True)

    assert creds["host"] == "prompt_host"
    assert creds["http_path"] == "prompt_path"
    assert creds["token"] == "prompt_token"
    assert creds["catalog"] == "prompt_catalog"
    assert creds["schema"] == "prompt_schema"
    assert creds["port"] == 445


def test_databricks_driver_dialect_and_url():
    driver = DatabricksDriver(
        host="adb-123456.cloud.databricks.com",
        token="dapi_token",
        http_path="/sql/1.0/warehouses/123",
        catalog="main",
        schema="public",
        port=443,
    )
    assert driver.dialect == "databricks"
    assert driver.host == "adb-123456.cloud.databricks.com"
    url = driver._build_connection_url()
    assert "databricks://token:dapi_token@adb-123456.cloud.databricks.com:443" in url
    assert "http_path=%2Fsql%2F1.0%2Fwarehouses%2F123" in url
    assert "catalog=main" in url
    assert "schema=public" in url


def test_databricks_driver_connect_success():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = DatabricksDriver(custom_engine=mock_engine)
    driver.connect()

    mock_conn.execute.assert_called_once()


def test_databricks_driver_connect_auth_failure_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("statement", {}, Exception("Invalid token"))

    driver = DatabricksDriver(custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Access denied" in str(exc_info.value.hint)


def test_databricks_driver_execute_select():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    expected_df = pd.DataFrame({"id": [1, 2], "val": [100, 200]})

    with patch("pandas.read_sql", return_value=expected_df):
        driver = DatabricksDriver(custom_engine=mock_engine)
        result = driver.execute("SELECT * FROM sales;")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_databricks_driver_execute_dml():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_trans = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5

    mock_conn.begin.return_value = mock_trans
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = DatabricksDriver(custom_engine=mock_engine)
    res = driver.execute("INSERT INTO sales VALUES (1, 100);")

    assert res["status"] == "Query executed successfully"
    assert res["rowcount"] == 5
    mock_trans.commit.assert_called_once()


def test_databricks_driver_execute_sql_error():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = SQLAlchemyError("Databricks SQL Error: Syntax Error")
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = DatabricksDriver(custom_engine=mock_engine)

    with pytest.raises(QueryError):
        driver.execute("INVALID STATEMENT")


def test_databricks_driver_close():
    mock_engine = MagicMock()
    driver = DatabricksDriver(custom_engine=mock_engine)
    driver.close()

    mock_engine.dispose.assert_called_once()
    assert driver._engine is None


def test_top_level_databricks_connect():
    esje.close_all()
    mock_engine = MagicMock()

    conn1 = esje.connect_databricks(name="dbx_test", host="test_host", interactive_prompt=False, custom_engine=mock_engine)
    assert conn1.name == "dbx_test"
    assert conn1.dialect == "databricks"

    conn2 = esje.connect_dbx(name="dbx_alias", host="test_host", interactive_prompt=False, custom_engine=mock_engine)
    assert conn2.name == "dbx_alias"

    conn3 = esje.connect(dialect="databricks", name="dbx_generic", host="test_host", interactive_prompt=False, custom_engine=mock_engine)
    assert conn3.name == "dbx_generic"

    df_conns = esje.connections()
    assert len(df_conns) == 3

    esje.close_all()
