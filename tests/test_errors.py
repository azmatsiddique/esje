"""Tests for esje.errors."""

from esje.errors import ConfigurationError, ConnectionError, EsjeError, QueryError


def test_esje_error_string_formatting():
    err = EsjeError("Something failed", hint="Try turning it off and on.")
    assert "Something failed" in str(err)
    assert "Hint: Try turning it off and on." in str(err)

    err_no_hint = EsjeError("No hint here")
    assert str(err_no_hint) == "No hint here"


def test_error_subclasses():
    conn_err = ConnectionError("Connection failed")
    query_err = QueryError("Syntax error")
    config_err = ConfigurationError("Invalid setting")

    assert isinstance(conn_err, EsjeError)
    assert isinstance(query_err, EsjeError)
    assert isinstance(config_err, EsjeError)
