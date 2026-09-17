"""Tests for PostgresDriver, PostgreSQL prompt resolution, and top-level PostgreSQL connection helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import esje
from esje.drivers.postgres import PostgresDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_postgres_credentials


def test_resolve_postgres_credentials_explicit():
    creds = resolve_postgres_credentials(
        host="pg.example.com",
        port=5433,
        user="myuser",
        password="secretpassword",
        database="mydb",
        sslmode="require",
        interactive_prompt=False,
    )

    assert creds["host"] == "pg.example.com"
    assert creds["port"] == 5433
    assert creds["user"] == "myuser"
    assert creds["password"] == "secretpassword"
    assert creds["database"] == "mydb"
    assert creds["sslmode"] == "require"


def test_resolve_postgres_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_POSTGRES_HOST", "envpghost")
    monkeypatch.setenv("ESJE_POSTGRES_PORT", "5434")
    monkeypatch.setenv("ESJE_POSTGRES_USER", "envpguser")
    monkeypatch.setenv("ESJE_POSTGRES_PASSWORD", "envpgpass")
    monkeypatch.setenv("ESJE_POSTGRES_DATABASE", "envpgdb")
    monkeypatch.setenv("ESJE_POSTGRES_SSLMODE", "prefer")

    creds = resolve_postgres_credentials(interactive_prompt=False)

    assert creds["host"] == "envpghost"
    assert creds["port"] == 5434
    assert creds["user"] == "envpguser"
    assert creds["password"] == "envpgpass"
    assert creds["database"] == "envpgdb"
    assert creds["sslmode"] == "prefer"


def test_resolve_postgres_credentials_pg_env_fallbacks(monkeypatch):
    monkeypatch.setenv("PGHOST", "pghost")
    monkeypatch.setenv("PGPORT", "5435")
    monkeypatch.setenv("PGUSER", "pguser")
    monkeypatch.setenv("PGPASSWORD", "pgpass")
    monkeypatch.setenv("PGDATABASE", "pgdb")
    monkeypatch.setenv("PGSSLMODE", "require")

    creds = resolve_postgres_credentials(interactive_prompt=False)

    assert creds["host"] == "pghost"
    assert creds["port"] == 5435
    assert creds["user"] == "pguser"
    assert creds["password"] == "pgpass"
    assert creds["database"] == "pgdb"
    assert creds["sslmode"] == "require"


def test_resolve_postgres_credentials_interactive():
    inputs = ["prompt_pghost", "5436", "prompt_pguser", "prompt_pgdb"]
    with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="prompt_pgpass"):
        creds = resolve_postgres_credentials(interactive_prompt=True)

    assert creds["host"] == "prompt_pghost"
    assert creds["port"] == 5436
    assert creds["user"] == "prompt_pguser"
    assert creds["password"] == "prompt_pgpass"
    assert creds["database"] == "prompt_pgdb"


def test_postgres_driver_dialect_and_url():
    driver = PostgresDriver(
        host="localhost",
        port=5432,
        user="postgres",
        password="p@ss/word",
        database="testdb",
        sslmode="require",
    )
    assert driver.dialect == "postgres"
    url = driver._build_connection_url()
    assert "postgresql+psycopg2://postgres:p%40ss%2Fword@localhost:5432/testdb?sslmode=require" in url


def test_postgres_driver_connect_success():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = PostgresDriver(custom_engine=mock_engine)
    driver.connect()

    mock_conn.execute.assert_called_once()


def test_postgres_driver_connect_auth_failure_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("statement", {}, Exception("FATAL: password authentication failed for user 'postgres'"))

    driver = PostgresDriver(custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Access denied" in str(exc_info.value.hint)


def test_postgres_driver_connect_refused_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("statement", {}, Exception("could not connect to server: Connection refused"))

    driver = PostgresDriver(host="127.0.0.1", port=5432, custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Failed to connect to PostgreSQL server" in str(exc_info.value.hint)


def test_postgres_driver_execute_select():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    expected_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})

    with patch("pandas.read_sql", return_value=expected_df):
        driver = PostgresDriver(custom_engine=mock_engine)
        result = driver.execute("SELECT * FROM users;")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_postgres_driver_execute_dml():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_trans = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 3

    mock_conn.begin.return_value = mock_trans
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = PostgresDriver(custom_engine=mock_engine)
    res = driver.execute("UPDATE users SET active = true WHERE age > 20;")

    assert res["status"] == "Query executed successfully"
    assert res["rowcount"] == 3
    mock_trans.commit.assert_called_once()


def test_postgres_driver_execute_sql_error():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = SQLAlchemyError("syntax error at or near 'SELECT'")
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = PostgresDriver(custom_engine=mock_engine)

    with pytest.raises(QueryError):
        driver.execute("UPDATE invalid table")


def test_postgres_driver_close():
    mock_engine = MagicMock()
    driver = PostgresDriver(custom_engine=mock_engine)
    driver.close()

    mock_engine.dispose.assert_called_once()
    assert driver._engine is None


def test_top_level_postgres_connect():
    esje.close_all()
    mock_engine = MagicMock()

    conn1 = esje.connect_postgres(name="pg_test", interactive_prompt=False, custom_engine=mock_engine)
    assert conn1.name == "pg_test"
    assert conn1.dialect == "postgres"

    conn2 = esje.connect_postgresql(name="pg_alias", interactive_prompt=False, custom_engine=mock_engine)
    assert conn2.name == "pg_alias"

    conn3 = esje.connect(dialect="postgres", name="pg_generic", interactive_prompt=False, custom_engine=mock_engine)
    assert conn3.name == "pg_generic"

    conn4 = esje.connect(dialect="postgresql", name="psql_generic", interactive_prompt=False, custom_engine=mock_engine)
    assert conn4.name == "psql_generic"

    df_conns = esje.connections()
    assert len(df_conns) == 4

    esje.close_all()
