# PRD: `esje` — SQL Magic for Jupyter Notebooks

## 1. Summary
`esje` is a Python pip package that brings SQL-in-notebook workflows to Jupyter/IPython, similar in spirit to `ipython-sql` / `jupysql`, but with a simpler, opinionated connection flow: the user loads the extension, connects with a guided (prompted) credential flow instead of a connection-string, and runs SQL directly in notebook cells via a `%sql` / `%%sql` magic.

**v1 scope:** MySQL only.
**Future scope:** PostgreSQL and other DBs via a pluggable driver interface.

## 2. Problem Statement
Data engineers/analysts working in Jupyter often want to run ad-hoc SQL against a database without leaving the notebook, without hardcoding credentials in cells, and without writing boilerplate `pymysql`/`sqlalchemy` connection code every time. Existing tools (`ipython-sql`, `jupysql`) require a SQLAlchemy connection string, which is easy to leak into notebook history/git. `esje` should ask for connection details interactively (or via secure env vars) and manage the query loop.

## 3. Goals
- One-line extension load: `%load_ext esje`
- A `connect()` helper that prompts for `username`, `password` (masked), `hostname`, `port` (with sensible default), and `database` name
- A `%sql` line magic and `%%sql` cell magic to run queries against the active connection
- Return query results as a `pandas.DataFrame` and pretty-print in the notebook
- Support multiple **named** connections so a user can switch between databases across cells
- Never persist plaintext password to notebook cell output or `.ipynb` file
- Reasonable error messages for connection/auth/query failures (no raw stack traces by default)

## 4. Non-Goals (v1)
- No ORM/model layer — this is a raw-SQL runner
- No query result caching/persistence beyond the current kernel session
- No GUI/connection manager UI
- No non-MySQL database support in v1 (Postgres etc. planned for v2)
- No async query execution in v1

## 5. Target User
Data/ML engineers and analysts already using Jupyter/JupyterLab/VS Code notebooks who want fast, low-boilerplate SQL access during EDA, debugging, or reporting.

## 6. User Stories
1. As a user, I load the extension once per notebook with `%load_ext esje`.
2. As a user, I call `conn = esje.connect()` (or a MySQL-specific alias) and get prompted for host, port, username, password, and DB name — so I never type my password into a visible cell.
3. As a user, once connected, I run `%sql SELECT * FROM orders LIMIT 10` in any cell and get a DataFrame rendered as a table.
4. As a user, I can run multi-line queries with `%%sql`.
5. As a user, I can assign query results to a variable: `df = %sql SELECT * FROM orders`.
6. As a user, if I have multiple connections open, I can pick which one a query runs against.
7. As a user, I get a clear error if my query fails (SQL syntax, permissions, connection dropped) instead of a raw traceback.

## 7. Proposed API / UX

```python
# Cell 1
%load_ext esje

# Cell 2
conn = esje.connect_mysql()
# Prompts (masked password input via getpass):
#   Host [localhost]:
#   Port [3306]:
#   Username:
#   Password:
#   Database:

# Cell 3
%sql SELECT * FROM customers LIMIT 5

# Cell 4 (multi-line)
%%sql
SELECT region, COUNT(*) 
FROM orders
GROUP BY region

# Cell 5 (capture result)
df = %sql SELECT * FROM orders WHERE amount > 100
```

### Design decisions
| Decision | Rationale |
|---|---|
| `connect_mysql()` prompts interactively via `input()`/`getpass` rather than a connection string | Avoids credentials landing in cell source / notebook JSON / git history |
| Also support env vars (`ESJE_MYSQL_HOST`, `ESJE_MYSQL_USER`, etc.) and `.env` file | Enables non-interactive use in scripts/CI, and reuse across sessions |
| Default active connection is the most recently created; `%sql -c <name>` switches | Keeps common case (one DB) simple while supporting multi-DB |
| Results returned as `pandas.DataFrame`, displayed via IPython rich display | Matches expectations from `jupysql`/pandas ecosystem |
| Underlying driver: `pymysql` (pure Python, no C build deps) via SQLAlchemy engine | Easiest install experience (`pip install esje`), avoids `mysqlclient` build issues |

## 8. Functional Requirements

### 8.1 Extension loading
- `%load_ext esje` registers the `sql` line and cell magic with IPython's magic system, following the standard `IPython.core.magic` extension pattern (`load_ipython_extension(ipython)`).

### 8.2 Connection
- `esje.connect_mysql(name="default", host=None, port=None, user=None, password=None, database=None)`
  - Any parameter left `None` is prompted for interactively (password via `getpass.getpass`, never echoed).
  - Falls back to environment variables if set and not prompted (for non-interactive/CI use).
  - Validates connection on creation (a lightweight `SELECT 1`) and raises a clear `esje.ConnectionError` on failure.
  - Stores the connection in an in-memory registry keyed by `name`; if `name` already exists, prompts to reuse or overwrite.
  - Returns a lightweight `Connection` handle object (does not expose the raw password afterward, e.g. `repr()` masks it).

