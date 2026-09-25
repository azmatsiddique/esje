"""Tests for CockroachDBDriver, CockroachDB prompt resolution, and top-level CockroachDB connection helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import esje
from esje.drivers.cockroachdb import CockroachDBDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_cockroachdb_credentials


def test_resolve_cockroachdb_credentials_explicit():
    creds = resolve_cockroachdb_credentials(
        host="crdb.example.com",
        port=26258,
        user="mycruser",
        password="secretpassword",
        database="mydb",
        sslmode="require",
        interactive_prompt=False,
    )

    assert creds["host"] == "crdb.example.com"
    assert creds["port"] == 26258
    assert creds["user"] == "mycruser"
    assert creds["password"] == "secretpassword"
    assert creds["database"] == "mydb"
    assert creds["sslmode"] == "require"


def test_resolve_cockroachdb_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_COCKROACH_HOST", "envcrhost")
    monkeypatch.setenv("ESJE_COCKROACH_PORT", "26259")
    monkeypatch.setenv("ESJE_COCKROACH_USER", "envcruser")
    monkeypatch.setenv("ESJE_COCKROACH_PASSWORD", "envcrpass")
    monkeypatch.setenv("ESJE_COCKROACH_DATABASE", "envcrdb")
    monkeypatch.setenv("ESJE_COCKROACH_SSLMODE", "require")

    creds = resolve_cockroachdb_credentials(interactive_prompt=False)

    assert creds["host"] == "envcrhost"
    assert creds["port"] == 26259
    assert creds["user"] == "envcruser"
    assert creds["password"] == "envcrpass"
    assert creds["database"] == "envcrdb"
    assert creds["sslmode"] == "require"


def test_resolve_cockroachdb_credentials_interactive():
    inputs = ["prompt_crhost", "26260", "prompt_cruser", "prompt_crdb"]
    with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="prompt_crpass"):
        creds = resolve_cockroachdb_credentials(interactive_prompt=True)

    assert creds["host"] == "prompt_crhost"
    assert creds["port"] == 26260
    assert creds["user"] == "prompt_cruser"
    assert creds["password"] == "prompt_crpass"
    assert creds["database"] == "prompt_crdb"


def test_cockroachdb_driver_dialect_and_url():
    driver = CockroachDBDriver(
        host="localhost",
        port=26257,
        user="root",
        password="p@ss/word",
        database="movr",
        sslmode="require",
    )
    assert driver.dialect == "cockroachdb"
    url = driver._build_connection_url()
    assert "postgresql+psycopg2://root:p%40ss%2Fword@localhost:26257/movr?sslmode=require" in url


def test_cockroachdb_driver_connect_success():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = CockroachDBDriver(custom_engine=mock_engine)
    driver.connect()

    mock_conn.execute.assert_called_once()


def test_cockroachdb_driver_connect_auth_failure_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("statement", {}, Exception("FATAL: password authentication failed for user 'root'"))

    driver = CockroachDBDriver(custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Access denied" in str(exc_info.value.hint)


def test_cockroachdb_driver_connect_refused_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("statement", {}, Exception("could not connect to server: Connection refused"))

    driver = CockroachDBDriver(host="127.0.0.1", port=26257, custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Failed to connect to CockroachDB server" in str(exc_info.value.hint)


def test_cockroachdb_driver_execute_select():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    expected_df = pd.DataFrame({"id": [1, 2], "city": ["New York", "Chicago"]})

    with patch("pandas.read_sql", return_value=expected_df):
        driver = CockroachDBDriver(custom_engine=mock_engine)
        result = driver.execute("SELECT * FROM users;")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_cockroachdb_driver_execute_dml():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_trans = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5

    mock_conn.begin.return_value = mock_trans
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = CockroachDBDriver(custom_engine=mock_engine)
    res = driver.execute("UPDATE users SET credit_rating = 800 WHERE city = 'Chicago';")

    assert res["status"] == "Query executed successfully"
    assert res["rowcount"] == 5
    mock_trans.commit.assert_called_once()


def test_cockroachdb_driver_execute_sql_error():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = SQLAlchemyError("syntax error at or near 'SELECT'")
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = CockroachDBDriver(custom_engine=mock_engine)

    with pytest.raises(QueryError):
        driver.execute("UPDATE invalid table")


def test_cockroachdb_driver_close():
    mock_engine = MagicMock()
    driver = CockroachDBDriver(custom_engine=mock_engine)
    driver.close()

    mock_engine.dispose.assert_called_once()
    assert driver._engine is None


def test_top_level_cockroachdb_connect():
    esje.close_all()
    mock_engine = MagicMock()

    conn1 = esje.connect_cockroachdb(name="cr_test", interactive_prompt=False, custom_engine=mock_engine)
    assert conn1.name == "cr_test"
    assert conn1.dialect == "cockroachdb"

    conn2 = esje.connect_cockroach(name="cr_alias1", interactive_prompt=False, custom_engine=mock_engine)
    assert conn2.name == "cr_alias1"

    conn3 = esje.connect_crdb(name="cr_alias2", interactive_prompt=False, custom_engine=mock_engine)
    assert conn3.name == "cr_alias2"

    conn4 = esje.connect(dialect="cockroachdb", name="cr_generic1", interactive_prompt=False, custom_engine=mock_engine)
    assert conn4.name == "cr_generic1"

    conn5 = esje.connect(dialect="crdb", name="cr_generic2", interactive_prompt=False, custom_engine=mock_engine)
    assert conn5.name == "cr_generic2"

    df_conns = esje.connections()
    assert len(df_conns) == 5

    esje.close_all()
