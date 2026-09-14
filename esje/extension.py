"""IPython extension registration hooks."""

import sys
from IPython.core.magic import Magics

import esje
from esje.magics import SqlMagics


def load_ipython_extension(ipython) -> None:
    """Load the extension in IPython: %load_ext esje"""
    ipython.register_magics(SqlMagics)
    ipython.user_ns["esje"] = sys.modules.get("esje", esje)


def unload_ipython_extension(ipython) -> None:
    """Unload the extension from IPython."""
    pass



