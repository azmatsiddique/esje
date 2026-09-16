"""Google BigQuery driver implementation for esje using google-cloud-bigquery or SQLAlchemy."""

import os
from typing import Any, Dict, Optional, Union

import pandas as pd

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class BigQueryDriver(BaseDriver):
    """BigQuery driver wrapping google-cloud-bigquery SDK and SQLAlchemy."""

    def __init__(
        self,
        project: Optional[str] = None,
        dataset: str = "",
        credentials_path: Optional[str] = None,
        location: Optional[str] = None,
        custom_client: Any = None,
        custom_engine: Any = None,
    ) -> None:
        self.project = project or ""
        self.dataset = dataset
        self.credentials_path = credentials_path
        self.location = location

        self._client = custom_client
        self._engine = custom_engine

        # Useful metadata properties for Connection handle display
        self.host = self.project or "bigquery"
        self.port = 443
        self.user = "sa" if self.credentials_path else "default"
        self.database = self.dataset

    @property
    def dialect(self) -> str:
        return "bigquery"

    def connect(self) -> None:
        """Establish BigQuery client connection and run validation query."""
        if self._client is None and self._engine is None:
            try:
                from google.cloud import bigquery
            except ImportError:
                raise ConnectionError(
                    "google-cloud-bigquery is not installed.",
                    hint="Install BigQuery support via: pip install 'esje[bigquery]' or pip install google-cloud-bigquery db-dtypes",
                )

            try:
                credentials = None
                if self.credentials_path:
                    if not os.path.exists(self.credentials_path):
                        raise ConnectionError(
                            f"Service account file not found at: {self.credentials_path}",
                            hint="Verify your service account JSON credentials file path.",
                        )
                    from google.oauth2 import service_account

                    credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_path
                    )

                client_kwargs: Dict[str, Any] = {}
                if self.project:
                    client_kwargs["project"] = self.project
                if credentials:
                    client_kwargs["credentials"] = credentials
                if self.location:
                    client_kwargs["location"] = self.location
                if self.dataset:
                    client_kwargs["default_query_job_config"] = bigquery.QueryJobConfig(
                        default_dataset=f"{self.project}.{self.dataset}"
                        if self.project
                        else self.dataset
                    )

                self._client = bigquery.Client(**client_kwargs)
            except Exception as exc:
                if isinstance(exc, ConnectionError):
                    raise
                raise ConnectionError(
                    f"BigQuery initialization failed: {exc}",
                    hint="Check GCP Project ID, authentication credentials, and permissions.",
                ) from (exc if config.verbose_errors else None)

        # Validate connection with ping query
        try:
            if self._client is not None:
                query_job = self._client.query("SELECT 1")
                query_job.result()
            elif self._engine is not None:
                from sqlalchemy import text

                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
        except Exception as exc:
            raise ConnectionError(
                f"BigQuery ping check failed: {exc}",
                hint="Verify GCP Project ID, network connectivity, and BigQuery API quota.",
            ) from (exc if config.verbose_errors else None)

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Execute BigQuery SQL query and return DataFrame or execution summary."""
        if self._client is None and self._engine is None:
            raise ConnectionError("Not connected to BigQuery.")

        clean_query = query.strip().rstrip(";")
        is_select = clean_query.lower().startswith(
            ("select", "with", "show", "describe", "desc", "explain")
        )

        try:
            if self._client is not None:
                query_job = self._client.query(query)

                if is_select:
                    if config.use_pyarrow:
                        try:
                            return query_job.to_dataframe(dtype_backend="pyarrow")
                        except Exception:
                            return query_job.to_dataframe()
                    else:
                        return query_job.to_dataframe()
                else:
                    query_job.result()
                    affected = getattr(query_job, "num_dml_affected_rows", None)
                    return {
                        "status": "BigQuery query executed successfully",
                        "affected_rows": affected if affected is not None else 0,
                    }

            elif self._engine is not None:
                from sqlalchemy import text

                with self._engine.connect() as conn:
                    if is_select:
                        if config.use_pyarrow:
                            try:
                                return pd.read_sql(text(query), con=conn, dtype_backend="pyarrow")
                            except Exception:
                                return pd.read_sql(text(query), con=conn)
                        else:
                            return pd.read_sql(text(query), con=conn)
                    else:
                        result = conn.execute(text(query))
                        rowcount = getattr(result, "rowcount", 0)
                        return {"status": "BigQuery query executed successfully", "affected_rows": rowcount}
        except Exception as exc:
            raise QueryError(f"BigQuery Query Error: {exc}") from (
                exc if config.verbose_errors else None
            )

    def close(self) -> None:
        """Close BigQuery client or engine resources."""
        if self._client is not None:
            if hasattr(self._client, "close"):
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = None

        if self._engine is not None:
            try:
                self._engine.dispose()
            except Exception:
                pass
            self._engine = None
