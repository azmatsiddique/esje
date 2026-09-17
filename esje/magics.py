"""IPython magic definitions for %sql and %%sql with --live mode."""

import argparse
import sys
import time
from typing import Any, Optional, Tuple

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
from IPython.display import clear_output, display

from esje.config import config
from esje.connection import manager
from esje.display import DisplayWrapper, format_result
from esje.errors import EsjeError


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sql", description="SQL Magic for Jupyter", add_help=False)
    parser.add_argument("-c", "--connection", type=str, default=None, help="Name of connection to execute against")
    parser.add_argument("-o", "--output", type=str, default=None, help="Variable name to store result DataFrame in")
    parser.add_argument(
        "--live",
        nargs="?",
        const=2.0,
        type=float,
        default=None,
        help="Enable live auto-refresh mode (interval in seconds, default 2.0)",
    )
    return parser


def parse_sql_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[float], str]:
    """Parse line string into (connection_name, output_var, live_interval, remaining_query)."""
    parser = create_parser()
    parts = line.strip().split()

    if not parts:
        return None, None, None, ""

    args, remaining = parser.parse_known_args(parts)
    query = " ".join(remaining)
    return args.connection, args.output, args.live, query


def split_sql_and_python(cell: str) -> Tuple[str, str]:
    """Split cell body into (sql_query, python_code)."""
    raw_cell = cell.strip()
    if not raw_cell:
        return "", ""

    sql_clause_keywords = (
        "select", "with", "insert", "update", "delete",
        "show", "describe", "desc", "explain", "create",
        "drop", "alter", "use", "grant", "revoke", "set",
        "from", "where", "group", "order", "having", "limit",
        "join", "left", "right", "inner", "outer", "on", "and", "or",
        "values", "into", "union", "all", "case", "when", "then", "else", "end",
        "options", "table", "index", "database", "schema"
    )

    python_triggers = (
        "import ", "from ", "plt.", "df.", "fig.", "fig,", "ax.", "ax,", "print(", "pd.", "sns.", "matplotlib", "#"
    )

    lines = raw_cell.splitlines()
    python_start_idx = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        first_word = stripped.split()[0].lower() if stripped.split() else ""

        # Check for inline semicolon split on a single line: e.g. "SELECT * FROM users; df.plot()"
        if ";" in stripped:
            parts = stripped.split(";", 1)
            rest = parts[1].strip()
            if rest:
                rest_first_word = rest.split()[0].lower() if rest.split() else ""
                if rest_first_word not in sql_clause_keywords:
                    is_rest_python = (
                        any(rest.startswith(trig) for trig in python_triggers)
                        or ("from " in rest and " import " in rest)
                        or ("=" in rest and not rest.startswith("("))
                    )
                    if is_rest_python:
                        sql_part = "\n".join(lines[:idx] + [parts[0].strip()]).strip().rstrip(";")
                        py_part = "\n".join([rest] + lines[idx + 1:]).strip()
                        return sql_part, py_part

        if idx == 0:
            continue

        is_python = (
            any(stripped.startswith(trig) for trig in python_triggers)
            or ("from " in stripped and " import " in stripped)
            or (
                "=" in stripped
                and first_word not in sql_clause_keywords
                and not stripped.startswith("(")
                and not stripped.startswith("'")
                and not stripped.startswith('"')
            )
        )

        if is_python:
            python_start_idx = idx
            break

    if python_start_idx is not None:
        sql_lines = lines[:python_start_idx]
        python_lines = lines[python_start_idx:]
        sql_str = "\n".join(sql_lines).strip().rstrip(";")
        python_str = "\n".join(python_lines).strip()
        return sql_str, python_str

    return raw_cell.rstrip(";"), ""










@magics_class
class SqlMagics(Magics):
    """IPython magic class providing %sql line magic and %%sql cell magic."""

    @line_magic("sql")
    def execute_line_sql(self, line: str) -> Any:
        """Run line magic query: %sql [-c connection] [-o output_var] <query>"""
        conn_name, output_var, _, query = parse_sql_line(line)
        if not query:
            print("Usage: %sql [-c connection] [-o output_var] <query>", file=sys.stderr)
            return None

        try:
            conn = manager.get(conn_name)
            raw_result = conn.execute(query)
            formatted = format_result(raw_result)

            if output_var and self.shell:
                target_obj = formatted.df if isinstance(formatted, DisplayWrapper) else formatted
                self.shell.user_ns[output_var] = target_obj

            return formatted
        except EsjeError as exc:
            if config.verbose_errors:
                raise
            print(f"Error: {exc}", file=sys.stderr)
            return None
        except Exception as exc:
            if config.verbose_errors:
                raise
            print(f"Error: {exc}", file=sys.stderr)
            return None

    @cell_magic("sql")
    def execute_cell_sql(self, line: str, cell: str) -> Any:
        """Run cell magic query: %%sql [-c connection] [-o output_var] [--live [interval]] \\n <query_body>"""
        conn_name, output_var, live_interval, _ = parse_sql_line(line)
        sql_query, python_code = split_sql_and_python(cell)

        if not sql_query:
            print("Error: Cell SQL query body cannot be empty.", file=sys.stderr)
            return None

        target_var = output_var or "df"

        if live_interval is not None:
            # Non-blocking Live Mode with Play/Pause/Stop control widget
            try:
                from esje.live import live_manager

                live_manager.create(
                    conn_name=conn_name,
                    sql_query=sql_query,
                    python_code=python_code,
                    target_var=target_var,
                    interval=live_interval,
                    shell=self.shell,
                )
                return None
            except Exception as exc:
                if config.verbose_errors:
                    raise
                print(f"Live mode error: {exc}", file=sys.stderr)
                return None

        else:
            # Standard single execution
            try:
                conn = manager.get(conn_name)
                raw_result = conn.execute(sql_query)
                formatted = format_result(raw_result)

                if self.shell:
                    target_obj = formatted.df if isinstance(formatted, DisplayWrapper) else formatted
                    self.shell.user_ns[target_var] = target_obj

                if python_code:
                    self.shell.ex(python_code)
                    return None
                else:
                    return formatted
            except EsjeError as exc:
                if config.verbose_errors:
                    raise
                print(f"Error: {exc}", file=sys.stderr)
                return None
            except Exception as exc:
                if config.verbose_errors:
                    raise
                print(f"Error: {exc}", file=sys.stderr)
                return None
