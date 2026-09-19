# `esje` — Credential-Safe SQL Magic & Live Dashboards for Jupyter

[![PyPI Version](https://img.shields.io/pypi/v/esje.svg)](https://pypi.org/project/esje/)
[![Python Versions](https://img.shields.io/pypi/pyversions/esje.svg)](https://pypi.org/project/esje/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: IPython](https://img.shields.io/badge/Framework-IPython-blue.svg)](https://ipython.org)

**E.S.J.E** — *Easy. SQL. Jupyter. Engine.*

`esje` brings powerful, credential-safe `%sql` and `%%sql` magics to Jupyter Notebooks and JupyterLab. Designed for data analysts and engineers, it eliminates hardcoded secrets in `.ipynb` files, seamlessly executes multi-statement SQL alongside Python visualization code, and provides non-blocking auto-refreshing `--live` dashboards with Play/Pause/Stop controls.

---

## ✨ Features

- 🦆 **DuckDB Analytical Engine**: Embedded fast analytical SQL querying over in-memory (`:memory:`) databases, DuckDB files, CSVs, and Parquet datasets.
- 🐘 **Native PostgreSQL Support**: Connect to PostgreSQL databases seamlessly using interactive credential prompts, environment variables (`PGHOST`, `PGUSER`, etc.), or explicit parameters.
- 🐬 **MySQL & MariaDB Support**: Connect to MySQL databases with pure Python drivers (`pymysql` + SQLAlchemy).
- 🌐 **Login with Google**: One-click browser OAuth2 login for BigQuery — no service account JSON required.
- 🔒 **Zero Hardcoded Secrets**: Interactive prompts (`getpass` for passwords) and automatic `.env` / environment variable fallbacks prevent password leaks in notebooks, git commits, or exports.
- ☁️ **Google BigQuery Native Driver**: Query BigQuery directly via browser login, Application Default Credentials (ADC), or service account key files.
- ⚡ **PyArrow High-Performance Backend**: Optional PyArrow integration for memory-efficient, fast query execution on large datasets.
- 📊 **SQL + Python Inline Execution**: Write SQL queries and Python plotting code (`matplotlib`, `seaborn`, `plotly`) in the same `%%sql` cell.
- ⏱️ **Non-Blocking `--live` Dashboards**: Auto-refresh queries on a timer without blocking the Jupyter kernel. Includes interactive Play/Pause/Stop widget controls.
- 📝 **Multi-Statement Execution**: Execute multi-statement SQL cells (`CREATE TABLE`, `INSERT INTO`, `SELECT`) seamlessly in a single cell execution block.
- 🔌 **Named Connection Registry**: Connect to multiple databases/warehouses and switch between them using `-c <name>` or `esje.use()`.
- 🗣️ **MySQL-Style Dialect Translation**: Use familiar `SHOW DATABASES`, `SHOW TABLES`, `DESCRIBE table` commands — esje auto-translates them to BigQuery's `INFORMATION_SCHEMA` queries.
- 🛡️ **Clean Exception Handling**: Friendly, concise error messages without distracting multi-page Python tracebacks.

---

## 📦 Installation

```bash
pip install esje
```

For **DuckDB** support:

```bash
pip install "esje[duckdb]"
```

For **PostgreSQL** support:

```bash
pip install "esje[postgres]"
```

For **Google BigQuery** support (includes browser login):

```bash
pip install "esje[bigquery]"
```

For all extras:

```bash
pip install "esje[duckdb,postgres,bigquery,pyarrow]"
```

---

## 🚀 Quickstart

### 1. Load the Extension

```python
%load_ext esje
```

### 2. Connect to DuckDB

#### 🦆 In-Memory Database (Default)

```python
import esje

# Connects to an in-memory DuckDB database (':memory:')
conn = esje.connect_duckdb()
```

#### 🦆 Local DuckDB File

```python
conn = esje.connect_duckdb(
    name="my_duck",
    database="my_data.duckdb",
    read_only=False
)
```

#### 🦆 Generic `esje.connect()` Dispatch

```python
conn = esje.connect(dialect="duckdb", database="analytics.duckdb")
# Aliases supported: 'duckdb', 'duck'
```

---

### 3. Connect to PostgreSQL

```python
conn = esje.connect_postgres(name="my_pg", host="localhost", user="postgres", database="analytics_db")
```

---

### 4. Connect to MySQL

```python
conn = esje.connect_mysql(name="default", host="localhost", user="root", database="app_db")
```

---

### 5. Connect to Google BigQuery

```python
conn = esje.connect_bigquery(name="bq", project="my-gcp-project", auth_method="browser")
```

---

## 💡 Usage Examples

### DuckDB Querying (Parquet / CSV Querying)

Query external files directly in Jupyter using DuckDB SQL:

```sql
%%sql -c duckdb
SELECT 
    passenger_count, 
    AVG(trip_distance) AS avg_distance,
    AVG(fare_amount) AS avg_fare
FROM 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet'
GROUP BY passenger_count
ORDER BY passenger_count;
```

### Line Magic (`%sql`)

```python
%sql SELECT * FROM users LIMIT 5

# Query specific DuckDB connection
%sql -c duckdb SELECT * FROM 'data.csv' LIMIT 10
```

### Multi-Statement Cell Magic (`%%sql`)

Execute table creation and bulk insertion in a single cell:

```sql
%%sql -c duckdb
CREATE TABLE products (
    id INT,
    product_name VARCHAR,
    price DOUBLE
);

INSERT INTO products VALUES
    (1, 'Laptop', 1299.99),
    (2, 'Mouse', 25.50),
    (3, 'Keyboard', 75.00);
```

### Save Query Output to a Pandas DataFrame

```python
df = %sql SELECT * FROM products WHERE price > 50
```

---

### 📊 SQL + Python in One Cell

Combine SQL data extraction with immediate visualization. The result DataFrame is automatically available as `df`:

```python
%%sql -c duckdb
SELECT product_name, price FROM products ORDER BY price DESC;

import matplotlib.pyplot as plt

df.plot(x='product_name', y='price', kind='bar',
        title='Product Prices', color='teal', figsize=(8, 4))
plt.tight_layout()
plt.show()
```

---

## 🔄 Non-Blocking Live Dashboards (`--live`)

Auto-refresh dashboards on a timer without blocking the Jupyter kernel:

```python
%%sql -c duckdb --live 2.0 -o df_live
SELECT 
    product_name, price 
FROM products;

import matplotlib.pyplot as plt

df_live.plot(x='product_name', y='price', kind='bar',
            title='Live Product Dashboard', color='darkcyan', figsize=(7, 3.5))
plt.tight_layout()
plt.show()
```

Each live widget includes interactive **▶️ Play / ⏸ Pause / ⏹ Stop** buttons.

---

## 🔑 Environment Variables

### DuckDB Environment Variables:

| Variable | Purpose | Fallback |
|---|---|---|
| `ESJE_DUCKDB_DATABASE` / `DUCKDB_DATABASE` | Path to DuckDB file or `:memory:` | `:memory:` |
| `ESJE_DUCKDB_READ_ONLY` | Read-only mode (`true`/`false`) | `False` |

### PostgreSQL Environment Variables:

| Variable | Purpose | Fallback |
|---|---|---|
| `ESJE_POSTGRES_HOST` / `POSTGRES_HOST` / `PGHOST` | Hostname or IP | `localhost` |
| `ESJE_POSTGRES_PORT` / `POSTGRES_PORT` / `PGPORT` | Port number | `5432` |
| `ESJE_POSTGRES_USER` / `POSTGRES_USER` / `PGUSER` | Database username | `postgres` |
| `ESJE_POSTGRES_PASSWORD` / `POSTGRES_PASSWORD` / `PGPASSWORD` | Database password | Prompt via `getpass` |
| `ESJE_POSTGRES_DATABASE` / `POSTGRES_DATABASE` / `PGDATABASE` | Target database name | `postgres` |

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
esje.use("duckdb")       # Set default connection for %sql
esje.close("duckdb")     # Close a specific connection
esje.close_all()         # Close all connections + stop live widgets
```

---

## 🔮 Roadmap

### 🌐 Universal Database Connectivity
- [x] **DuckDB** ✅ *(Released in v0.5.0)*
- [x] **PostgreSQL** ✅ *(Released in v0.4.0)*
- [x] **MySQL & MariaDB** ✅
- [x] **Google BigQuery** ✅
- [ ] **SQLite**
- [ ] **Snowflake, Databricks, Redshift, ClickHouse**

---

## 📄 License

Distributed under the [MIT License](https://opensource.org/licenses/MIT).
