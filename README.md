# `esje` — Credential-Safe SQL Magic & Live Dashboards for Jupyter

[![PyPI Version](https://img.shields.io/pypi/v/esje.svg)](https://pypi.org/project/esje/)
[![Python Versions](https://img.shields.io/pypi/pyversions/esje.svg)](https://pypi.org/project/esje/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: IPython](https://img.shields.io/badge/Framework-IPython-blue.svg)](https://ipython.org)

`esje` brings powerful, credential-safe `%sql` and `%%sql` magics to Jupyter Notebooks and JupyterLab. Designed for data analysts and engineers, it eliminates hardcoded secrets in `.ipynb` files, seamlessly executes SQL alongside Python visualization code, and provides non-blocking auto-refreshing `--live` dashboards with Play/Pause/Stop controls.

---

## ✨ Features

- 🔒 **Zero Hardcoded Secrets**: Interactive `getpass` prompts and automatic `.env` / environment variable fallbacks prevent password leaks in notebook cells, git commits, or exports.
- ⚡ **PyArrow High-Performance Backend**: Optional PyArrow data type integration for memory-efficient and fast query execution on large datasets.
- 📊 **SQL + Python Inline Execution**: Write SQL queries and Python plotting code (`matplotlib`, `seaborn`, `plotly`) in the exact same `%%sql` cell.
- ⏱️ **Non-Blocking `--live` Dashboards**: Run queries on an auto-refresh timer without blocking the Jupyter kernel execution thread. Includes interactive Play/Pause/Stop widget controls.
- 🔌 **Named Connection Registry**: Connect to multiple databases and switch between them effortlessly using `-c <conn_name>` or `esje.use()`.
- 🛡️ **Clean Exception Handling**: Friendly, concise error messages by default without distracting multi-page Python tracebacks.

---

## 📦 Installation

Install `esje` via `pip`:

```bash
pip install esje
```

For high-performance PyArrow data type acceleration, install with the optional `pyarrow` extra:

```bash
pip install "esje[pyarrow]"
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

Or connect with a named connection:

```python
esje.connect_mysql(name="analytics", database="sales_db")
```

---

## 💡 Usage Examples

### Line Magic (`%sql`)

Run a quick one-liner SQL query:

```python
%sql SELECT * FROM users LIMIT 5
```

Assign the query result directly to a Python variable:

```python
df = %sql SELECT country, SUM(revenue) FROM sales GROUP BY country
```

### Cell Magic (`%%sql`)

Execute multi-line SQL queries and capture results into a DataFrame with `-o <var_name>`:

```python
%%sql -o sales_summary
SELECT 
    category,
    COUNT(*) AS total_orders,
    SUM(revenue) AS total_revenue
FROM sales_data
WHERE created_at >= '2026-01-01'
GROUP BY category
ORDER BY total_revenue DESC;
```

### SQL + Python Code Execution in a Single Cell

Combine SQL data extraction with immediate visualization. The result DataFrame is automatically made available to your Python snippet as `df`:

```python
%%sql
SELECT category, SUM(revenue) AS total_revenue 
FROM sales_data 
GROUP BY category;

import matplotlib.pyplot as plt

df.plot(
    x='category', 
    y='total_revenue', 
    kind='bar', 
    title='Total Revenue by Category',
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
%%sql --live 2
SELECT category, SUM(revenue) AS total_revenue 
FROM sales_data 
GROUP BY category;

import matplotlib.pyplot as plt

df.plot(
    x='category', 
    y='total_revenue', 
    kind='bar', 
    title='Real-Time Revenue Dashboard',
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

When calling `esje.connect_mysql()`, credentials are automatically resolved in the following priority order:

1. **Explicit Parameters**: Arguments passed directly to `esje.connect_mysql(host=..., user=..., password=...)`.
2. **Environment File (`.env`)**: Variables defined in a local `.env` file (`ESJE_MYSQL_HOST`, `ESJE_MYSQL_USER`, `ESJE_MYSQL_PASSWORD`, `ESJE_MYSQL_DATABASE`, `ESJE_MYSQL_PORT`).
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
esje.use("analytics")

# Close a specific connection
esje.close("analytics")

# Close all connections and stop all live widgets
esje.close_all()
```

---

## 🔮 Future Scope & Roadmap

`esje` is expanding into a universal, AI-native data connectivity ecosystem for notebook environments. Upcoming features include:

### 🌐 1. Universal Database & Data Lake Connectivity
- **Relational Databases**: Native drivers for PostgreSQL, SQLite, Oracle, Microsoft SQL Server, and CockroachDB.
- **Big Data & Data Warehouses**: Apache Hive, Trino / Presto, Apache Spark SQL, Databricks, Snowflake, Google BigQuery, Amazon Redshift, and ClickHouse.
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
