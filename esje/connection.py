"""Connection object and ConnectionManager registry."""

from typing import Any, Dict, List, Optional, Union

import pandas as pd

from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, ConfigurationError


class Connection:
    """Lightweight Connection handle wrapping a database driver."""

    def __init__(self, name: str, driver: BaseDriver) -> None:
        self.name = name
        self.driver = driver

    @property
    def host(self) -> str:
        return getattr(self.driver, "host", "unknown")

    @property
    def port(self) -> int:
        return getattr(self.driver, "port", 0)

    @property
    def user(self) -> str:
        return getattr(self.driver, "user", "")

    @property
    def database(self) -> str:
        return getattr(self.driver, "database", "")

    @property
    def dialect(self) -> str:
        return self.driver.dialect

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Execute a query against this connection."""
        return self.driver.execute(query)

    def close(self) -> None:
        """Close the underlying driver."""
        self.driver.close()

    def __repr__(self) -> str:
        db_str = f" db='{self.database}'" if self.database else ""
        return (
            f"<esje.Connection name='{self.name}' dialect='{self.dialect}' "
            f"user='{self.user}' host='{self.host}:{self.port}'{db_str}>"
        )

    def __str__(self) -> str:
        return self.__repr__()


class ConnectionManager:
    """Registry and manager for active database connections."""

    def __init__(self) -> None:
        self._connections: Dict[str, Connection] = {}
        self._active: Optional[str] = None

    @property
    def active_name(self) -> Optional[str]:
        return self._active

    def add(self, conn: Connection, set_active: bool = True) -> Connection:
        """Register a connection. Overwrites if name exists after closing old connection."""
        if conn.name in self._connections:
            # Close existing connection before replacing
            try:
                self._connections[conn.name].close()
            except Exception:
                pass

        self._connections[conn.name] = conn
        if set_active or self._active is None:
            self._active = conn.name
        return conn

    def get(self, name: Optional[str] = None) -> Connection:
        """Get connection by name or active connection if name is None."""
        target_name = name or self._active
        if not target_name:
            raise ConnectionError(
                "No active connection. Connect first using esje.connect_mysql() or esje.connect().",
                hint="Run `conn = esje.connect_mysql()` to establish a connection.",
            )
        if target_name not in self._connections:
            raise ConfigurationError(
                f"Connection '{target_name}' not found.",
                hint=f"Available connections: {list(self._connections.keys())}",
            )
        return self._connections[target_name]

    def use(self, name: str) -> str:
        """Set the active connection name."""
        if name not in self._connections:
            raise ConfigurationError(
                f"Connection '{name}' not found.",
                hint=f"Available connections: {list(self._connections.keys())}",
            )
        self._active = name
        return f"Active connection set to '{name}'"

    def list_connections(self) -> List[Dict[str, Any]]:
        """Return list of metadata dicts for active connections (no passwords)."""
        summary = []
        for name, conn in self._connections.items():
            summary.append(
                {
                    "name": name,
                    "active": "*" if name == self._active else "",
                    "dialect": conn.dialect,
                    "host": conn.host,
                    "port": conn.port,
                    "user": conn.user,
                    "database": conn.database,
                }
            )
        return summary

    def close(self, name: str) -> str:
        """Close connection by name."""
        if name not in self._connections:
            raise ConfigurationError(f"Connection '{name}' not found.")

        conn = self._connections.pop(name)
        conn.close()

        if self._active == name:
            self._active = next(iter(self._connections.keys()), None)

        return f"Connection '{name}' closed."

    def close_all(self) -> None:
        """Close all open connections."""
        for conn in self._connections.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()
        self._active = None


# Global singleton instance
manager = ConnectionManager()
