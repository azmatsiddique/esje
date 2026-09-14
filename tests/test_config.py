"""Tests for esje.config."""

from esje.config import Config, config


def test_config_defaults():
    cfg = Config()
    assert cfg.verbose_errors is False
    assert cfg.max_display_rows == 20
    assert cfg.auto_commit is True
    assert cfg.use_pyarrow is False


def test_config_mutation_and_reset():
    config.verbose_errors = True
    config.max_display_rows = 50
    config.auto_commit = False
    config.use_pyarrow = True

    assert config.verbose_errors is True
    assert config.max_display_rows == 50
    assert config.auto_commit is False
    assert config.use_pyarrow is True

    config.reset()
    assert config.verbose_errors is False
    assert config.max_display_rows == 20
    assert config.auto_commit is True
    assert config.use_pyarrow is False


def test_config_repr():
    cfg = Config()
    r = repr(cfg)
    assert "verbose_errors=False" in r
    assert "max_display_rows=20" in r
    assert "use_pyarrow=False" in r

