"""Notebook display formatting and result truncation."""

from typing import Any, Dict, Union

import pandas as pd

from esje.config import config


class DisplayWrapper:
    """Wrapper around pandas DataFrame to customize rich HTML/Text notebook display without modifying original data."""

    def __init__(self, df: pd.DataFrame, max_rows: int) -> None:
        self._df = df
        self._max_rows = max_rows

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _repr_html_(self) -> str:
        total_rows = len(self._df)
        if self._max_rows and total_rows > self._max_rows:
            truncated_df = self._df.head(self._max_rows)
            html = truncated_df._repr_html_()
            note = (
                f'<div style="font-size: 0.85em; color: #666; margin-top: 4px;">'
                f'<i>Showing {self._max_rows} of {total_rows} rows. (Full DataFrame retained)</i>'
                f'</div>'
            )
            return html + note
        return self._df._repr_html_()

    def _repr_pretty_(self, p: Any, cycle: bool) -> None:
        total_rows = len(self._df)
        if self._max_rows and total_rows > self._max_rows:
            p.text(str(self._df.head(self._max_rows)))
            p.text(f"\n[Showing {self._max_rows} of {total_rows} rows. Full DataFrame retained]")
        else:
            p.text(str(self._df))

    def __getattr__(self, item: str) -> Any:
        return getattr(self._df, item)

    def __getitem__(self, key: Any) -> Any:
        return self._df[key]

    def __len__(self) -> int:
        return len(self._df)

    def __iter__(self) -> Any:
        return iter(self._df)

    def __repr__(self) -> str:
        total_rows = len(self._df)
        if self._max_rows and total_rows > self._max_rows:
            return (
                f"{self._df.head(self._max_rows)}\n"
                f"[Showing {self._max_rows} of {total_rows} rows. Full DataFrame retained]"
            )
        return repr(self._df)


def format_result(result: Union[pd.DataFrame, Dict[str, Any]]) -> Any:
    """Format query result for IPython output.

    Returns DisplayWrapper for DataFrames so IPython displays truncated view while keeping original DataFrame.
    Returns string for DDL/DML execution status.
    """
    if isinstance(result, pd.DataFrame):
        return DisplayWrapper(result, max_rows=config.max_display_rows)
    elif isinstance(result, dict):
        status = result.get("status", "Success")
        rowcount = result.get("rowcount", 0)
        return f"{status} (Affected rows: {rowcount})"
    return str(result)