### 8.3 Query execution
- `%sql <query>` — runs a single-line query against the active (or `-c <name>`-selected) connection.
- `%%sql` — runs a multi-line query from the cell body.
- `%sql -c mydb SELECT ...` — run against a specific named connection.
- Return value: `pandas.DataFrame` for `SELECT`-like queries; a short status string/rowcount for `INSERT`/`UPDATE`/`DELETE`/DDL.
- Auto-display: if not assigned to a variable, the DataFrame is rendered via IPython's rich display (HTML table), truncated to a configurable max row count (default 20) with a note on how to see more.

### 8.4 Multiple connections
- `esje.connections()` — lists active named connections (name, host, database — no credentials).
- `esje.use(name)` — sets the default/active connection for subsequent `%sql` calls without `-c`.
- `esje.close(name)` / `esje.close_all()`.

### 8.5 Error handling
- Connection errors (bad host/port/auth) → friendly message: what failed, and a hint (e.g. "check host/port" or "access denied — check username/password").
- Query errors (syntax, missing table, permissions) → surface the DB error message concisely, suppress the full Python traceback by default; a config flag (`esje.config.verbose_errors = True`) restores full tracebacks for debugging.

### 8.6 Security
- Passwords are never written to notebook cell source or output.
- Passwords held in memory only for the session (not written to disk/config file) unless the user explicitly opts into env var / `.env` usage.
- `repr()`/`str()` of connection objects never include the password.

## 9. Non-Functional Requirements
- **Install:** `pip install esje`, pure-Python dependencies only (no system MySQL client library required) so it installs cleanly in any Jupyter environment.
- **Compatibility:** Python 3.9+; works in Jupyter Notebook, JupyterLab, and VS Code's Jupyter extension (anywhere IPython magics work).
- **Performance:** No hard requirement beyond "as fast as the underlying `pymysql`/SQLAlchemy round trip"; large result sets should not hang the kernel (stream/limit by default, e.g. cap `%sql` auto-display at N rows without truncating the returned DataFrame's actual data unless the user requests a `LIMIT`).
- **Dependencies (proposed):** `ipython`, `pandas`, `sqlalchemy`, `pymysql`, `python-dotenv` (optional/env support), `prettytable` or rely on pandas' own HTML rendering for display.

## 10. Architecture Sketch
```
esje/
├── __init__.py          # public API: connect_mysql, use, connections, close, close_all
├── extension.py         # load_ipython_extension / unload_ipython_extension
├── magics.py            # SqlMagics(Magics) class: line_magic('sql'), cell_magic('sql')
├── connection.py         # Connection class wrapping SQLAlchemy engine; registry of named connections
├── drivers/
│   ├── base.py           # DriverInterface (connect, execute, dialect-specific bits)
│   └── mysql.py          # MySQL driver using pymysql + SQLAlchemy
├── prompts.py            # interactive input()/getpass prompting, env var fallback
├── display.py            # DataFrame formatting/truncation for notebook display
├── errors.py             # esje.ConnectionError, esje.QueryError
└── config.py             # verbose_errors, max_display_rows, etc.
```
This driver-interface split is what makes Postgres (v2) additive: implement `drivers/postgres.py` + `connect_postgres()`, reusing `magics.py`/`connection.py`/`display.py` unchanged.

## 11. Milestones / Roadmap
| Phase | Scope |
|---|---|
| M1 — MVP | `%load_ext esje`, `connect_mysql()` interactive prompt, `%sql`/`%%sql` against a single connection, DataFrame results, basic error handling |
| M2 | Multiple named connections, `-c` flag, `esje.use()`, env var / `.env` support |
| M3 | Config (`max_display_rows`, `verbose_errors`), better error messages, docs + PyPI publish |
| M4 (v2) | PostgreSQL driver, generalize `connect()` to dispatch by DB type |
| M5 (stretch) | Query history (`esje.history()`), `%sql --params` for parameterized queries, `.sql` file execution |

## 12. Open Questions
- Should `connect_mysql()` prompting happen even when called non-interactively (e.g. in a script), or auto-detect and require explicit params/env vars in that case?
- Should the default connection name auto-increment (`conn1`, `conn2`) or require the user to name it?
- Do we want an `%sql --limit N` override per query, in addition to the global `max_display_rows` config?
- Package name availability on PyPI — confirm `esje` isn't taken before publishing.

## 13. Success Metrics (for a personal/OSS project)
- Time from `pip install esje` to first successful query < 2 minutes for a new user.
- Zero plaintext credentials appear in notebook `.ipynb` JSON after normal use.
- Works unmodified across Jupyter Notebook, JupyterLab, and VS Code Jupyter.
