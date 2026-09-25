"""Tests for OracleDriver, Oracle prompt resolution, and top-level Oracle connection helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import esje
from esje.drivers.oracle import OracleDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_oracle_credentials


def test_resolve_oracle_credentials_explicit():
    creds = resolve_oracle_credentials(
        host="ora.example.com",
        port=1522,
        user="orauser",
        password="secretpassword",
        service_name="ORCLCDB",
        sid="ORCL",
        database="mydb",
        thick_mode=True,
        interactive_prompt=False,
    )

    assert creds["host"] == "ora.example.com"
    assert creds["port"] == 1522
    assert creds["user"] == "orauser"
    assert creds["password"] == "secretpassword"
    assert creds["service_name"] == "ORCLCDB"
    assert creds["sid"] == "ORCL"
    assert creds["database"] == "mydb"
    assert creds["thick_mode"] is True


def test_resolve_oracle_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_ORACLE_HOST", "envorahost")
    monkeypatch.setenv("ESJE_ORACLE_PORT", "1523")
    monkeypatch.setenv("ESJE_ORACLE_USER", "envorauser")
    monkeypatch.setenv("ESJE_ORACLE_PASSWORD", "envorapass")
    monkeypatch.setenv("ESJE_ORACLE_SERVICE_NAME", "ENV_SERVICE")
    monkeypatch.setenv("ESJE_ORACLE_THICK_MODE", "true")

    creds = resolve_oracle_credentials(interactive_prompt=False)

    assert creds["host"] == "envorahost"
    assert creds["port"] == 1523
    assert creds["user"] == "envorauser"
    assert creds["password"] == "envorapass"
    assert creds["service_name"] == "ENV_SERVICE"
    assert creds["thick_mode"] is True


def test_resolve_oracle_credentials_ora_env_fallbacks(monkeypatch):
    monkeypatch.setenv("ORA_HOST", "orahost")
    monkeypatch.setenv("ORA_PORT", "1524")
    monkeypatch.setenv("ORA_USER", "orauser")
    monkeypatch.setenv("ORA_PASSWORD", "orapass")
    monkeypatch.setenv("ORACLE_SERVICE_NAME", "ORCL_SERVICE")

    creds = resolve_oracle_credentials(interactive_prompt=False)

    assert creds["host"] == "orahost"
    assert creds["port"] == 1524
    assert creds["user"] == "orauser"
    assert creds["password"] == "orapass"
    assert creds["service_name"] == "ORCL_SERVICE"


def test_resolve_oracle_credentials_interactive():
    inputs = ["prompt_orahost", "1525", "prompt_orauser", "XE"]
    with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="prompt_orapass"):
        creds = resolve_oracle_credentials(interactive_prompt=True)

    assert creds["host"] == "prompt_orahost"
    assert creds["port"] == 1525
    assert creds["user"] == "prompt_orauser"
    assert creds["password"] == "prompt_orapass"
    assert creds["service_name"] == "XE"


def test_oracle_driver_dialect_and_url():
    driver = OracleDriver(
        host="localhost",
        port=1521,
        user="system",
        password="p@ss/word",
        service_name="ORCLCDB",
    )
    assert driver.dialect == "oracle"
    url = driver._build_connection_url()
    assert "oracle+oracledb://system:p%40ss%2Fword@localhost:1521/?service_name=ORCLCDB" in url

    # Test SID URL
    driver_sid = OracleDriver(
        host="localhost",
        port=1521,
        user="system",
        password="pass",
        sid="XE",
    )
    url_sid = driver_sid._build_connection_url()
    assert "oracle+oracledb://system:pass@localhost:1521/?sid=XE" in url_sid

    # Test database fallback URL
    driver_db = OracleDriver(
        host="localhost",
        port=1521,
        user="system",
        password="pass",
        database="MYSERVICE",
    )
    url_db = driver_db._build_connection_url()
    assert "oracle+oracledb://system:pass@localhost:1521/?service_name=MYSERVICE" in url_db


def test_oracle_driver_connect_success():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = OracleDriver(custom_engine=mock_engine)
    driver.connect()

    mock_conn.execute.assert_called_once()


def test_oracle_driver_connect_auth_failure_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError(
        "statement", {}, Exception("ORA-01017: invalid username/password; logon denied")
    )

    driver = OracleDriver(custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Access denied" in str(exc_info.value.hint)


def test_oracle_driver_connect_no_listener_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError(
        "statement", {}, Exception("ORA-12541: TNS:no listener")
    )

    driver = OracleDriver(host="127.0.0.1", port=1521, custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "Failed to connect to Oracle server" in str(exc_info.value.hint)


def test_oracle_driver_connect_unknown_service_hint():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError(
        "statement", {}, Exception("ORA-12514: TNS:listener does not currently know of service requested in connect descriptor")
    )

    driver = OracleDriver(service_name="NONEXISTENT", custom_engine=mock_engine)

    with pytest.raises(ConnectionError) as exc_info:
        driver.connect()

    assert "NONEXISTENT" in str(exc_info.value.hint)


def test_oracle_driver_execute_select_strips_semicolon():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    expected_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})

    with patch("pandas.read_sql", return_value=expected_df) as mock_read_sql:
        driver = OracleDriver(custom_engine=mock_engine)
        result = driver.execute("SELECT * FROM employees;")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    # Verify that the query passed to sqlalchemy text inside read_sql has semicolon stripped
    sql_text_arg = str(mock_read_sql.call_args[0][0])
    assert sql_text_arg == "SELECT * FROM employees"


def test_oracle_driver_execute_dml():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_trans = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5

    mock_conn.begin.return_value = mock_trans
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = OracleDriver(custom_engine=mock_engine)
    res = driver.execute("UPDATE employees SET salary = salary * 1.1 WHERE dept_id = 10;")

    assert res["status"] == "Query executed successfully"
    assert res["rowcount"] == 5
    mock_trans.commit.assert_called_once()


def test_oracle_driver_execute_sql_error():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = SQLAlchemyError("ORA-00942: table or view does not exist")
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    driver = OracleDriver(custom_engine=mock_engine)

    with pytest.raises(QueryError):
        driver.execute("UPDATE nonexistent_table SET col = 1")


def test_oracle_driver_close():
    mock_engine = MagicMock()
    driver = OracleDriver(custom_engine=mock_engine)
    driver.close()

    mock_engine.dispose.assert_called_once()
    assert driver._engine is None


def test_top_level_oracle_connect():
    esje.close_all()
    mock_engine = MagicMock()

    conn1 = esje.connect_oracle(name="ora_test", interactive_prompt=False, custom_engine=mock_engine)
    assert conn1.name == "ora_test"
    assert conn1.dialect == "oracle"

    conn2 = esje.connect_ora(name="ora_alias", interactive_prompt=False, custom_engine=mock_engine)
    assert conn2.name == "ora_alias"

    conn3 = esje.connect(dialect="oracle", name="ora_generic", interactive_prompt=False, custom_engine=mock_engine)
    assert conn3.name == "ora_generic"

    conn4 = esje.connect(dialect="oracledb", name="oracledb_generic", interactive_prompt=False, custom_engine=mock_engine)
    assert conn4.name == "oracledb_generic"

    df_conns = esje.connections()
    assert len(df_conns) == 4

    esje.close_all()
