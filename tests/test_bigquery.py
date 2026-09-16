"""Unit tests for BigQuery driver and credential prompting."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from esje.connection import Connection, manager
from esje.drivers.bigquery import BigQueryDriver
from esje.errors import ConnectionError, QueryError
from esje.prompts import resolve_bigquery_credentials


def test_resolve_bigquery_credentials_explicit():
    creds = resolve_bigquery_credentials(
        project="my-gcp-proj",
        dataset="sales_ds",
        credentials_path="/path/to/sa.json",
        location="US",
        interactive_prompt=False,
    )
    assert creds["project"] == "my-gcp-proj"
    assert creds["dataset"] == "sales_ds"
    assert creds["credentials_path"] == "/path/to/sa.json"
    assert creds["location"] == "US"


def test_resolve_bigquery_credentials_env_vars(monkeypatch):
    monkeypatch.setenv("ESJE_BIGQUERY_PROJECT", "env-proj-123")
    monkeypatch.setenv("ESJE_BIGQUERY_DATASET", "env_dataset")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/env/sa.json")
    monkeypatch.setenv("ESJE_BIGQUERY_LOCATION", "EU")

    creds = resolve_bigquery_credentials(interactive_prompt=False)
    assert creds["project"] == "env-proj-123"
    assert creds["dataset"] == "env_dataset"
    assert creds["credentials_path"] == "/env/sa.json"
    assert creds["location"] == "EU"


def test_bigquery_driver_connect_and_execute_mock():
    mock_client = MagicMock()
    mock_job = MagicMock()
    mock_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    mock_job.to_dataframe.return_value = mock_df
    mock_client.query.return_value = mock_job

    driver = BigQueryDriver(
        project="test-proj",
        dataset="test_ds",
        custom_client=mock_client,
    )

    assert driver.dialect == "bigquery"
    driver.connect()
    mock_client.query.assert_called_with("SELECT 1")

    # Test SELECT query execution
    df_res = driver.execute("SELECT * FROM `test-proj.test_ds.users`")
    assert isinstance(df_res, pd.DataFrame)
    assert len(df_res) == 2

    # Test DML execution
    mock_dml_job = MagicMock()
    mock_dml_job.num_dml_affected_rows = 5
    mock_client.query.return_value = mock_dml_job

    dml_res = driver.execute("DELETE FROM `test-proj.test_ds.users` WHERE id = 1")
    assert isinstance(dml_res, dict)
    assert dml_res["affected_rows"] == 5

    driver.close()


def test_connect_bigquery_api():
    mock_client = MagicMock()
    mock_job = MagicMock()
    mock_client.query.return_value = mock_job

    import esje

    conn = esje.connect_bigquery(
        name="bq_test",
        project="my-bq-proj",
        dataset="analytics",
        interactive_prompt=False,
        custom_client=mock_client,
    )

    assert conn.name == "bq_test"
    assert conn.dialect == "bigquery"
    assert manager.active_name == "bq_test"

    # Test generic dispatcher
    conn_generic = esje.connect(
        dialect="bigquery",
        name="bq_generic",
        project="my-bq-proj2",
        interactive_prompt=False,
        custom_client=mock_client,
    )
    assert conn_generic.dialect == "bigquery"
    assert conn_generic.name == "bq_generic"


def test_bigquery_missing_dependency_error():
    driver = BigQueryDriver(project="missing-dep-proj")
    with patch.dict("sys.modules", {"google.cloud": None, "google.cloud.bigquery": None}):
        with pytest.raises(ConnectionError) as exc_info:
            driver.connect()
        assert "google-cloud-bigquery" in str(exc_info.value)
