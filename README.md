# `esje` — Credential-Safe SQL Magic & Live Dashboards for Jupyter

[![PyPI Version](https://img.shields.io/pypi/v/esje.svg)](https://pypi.org/project/esje/)
[![Python Versions](https://img.shields.io/pypi/pyversions/esje.svg)](https://pypi.org/project/esje/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: IPython](https://img.shields.io/badge/Framework-IPython-blue.svg)](https://ipython.org)

`esje` brings powerful, credential-safe `%sql` and `%%sql` magics to Jupyter Notebooks and JupyterLab. Designed for data analysts and engineers, it eliminates hardcoded secrets in `.ipynb` files, seamlessly executes SQL alongside Python visualization code, and provides non-blocking auto-refreshing `--live` dashboards with Play/Pause/Stop controls.

---

## ✨ Features

- 🔒 **Zero Hardcoded Secrets**: Interactive `getpass` prompts and automatic `.env` / environment variable fallbacks prevent password leaks in notebook cells, git commits, or exports.
- ☁️ **Google BigQuery Native Driver**: Query Google BigQuery data warehouses directly using Application Default Credentials (ADC) or service account key JSON files.
- ⚡ **PyArrow High-Performance Backend**: Optional PyArrow data type integration for memory-efficient and fast query execution on large datasets.
- 📊 **SQL + Python Inline Execution**: Write SQL queries and Python plotting code (`matplotlib`, `seaborn`, `plotly`) in the exact same `%%sql` cell.
- ⏱️ **Non-Blocking `--live` Dashboards**: Run queries on an auto-refresh timer without blocking the Jupyter kernel execution thread. Includes interactive Play/Pause/Stop widget controls.
- 🔌 **Named Connection Registry**: Connect to multiple databases/warehouses and switch between them effortlessly using `-c <conn_name>` or `esje.use()`.
- 🛡️ **Clean Exception Handling**: Friendly, concise error messages by default without distracting multi-page Python tracebacks.

---

## 📦 Installation

Install `esje` via `pip`:

```bash
pip install esje
```

To enable **Google BigQuery** support, install with the `bigquery` extra:

```bash
pip install "esje[bigquery]"
```

For high-performance PyArrow data type acceleration, install with the `pyarrow` extra:

```bash
pip install "esje[pyarrow,bigquery]"
```

---

## 🚀 Quickstart

### 1. Load the Extension

In your Jupyter Notebook, load `esje`:

```python
%load_ext esje
```

### 2. Connect to MySQL

Connect interactively (you will be prompted securely for any missing credentials):

```python
import esje

# Prompts for host, user, password, database if not found in .env or environment
conn = esje.connect_mysql()
```

### 3. Connect to Google BigQuery

Connect to Google BigQuery using Application Default Credentials (ADC) or explicit project credentials:

```python
import esje

# Connect using Application Default Credentials (ADC) or env vars
bq_conn = esje.connect_bigquery(
    name="bq_prod",
    project="my-gcp-project",
    dataset="sales_analytics"
)

# Connect using Service Account JSON key file
bq_conn = esje.connect_bigquery(
    name="bq_sa",
    project="my-gcp-project",
    credentials_path="/path/to/service_account.json"
)
```

---

## 💡 Usage Examples

### Line Magic (`%sql`)

Run a quick one-liner SQL query against active connection or specified connection:

```python
%sql SELECT * FROM users LIMIT 5
```

Query BigQuery using named connection `-c`:

```python
df = %sql -c bq_prod SELECT country, SUM(revenue) FROM `my-gcp-project.sales_analytics.orders` GROUP BY country
```

### Cell Magic (`%%sql`)

Execute multi-line SQL queries and capture results into a DataFrame with `-o <var_name>`:

```python
%%sql -c bq_prod -o sales_summary
SELECT 
    category,
    COUNT(*) AS total_orders,
    SUM(revenue) AS total_revenue
FROM `my-gcp-project.sales_analytics.sales_data`
WHERE created_at >= '2026-01-01'
GROUP BY category
ORDER BY total_revenue DESC;
```

### SQL + Python Code Execution in a Single Cell

Combine SQL data extraction with immediate visualization. The result DataFrame is automatically made available to your Python snippet as `df`:

```python
%%sql -c bq_prod
SELECT category, SUM(revenue) AS total_revenue 
FROM `my-gcp-project.sales_analytics.sales_data` 
GROUP BY category;

import matplotlib.pyplot as plt

df.plot(
    x='category', 
    y='total_revenue', 
    kind='bar', 
    title='Total Revenue by Category (BigQuery)',
    color='skyblue',
    figsize=(8, 4)
)
plt.ylabel('Revenue ($)')
plt.tight_layout()
plt.show()
```

---

## 🔄 Non-Blocking Live Dashboards (`--live`)

Create real-time, auto-refreshing dashboard widgets right inside your notebook! Passing `--live <interval_seconds>` launches a background thread that periodically re-executes the query and updates the visualization **without blocking your Jupyter kernel**.

```python
%%sql -c bq_prod --live 5
SELECT category, SUM(revenue) AS total_revenue 
FROM `my-gcp-project.sales_analytics.sales_data`
GROUP BY category;

import matplotlib.pyplot as plt

df.plot(
    x='category', 
    y='total_revenue', 
    kind='bar', 
    title='Real-Time BigQuery Revenue Dashboard',
    color='teal',
    figsize=(8, 4)
)
plt.ylabel('Revenue ($)')
plt.tight_layout()
plt.show()
```

### Dashboard Widget Controls

Each live widget provides interactive buttons:
- ▶️ **Play**: Resume live auto-refresh.
- ⏸️ **Pause**: Freeze updates while keeping the widget visible.
- ⏹️ **Stop**: Terminate the background updater thread.

### Programmatic Control API

You can also control active live widgets directly from Python cells:

```python
esje.pause_live()      # Pause all active live widgets
esje.resume_live()     # Resume all live widgets
esje.stop_live()       # Stop a specific live widget by ID
esje.stop_all_live()   # Stop all running background widgets
```

---

## 🔑 Credential Resolution Order

Credentials are resolved in the following priority order:

1. **Explicit Parameters**: Arguments passed directly to `connect_mysql(...)` or `connect_bigquery(...)`.
2. **Environment File (`.env`)**:
   - MySQL: `ESJE_MYSQL_HOST`, `ESJE_MYSQL_USER`, `ESJE_MYSQL_PASSWORD`, `ESJE_MYSQL_DATABASE`, `ESJE_MYSQL_PORT`.
   - BigQuery: `ESJE_BIGQUERY_PROJECT` (or `GCP_PROJECT`/`GOOGLE_CLOUD_PROJECT`), `ESJE_BIGQUERY_DATASET`, `GOOGLE_APPLICATION_CREDENTIALS` (or `ESJE_BIGQUERY_CREDENTIALS_PATH`).
3. **OS Environment Variables**: System environment variables set in shell context.
4. **Interactive `getpass` Prompts**: Secure interactive prompts for missing credentials without echoing inputs.

---

## ⚙️ Configuration Options

Tune `esje` settings globally via `esje.config`:

```python
import esje

# Limit max table rows displayed in HTML output (default: 100)
esje.config.max_display_rows = 50

# Enable verbose Python tracebacks for debugging (default: False)
esje.config.verbose_errors = True

# Enable PyArrow backend for faster queries (default: True if pyarrow is installed)
esje.config.use_pyarrow = True

# Auto-commit DML statements (default: True)
esje.config.auto_commit = True
```

---

## 🔌 Connection Management

List, switch, and close active database connections:

```python
# List all active connections in a pandas DataFrame
esje.connections()

# Switch the default active connection for %sql magics
esje.use("bq_prod")

# Close a specific connection
esje.close("bq_prod")

# Close all connections and stop all live widgets
esje.close_all()
```

---

## 🔮 Future Scope & Roadmap

`esje` is expanding into a universal, AI-native data connectivity ecosystem for notebook environments. Upcoming features include:

### 🌐 1. Universal Database & Data Lake Connectivity
- **Supported Dialects**: MySQL, Google BigQuery.
- **Relational Databases**: Native drivers for PostgreSQL, SQLite, Oracle, Microsoft SQL Server, and CockroachDB.
- **Big Data & Data Warehouses**: Apache Hive, Trino / Presto, Apache Spark SQL, Databricks, Snowflake, Amazon Redshift, and ClickHouse.
- **Embedded & Columnar Engines**: DuckDB, Polars engine support, and parquet/feather direct query execution.

### 🤖 2. AI-Powered Intelligent Companion (`--ai` / `%%sql --ai`)
- **Natural Language to SQL**: Write queries in plain English:
  ```python
  %sql --ai "Show top 5 revenue generating categories in 2026 with month-over-month growth"
  ```
- **Automated AI Visualization**: AI automatically selects and renders optimal chart types based on dataset statistics (time-series, categorical distributions, heatmaps).
- **AI Query Optimization & Self-Healing**: Automatically detect SQL syntax errors, missing columns, or performance bottlenecks, providing instant schema-aware fixes.
- **RAG Schema Indexing**: Vectorized indexing of database schemas and table metadata for accurate multi-table joins using OpenAI, Anthropic, Gemini, or local LLMs (Ollama/Llama 3).

### 📊 3. Advanced Dashboarding & Enterprise Security
- **Multi-Chart Grid Canvas**: Arrange multiple live widgets side-by-side in custom interactive HTML/JS layouts inside single cells.
- **Automated Alerting & Export**: Trigger webhook / Slack notifications when live query metrics cross user-defined threshold limits.
- **Enterprise Secret Vaults**: Integration with AWS Secrets Manager, HashiCorp Vault, and Azure Key Vault.

---

## 📄 License

Distributed under the [MIT License](https://opensource.org/licenses/MIT).
