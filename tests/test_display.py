"""Tests for esje.display module."""

import pandas as pd

from esje.config import config
from esje.display import DisplayWrapper, format_result


def test_display_wrapper_truncation_and_delegation():
    df = pd.DataFrame({"col": range(50)})
    wrapper = DisplayWrapper(df, max_rows=10)

    # Test DataFrame delegation
    assert len(wrapper) == 50
    assert list(wrapper.columns) == ["col"]
    assert wrapper["col"].iloc[0] == 0

    # Test HTML representation note
    html = wrapper._repr_html_()
    assert "Showing 10 of 50 rows" in html
    assert "Full DataFrame retained" in html

    # Test text representation note
    text_repr = repr(wrapper)
    assert "[Showing 10 of 50 rows. Full DataFrame retained]" in text_repr


def test_format_result():
    config.max_display_rows = 5
    df = pd.DataFrame({"val": range(10)})
    res_df = format_result(df)

    assert isinstance(res_df, DisplayWrapper)
    assert len(res_df.df) == 10

    dml_dict = {"status": "OK", "rowcount": 3}
    res_dml = format_result(dml_dict)
    assert "Affected rows: 3" in res_dml
