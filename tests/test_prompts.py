"""Tests for esje.prompts."""

import os
from unittest.mock import patch

from esje.prompts import resolve_mysql_credentials


def test_resolve_mysql_credentials_explicit():
    creds = resolve_mysql_credentials(
        host="db.example.com",
        port=3307,
        user="myuser",
        password="secretpassword",
        database="mydb",
        interactive_prompt=False,
    )

    assert creds["host"] == "db.example.com"
    assert creds["port"] == 3307
    assert creds["user"] == "myuser"
    assert creds["password"] == "secretpassword"
    assert creds["database"] == "mydb"


def test_resolve_mysql_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_MYSQL_HOST", "envhost")
    monkeypatch.setenv("ESJE_MYSQL_PORT", "3308")
    monkeypatch.setenv("ESJE_MYSQL_USER", "envuser")
    monkeypatch.setenv("ESJE_MYSQL_PASSWORD", "envpass")
    monkeypatch.setenv("ESJE_MYSQL_DATABASE", "envdb")

    creds = resolve_mysql_credentials(interactive_prompt=False)

    assert creds["host"] == "envhost"
    assert creds["port"] == 3308
    assert creds["user"] == "envuser"
    assert creds["password"] == "envpass"
    assert creds["database"] == "envdb"


def test_resolve_mysql_credentials_interactive():
    inputs = ["prompt_host", "3309", "prompt_user", "prompt_db"]
    with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="prompt_pass"):
        creds = resolve_mysql_credentials(interactive_prompt=True)

    assert creds["host"] == "prompt_host"
    assert creds["port"] == 3309
    assert creds["user"] == "prompt_user"
    assert creds["password"] == "prompt_pass"
    assert creds["database"] == "prompt_db"
