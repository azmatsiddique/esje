# `esje` — Credential-Safe SQL Magic & Live Dashboards for Jupyter

[![PyPI Version](https://img.shields.io/pypi/v/esje.svg)](https://pypi.org/project/esje/)
[![Python Versions](https://img.shields.io/pypi/pyversions/esje.svg)](https://pypi.org/project/esje/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: IPython](https://img.shields.io/badge/Framework-IPython-blue.svg)](https://ipython.org)

**E.S.J.E** — *Easy. SQL. Jupyter. Engine.*

`esje` brings powerful, credential-safe `%sql` and `%%sql` magics to Jupyter Notebooks and JupyterLab. Designed for data analysts and engineers, it eliminates hardcoded secrets in `.ipynb` files, seamlessly executes multi-statement SQL alongside Python visualization code, and provides non-blocking auto-refreshing `--live` dashboards with Play/Pause/Stop controls.

---

## ✨ Features

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

For **PostgreSQL** support:

```bash
pip install "esje[postgres]"
```

For **Google BigQuery** support (includes browser login):

```bash
pip install "esje[bigquery]"
```

For high-performance **PyArrow** acceleration:

```bash
pip install "esje[pyarrow,bigquery,postgres]"
```

---

## 🚀 Quickstart

### 1. Load the Extension

```python
%load_ext esje
```

### 2. Connect to PostgreSQL

#### 🐘 Option A — Interactive Prompting (Secure — Password Masked)

When called without arguments, `esje` interactively prompts for host, port, user, password, and database:

```python
import esje

# Prompts: Host [localhost], Port [5432], Username [postgres], Password (masked), DB [postgres]
conn = esje.connect_postgres()
```

#### 🐘 Option B — Explicit Parameters

```python
conn = esje.connect_postgres(
    name="my_pg",              # Connection name (default: "postgres")
    host="localhost",
    port=5432,
    user="postgres",
    password="my_secure_password",
    database="analytics_db",
    sslmode="prefer"           # Optional: 'require', 'prefer', 'disable'
)
```

#### 🐘 Option C — Environment Variables or `.env` File

Supports standard PostgreSQL environment variables (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE`) or `ESJE_POSTGRES_*`:

```python
conn = esje.connect_postgres(interactive_prompt=False)
```

#### 🐘 Option D — Generic `esje.connect()` Dispatch

```python
conn = esje.connect(dialect="postgres", host="localhost", database="mydb")
# Aliases supported: 'postgres', 'postgresql', 'pg', 'psql'
```

---

### 3. Connect to MySQL

```python
conn = esje.connect_mysql(name="default", host="localhost", user="root", database="app_db")
```

---

### 4. Connect to Google BigQuery

#### 🌐 Option A — Login with Google (Browser) — *Recommended*

Opens your browser for Google Sign-In. No JSON key file needed.

```python
conn = esje.connect_bigquery(
    name="bq",
    project="my-gcp-project",
    auth_method="browser"       # opens browser → sign in → done!
)
```

---

## 💡 Usage Examples

### Line Magic (`%sql`)

```python
%sql SELECT * FROM users LIMIT 5

# Query specific connection
%sql -c my_pg SELECT * FROM pg_tables WHERE schemaname = 'public'
```

### Multi-Statement Cell Magic (`%%sql`)

Execute table creation and bulk insertion in a single cell:

```sql
%%sql -c my_pg
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(100),
    price NUMERIC(10, 2)
);

INSERT INTO products (product_name, price) VALUES
    ('Laptop', 1299.99),
    ('Mouse', 25.50),
    ('Keyboard', 75.00);
```

### Save Query Output to a Pandas DataFrame

```python
df = %sql SELECT * FROM products WHERE price > 50
```

Or via `-o` parameter:

```sql
%%sql -c my_pg -o sales_summary
SELECT 
    product_name,
    COUNT(*) AS total_sold,
    SUM(price) AS revenue
FROM products
GROUP BY product_name
ORDER BY revenue DESC;
```

---

### 📊 SQL + Python in One Cell

Combine SQL data extraction with immediate visualization. The result DataFrame is automatically available as `df`:

```python
%%sql -c my_pg
SELECT 
    schemaname, 
    COUNT(*) AS table_count
FROM pg_tables
GROUP BY schemaname;

import matplotlib.pyplot as plt

df.plot(x='schemaname', y='table_count', kind='bar',
        title='Tables per Schema', color='steelblue', figsize=(8, 4))
plt.tight_layout()
plt.show()
```

---

## 🔄 Non-Blocking Live Dashboards (`--live`)

Auto-refresh dashboards on a timer without blocking the Jupyter kernel:

```python
%%sql -c my_pg --live 2.0 -o df_live
SELECT 
    state, 
    COUNT(*) AS connection_count
FROM pg_stat_activity
WHERE state IS NOT NULL
GROUP BY state;

import matplotlib.pyplot as plt

df_live.plot(x='state', y='connection_count', kind='bar',
            title='Live PostgreSQL Active Connections', color='teal', figsize=(7, 3.5))
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

## 🔑 Credential Resolution & Environment Variables

### PostgreSQL Environment Variables:

| Variable | Purpose | Fallback |
|---|---|---|
| `ESJE_POSTGRES_HOST` / `POSTGRES_HOST` / `PGHOST` | Hostname or IP | `localhost` |
| `ESJE_POSTGRES_PORT` / `POSTGRES_PORT` / `PGPORT` | Port number | `5432` |
| `ESJE_POSTGRES_USER` / `POSTGRES_USER` / `PGUSER` | Database username | `postgres` |
| `ESJE_POSTGRES_PASSWORD` / `POSTGRES_PASSWORD` / `PGPASSWORD` | Database password | Prompt via `getpass` |
| `ESJE_POSTGRES_DATABASE` / `POSTGRES_DATABASE` / `PGDATABASE` | Target database name | `postgres` |
| `ESJE_POSTGRES_SSLMODE` / `PGSSLMODE` | SSL Connection mode | `None` / driver default |

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
esje.use("my_pg")        # Set default connection for %sql
esje.close("my_pg")      # Close a specific connection
esje.close_all()         # Close all connections + stop live widgets
```

---

## 🔮 Roadmap

### 🌐 Universal Database Connectivity
- [x] **PostgreSQL** ✅ *(Released in v0.4.0)*
- [x] **MySQL & MariaDB** ✅
- [x] **Google BigQuery** ✅
- [ ] **SQLite & DuckDB**
- [ ] **Snowflake, Databricks, Redshift, ClickHouse**

---

## 📄 License

Distributed under the [MIT License](https://opensource.org/licenses/MIT).
