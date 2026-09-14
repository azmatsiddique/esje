"""Configuration options for esje."""


class Config:
    """Global configuration settings for esje."""

    def __init__(self) -> None:
        self.verbose_errors: bool = False
        self.max_display_rows: int = 20
        self.auto_commit: bool = True
        self.use_pyarrow: bool = False

    def reset(self) -> None:
        """Reset configuration to default values."""
        self.verbose_errors = False
        self.max_display_rows = 20
        self.auto_commit = True
        self.use_pyarrow = False

    def __repr__(self) -> str:
        return (
            f"Config(verbose_errors={self.verbose_errors}, "
            f"max_display_rows={self.max_display_rows}, "
            f"auto_commit={self.auto_commit}, "
            f"use_pyarrow={self.use_pyarrow})"
        )



config = Config()
