"""Base driver interface definition."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union

import pandas as pd


class BaseDriver(ABC):
    """Abstract base class for database drivers in esje."""

    @abstractmethod
    def connect(self) -> None:
        """Establish the database connection engine and validate with a ping."""
        pass

    @abstractmethod
    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Execute a raw SQL query.

        Returns a DataFrame for SELECT-like queries, or a dictionary summary for DDL/DML.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database engine resources."""
        pass

    @property
    @abstractmethod
    def dialect(self) -> str:
        """Return dialect name (e.g. 'mysql')."""
        pass
