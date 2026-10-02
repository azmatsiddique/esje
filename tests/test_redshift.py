"""Tests for RedshiftDriver, Redshift prompt resolution, and top-level Redshift connection helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import esje
from esje.drivers.redshift import RedshiftDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_redshift_credentials


def test_resolve_redshift_credentials_explicit():
    creds = resolve_redshift_credentials(
        host="my-redshift-cluster.eu-west-1.redshift.amazonaws.com",
        port=5439,
        user="my_user",
        password="my_password",
        database="analytics",
        sslmode="require",
        interactive_prompt=False,
    )

    assert creds["host"] == "my-redshift-cluster.eu-west-1.redshift.amazonaws.com"
    assert creds["port"] == 5439
    assert creds["user"] == "my_user"
    assert creds["password"] == "my_password"
    assert creds["database"] == "analytics"
    assert creds["sslmode"] == "require"


def test_resolve_redshift_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_REDSHIFT_HOST", "env_host")
    monkeypatch.setenv("ESJE_REDSHIFT_PORT", "5440")
    monkeypatch.setenv("ESJE_REDSHIFT_USER", "env_user")
    monkeypatch.setenv("ESJE_REDSHIFT_PASSWORD", "env_pass")
    monkeypatch.setenv("ESJE_REDSHIFT_DATABASE", "env_db")
    monkeypatch.setenv("ESJE_REDSHIFT_SSLMODE", "prefer")

    creds = resolve_redshift_credentials(interactive_prompt=False)

    assert creds["host"] == "env_host"
    assert creds["port"] == 5440
    assert creds["user"] == "env_user"
    assert creds["password"] == "env_pass"
    assert creds["database"] == "env_db"
    assert creds["sslmode"] == "prefer"


def test_resolve_redshift_credentials_interactive():
    inputs = ["prompt_host", "5441", "prompt_user", "prompt_db"]
    with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="prompt_pass"):
        creds = resolve_redshift_credentials(interactive_prompt=True)

    assert creds["host"] == "prompt_host"
    assert creds["port"] == 5441
    assert creds["user"] == "prompt_user"
    assert creds["password"] == "prompt_pass"
    assert creds["database"] == "prompt_db"


def test_redshift_driver_dialect_and_url():
    driver = RedshiftDriver(
        host="my-cluster",
        port=5439,
        user="awsuser",
        password="secret/pass",
        database="dev",
        sslmode="require",
    )
    assert driver.dialect == "redshift"
    assert driver.host == "my-cluster"
    url = driver._build_connection_url(driver_prefix="redshift+psycopg2")
    assert "redshift+psycopg2://awsuser:secret%2Fpass@my-cluster:5439/dev" in url
    assert "sslmode=require" in url


def test_redshift_driver_connect_success():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = RedshiftDriver(custom_engine=mock_engine)
    driver.connect()

    mock_conn.execute.assert_called_once()


def test_redshift_driver_connect_auth_failure_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("statement", {}, Exception("password authentication failed"))

    driver = RedshiftDriver(custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Access denied" in str(exc_info.value.hint)


def test_redshift_driver_execute_select():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    expected_df = pd.DataFrame({"id": [1, 2], "val": [100, 200]})

    with patch("pandas.read_sql", return_value=expected_df):
        driver = RedshiftDriver(custom_engine=mock_engine)
        result = driver.execute("SELECT * FROM sales;")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_redshift_driver_execute_dml():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_trans = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5

    mock_conn.begin.return_value = mock_trans
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = RedshiftDriver(custom_engine=mock_engine)
    res = driver.execute("INSERT INTO sales VALUES (1, 100);")

    assert res["status"] == "Query executed successfully"
    assert res["rowcount"] == 5
    mock_trans.commit.assert_called_once()


def test_redshift_driver_execute_sql_error():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = SQLAlchemyError("Redshift SQL Error: Syntax Error")
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = RedshiftDriver(custom_engine=mock_engine)

    with pytest.raises(QueryError):
        driver.execute("INVALID STATEMENT")


def test_redshift_driver_close():
    mock_engine = MagicMock()
    driver = RedshiftDriver(custom_engine=mock_engine)
    driver.close()

    mock_engine.dispose.assert_called_once()
    assert driver._engine is None


def test_top_level_redshift_connect():
    esje.close_all()
    mock_engine = MagicMock()

    conn1 = esje.connect_redshift(name="rs_test", host="test_host", interactive_prompt=False, custom_engine=mock_engine)
    assert conn1.name == "rs_test"
    assert conn1.dialect == "redshift"

    conn2 = esje.connect_rs(name="rs_alias", host="test_host", interactive_prompt=False, custom_engine=mock_engine)
    assert conn2.name == "rs_alias"

    conn3 = esje.connect(dialect="redshift", name="rs_generic", host="test_host", interactive_prompt=False, custom_engine=mock_engine)
    assert conn3.name == "rs_generic"

    df_conns = esje.connections()
    assert len(df_conns) == 3

    esje.close_all()
