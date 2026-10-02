"""Tests for SnowflakeDriver, Snowflake prompt resolution, and top-level Snowflake connection helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import esje
from esje.drivers.snowflake import SnowflakeDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_snowflake_credentials


def test_resolve_snowflake_credentials_explicit():
    creds = resolve_snowflake_credentials(
        account="orgname-accountname",
        user="sf_user",
        password="sf_password",
        database="analytics",
        schema="public",
        warehouse="compute_wh",
        role="sysadmin",
        authenticator="externalbrowser",
        interactive_prompt=False,
    )

    assert creds["account"] == "orgname-accountname"
    assert creds["user"] == "sf_user"
    assert creds["password"] == "sf_password"
    assert creds["database"] == "analytics"
    assert creds["schema"] == "public"
    assert creds["warehouse"] == "compute_wh"
    assert creds["role"] == "sysadmin"
    assert creds["authenticator"] == "externalbrowser"


def test_resolve_snowflake_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_SNOWFLAKE_ACCOUNT", "env_account")
    monkeypatch.setenv("ESJE_SNOWFLAKE_USER", "env_user")
    monkeypatch.setenv("ESJE_SNOWFLAKE_PASSWORD", "env_pass")
    monkeypatch.setenv("ESJE_SNOWFLAKE_DATABASE", "env_db")
    monkeypatch.setenv("ESJE_SNOWFLAKE_SCHEMA", "env_schema")
    monkeypatch.setenv("ESJE_SNOWFLAKE_WAREHOUSE", "env_wh")
    monkeypatch.setenv("ESJE_SNOWFLAKE_ROLE", "env_role")

    creds = resolve_snowflake_credentials(interactive_prompt=False)

    assert creds["account"] == "env_account"
    assert creds["user"] == "env_user"
    assert creds["password"] == "env_pass"
    assert creds["database"] == "env_db"
    assert creds["schema"] == "env_schema"
    assert creds["warehouse"] == "env_wh"
    assert creds["role"] == "env_role"


def test_resolve_snowflake_credentials_interactive():
    inputs = ["prompt_account", "prompt_user", "prompt_db", "prompt_wh", "prompt_role"]
    with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="prompt_pass"):
        creds = resolve_snowflake_credentials(interactive_prompt=True)

    assert creds["account"] == "prompt_account"
    assert creds["user"] == "prompt_user"
    assert creds["password"] == "prompt_pass"
    assert creds["database"] == "prompt_db"
    assert creds["warehouse"] == "prompt_wh"
    assert creds["role"] == "prompt_role"


def test_snowflake_driver_dialect_and_url():
    driver = SnowflakeDriver(
        account="xy12345.us-east-1",
        user="myuser",
        password="secret/pass",
        database="sales_db",
        schema="public",
        warehouse="small_wh",
        role="analyst",
    )
    assert driver.dialect == "snowflake"
    assert driver.host == "xy12345.us-east-1"
    url = driver._build_connection_url()
    assert "snowflake://myuser:secret%2Fpass@xy12345.us-east-1/sales_db/public" in url
    assert "warehouse=small_wh" in url
    assert "role=analyst" in url


def test_snowflake_driver_connect_success():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = SnowflakeDriver(custom_engine=mock_engine)
    driver.connect()

    mock_conn.execute.assert_called_once()


def test_snowflake_driver_connect_auth_failure_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("statement", {}, Exception("Incorrect username or password"))

    driver = SnowflakeDriver(custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Access denied" in str(exc_info.value.hint)


def test_snowflake_driver_execute_select():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    expected_df = pd.DataFrame({"id": [1, 2], "val": [100, 200]})

    with patch("pandas.read_sql", return_value=expected_df):
        driver = SnowflakeDriver(custom_engine=mock_engine)
        result = driver.execute("SELECT * FROM sales;")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_snowflake_driver_execute_dml():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_trans = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5

    mock_conn.begin.return_value = mock_trans
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = SnowflakeDriver(custom_engine=mock_engine)
    res = driver.execute("INSERT INTO sales VALUES (1, 100);")

    assert res["status"] == "Query executed successfully"
    assert res["rowcount"] == 5
    mock_trans.commit.assert_called_once()


def test_snowflake_driver_execute_sql_error():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = SQLAlchemyError("Snowflake SQL Error: Syntax Error")
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = SnowflakeDriver(custom_engine=mock_engine)

    with pytest.raises(QueryError):
        driver.execute("INVALID STATEMENT")


def test_snowflake_driver_close():
    mock_engine = MagicMock()
    driver = SnowflakeDriver(custom_engine=mock_engine)
    driver.close()

    mock_engine.dispose.assert_called_once()
    assert driver._engine is None


def test_top_level_snowflake_connect():
    esje.close_all()
    mock_engine = MagicMock()

    conn1 = esje.connect_snowflake(name="sf_test", account="test_acc", interactive_prompt=False, custom_engine=mock_engine)
    assert conn1.name == "sf_test"
    assert conn1.dialect == "snowflake"

    conn2 = esje.connect_sf(name="sf_alias", account="test_acc", interactive_prompt=False, custom_engine=mock_engine)
    assert conn2.name == "sf_alias"

    conn3 = esje.connect(dialect="snowflake", name="sf_generic", account="test_acc", interactive_prompt=False, custom_engine=mock_engine)
    assert conn3.name == "sf_generic"

    conn4 = esje.connect(dialect="sf", name="sf2_generic", account="test_acc", interactive_prompt=False, custom_engine=mock_engine)
    assert conn4.name == "sf2_generic"

    df_conns = esje.connections()
    assert len(df_conns) == 4

    esje.close_all()
