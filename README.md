# `esje` — Credential-Safe SQL Magic & Live Dashboards for Jupyter

[![PyPI Version](https://img.shields.io/pypi/v/esje.svg)](https://pypi.org/project/esje/)
[![Python Versions](https://img.shields.io/pypi/pyversions/esje.svg)](https://pypi.org/project/esje/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: IPython](https://img.shields.io/badge/Framework-IPython-blue.svg)](https://ipython.org)

**E.S.J.E** — *Easy. SQL. Jupyter. Engine.*

`esje` brings powerful, credential-safe `%sql` and `%%sql` magics to Jupyter Notebooks and JupyterLab. Designed for data analysts and engineers, it eliminates hardcoded secrets in `.ipynb` files, seamlessly executes SQL alongside Python visualization code, and provides non-blocking auto-refreshing `--live` dashboards with Play/Pause/Stop controls.

---

## ✨ Features

- 🌐 **Login with Google**: One-click browser OAuth2 login for BigQuery — no service account JSON required.
- 🔒 **Zero Hardcoded Secrets**: Interactive prompts and automatic `.env` / environment variable fallbacks prevent password leaks in notebooks, git commits, or exports.
- ☁️ **Google BigQuery Native Driver**: Query BigQuery directly via browser login, Application Default Credentials (ADC), or service account key files.
- ⚡ **PyArrow High-Performance Backend**: Optional PyArrow integration for memory-efficient, fast query execution on large datasets.
- 📊 **SQL + Python Inline Execution**: Write SQL queries and Python plotting code (`matplotlib`, `seaborn`, `plotly`) in the same `%%sql` cell.
- ⏱️ **Non-Blocking `--live` Dashboards**: Auto-refresh queries on a timer without blocking the Jupyter kernel. Includes interactive Play/Pause/Stop widget controls.
- 🔌 **Named Connection Registry**: Connect to multiple databases/warehouses and switch between them using `-c <name>` or `esje.use()`.
- 🗣️ **MySQL-Style Dialect Translation**: Use familiar `SHOW DATABASES`, `SHOW TABLES`, `DESCRIBE table` commands — esje auto-translates them to BigQuery's `INFORMATION_SCHEMA` queries.
- 🛡️ **Clean Exception Handling**: Friendly, concise error messages without distracting multi-page Python tracebacks.

---

## 📦 Installation

```bash
pip install esje
```

For **Google BigQuery** support (includes browser login):

```bash
pip install "esje[bigquery]"
```

For high-performance **PyArrow** acceleration:

```bash
pip install "esje[pyarrow,bigquery]"
```

---

## 🚀 Quickstart

### 1. Load the Extension

```python
%load_ext esje
```

### 2. Connect to MySQL

```python
import esje

# Prompts securely for any missing credentials
conn = esje.connect_mysql()
```

### 3. Connect to Google BigQuery

#### 🌐 Option A — Login with Google (Browser) — *Recommended*

Opens your browser for Google Sign-In. No JSON key file needed.

```python
import esje

conn = esje.connect_bigquery(
    name="bq",
    project="my-gcp-project",
    auth_method="browser"       # opens browser → sign in → done!
)
```

> **In Jupyter, `auth_method="browser"` is the default** when no credentials are configured. Just call `connect_bigquery(project="my-gcp-project")`.

#### 🖥 Option B — Application Default Credentials (ADC)

Uses your existing `gcloud auth application-default login` session.

```python
conn = esje.connect_bigquery(
    name="bq",
    project="my-gcp-project",
    auth_method="adc"
)
```

#### 🔑 Option C — Service Account Key File

```python
conn = esje.connect_bigquery(
    name="bq",
    project="my-gcp-project",
    credentials_path="/path/to/service_account.json",
    auth_method="service_account"
)
```

**Auth method auto-detection:**

| Condition | Method chosen |
|---|---|
| `credentials_path` is set | `service_account` |
| Running interactively in Jupyter | `browser` |
| Non-interactive / CI environment | `adc` |

---

## 💡 Usage Examples

### Line Magic (`%sql`)

```python
%sql SELECT * FROM users LIMIT 5

# With named connection
%sql -c bq SELECT country, SUM(revenue) FROM `project.dataset.orders` GROUP BY country
```

### Cell Magic (`%%sql`)

```python
%%sql -c bq -o sales_summary
SELECT
    category,
    COUNT(*)        AS total_orders,
    SUM(revenue)    AS total_revenue
FROM `my-gcp-project.my_database.sales`
WHERE sale_date >= '2024-01-01'
GROUP BY category
ORDER BY total_revenue DESC
```

### Create Dataset & Table

```python
%%sql -c bq
CREATE SCHEMA IF NOT EXISTS `my-gcp-project.my_database`
OPTIONS (description = "My first esje dataset")
```

```python
%%sql -c bq
CREATE TABLE IF NOT EXISTS `my-gcp-project.my_database.sales` (
    id          INT64,
    product     STRING,
    category    STRING,
    quantity    INT64,
    revenue     FLOAT64,
    sale_date   DATE
)
```

### 🗣️ MySQL-Style Shorthand Commands

`esje` auto-translates familiar MySQL commands to BigQuery equivalents:

```python
%%sql -c bq
SHOW DATABASES          -- lists all datasets in your project

%%sql -c bq
SHOW TABLES             -- lists all tables across datasets

%%sql -c bq
SHOW TABLES IN my_database   -- tables in a specific dataset

%%sql -c bq
DESCRIBE my_database.sales   -- columns + data types of a table
```

### SQL + Python in One Cell

Combine SQL data extraction with immediate visualization. The result DataFrame is automatically available as `df`:

```python
%%sql -c bq
SELECT category, SUM(revenue) AS total_revenue
FROM `my-gcp-project.my_database.sales`
GROUP BY category;

import matplotlib.pyplot as plt

df.plot(x='category', y='total_revenue', kind='bar',
        title='Revenue by Category', color='steelblue', figsize=(8, 4))
plt.tight_layout()
plt.show()
```

---

## 🔄 Non-Blocking Live Dashboards (`--live`)

Auto-refresh dashboards without blocking the Jupyter kernel:

```python
%%sql -c bq --live 5
SELECT category, SUM(revenue) AS total_revenue
FROM `my-gcp-project.my_database.sales`
GROUP BY category;

import matplotlib.pyplot as plt

df.plot(x='category', y='total_revenue', kind='bar',
        title='Real-Time Revenue Dashboard', color='teal', figsize=(8, 4))
plt.tight_layout()
plt.show()
```

Each live widget includes interactive **▶️ Play / ⏸ Pause / ⏹ Stop** buttons.

```python
esje.pause_live()      # Pause all active live widgets
esje.resume_live()     # Resume all
esje.stop_all_live()   # Stop all background widgets
```

---

## 🔑 Credential Resolution Order

| Priority | Source |
|---|---|
| 1 | Explicit parameters passed to `connect_bigquery(...)` |
| 2 | `.env` file (`ESJE_BIGQUERY_PROJECT`, `ESJE_BIGQUERY_AUTH_METHOD`, etc.) |
| 3 | OS environment variables (`GCP_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`, etc.) |
| 4 | Interactive browser login or `getpass` prompt |

**BigQuery environment variables:**

| Variable | Purpose |
|---|---|
| `ESJE_BIGQUERY_PROJECT` / `GCP_PROJECT` | GCP Project ID |
| `ESJE_BIGQUERY_AUTH_METHOD` | `browser`, `adc`, or `service_account` |
| `ESJE_BIGQUERY_CREDENTIALS_PATH` / `GOOGLE_APPLICATION_CREDENTIALS` | Service account JSON path |
| `ESJE_BIGQUERY_DATASET` | Default dataset |
| `ESJE_BIGQUERY_LOCATION` | Dataset location (e.g. `US`) |

---

## ⚙️ Configuration Options

```python
import esje

esje.config.max_display_rows = 50      # Max rows shown in HTML output (default: 100)
esje.config.verbose_errors = True      # Show full tracebacks (default: False)
esje.config.use_pyarrow = True         # Enable PyArrow backend (default: auto-detect)
esje.config.auto_commit = True         # Auto-commit DML statements (default: True)
```

---

## 🔌 Connection Management

```python
esje.connections()       # List all active connections as a DataFrame
esje.use("bq")           # Set default connection for %sql
esje.close("bq")         # Close a specific connection
esje.close_all()         # Close all connections + stop live widgets
```

---

## 🔮 Roadmap

### 🌐 Universal Database Connectivity
- **Relational**: PostgreSQL, SQLite, Oracle, MS SQL Server, CockroachDB
- **Big Data & Warehouses**: Apache Hive, Trino/Presto, Spark SQL, Databricks, Snowflake, Amazon Redshift, ClickHouse
- **Embedded Engines**: DuckDB, Polars, direct Parquet/Feather querying

### 🤖 AI Companion (`--ai`)
- Natural language to SQL: `%sql --ai "Show top revenue categories in 2026"`
- AI self-healing queries and schema-aware error fixes
- Automated chart type selection via LLMs (OpenAI, Gemini, Ollama)

### 📊 Advanced Dashboarding
- Multi-chart grid canvas in single cells
- Webhook / Slack alerting on metric thresholds
- Enterprise vault integration (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault)

---

## 📄 License

Distributed under the [MIT License](https://opensource.org/licenses/MIT).
