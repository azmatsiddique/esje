"""Tests for IPython magics (%sql and %%sql)."""

import pytest
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from unittest.mock import MagicMock

import pandas as pd

import esje
from esje.connection import Connection, manager
from esje.drivers.base import BaseDriver


class MockDriver(BaseDriver):
    def __init__(self, name="mock"):
        self.name = name

    @property
    def dialect(self) -> str:
        return "mysql"

    def connect(self) -> None:
        pass

    def execute(self, query: str):
        if "users" in query:
            return pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        elif "INSERT" in query:
            return {"status": "Query executed successfully", "rowcount": 1}
        return pd.DataFrame({"dummy": [1]})

    def close(self) -> None:
        pass


@pytest.fixture
def ip():
    shell = TerminalInteractiveShell.instance()
    shell.run_line_magic("load_ext", "esje")
    return shell


def test_ipython_magic_extension(ip):
    # Setup mock connection
    drv = MockDriver()
    conn = Connection("default", drv)
    manager.add(conn)

    # Test line magic execution
    result = ip.run_line_magic("sql", "SELECT * FROM users")
    assert result is not None
    assert len(result) == 2
    assert list(result.columns) == ["id", "name"]

    # Test line magic with output assignment
    ip.run_line_magic("sql", "-o my_df SELECT * FROM users")
    assert "my_df" in ip.user_ns
    assert len(ip.user_ns["my_df"]) == 2

    # Test cell magic execution
    cell_result = ip.run_cell_magic("sql", "", "SELECT * FROM users")
    assert cell_result is not None
    assert len(cell_result) == 2

    # Test cell magic output assignment
    ip.run_cell_magic("sql", "-o cell_df", "SELECT * FROM users")
    assert "cell_df" in ip.user_ns
    assert len(ip.user_ns["cell_df"]) == 2


def test_ipython_magic_named_connection(ip):
    drv1 = MockDriver("db1")
    drv2 = MockDriver("db2")
    manager.add(Connection("conn1", drv1))
    manager.add(Connection("conn2", drv2))

    res1 = ip.run_line_magic("sql", "-c conn1 SELECT * FROM users")
    res2 = ip.run_line_magic("sql", "-c conn2 SELECT * FROM users")

    assert res1 is not None
    assert res2 is not None


def test_magic_error_handling(ip, capsys):
    manager.close_all()
    # No active connection should print friendly error message to stderr
    res = ip.run_line_magic("sql", "SELECT * FROM users")
    assert res is None


def test_split_sql_and_python():
    from esje.magics import split_sql_and_python

    cell = """SELECT * FROM users
import matplotlib.pyplot as plt
df.plot()"""

    sql, py = split_sql_and_python(cell)
    assert sql == "SELECT * FROM users"
    assert "import matplotlib.pyplot as plt" in py
    assert "df.plot()" in py


def test_cell_magic_python_execution(ip):
    drv = MockDriver()
    conn = Connection("default", drv)
    manager.add(conn)

    cell_body = """SELECT * FROM users
x = len(df) * 10"""

    ip.run_cell_magic("sql", "-o df", cell_body)
    assert "df" in ip.user_ns
    assert "x" in ip.user_ns
    assert ip.user_ns["x"] == 20


