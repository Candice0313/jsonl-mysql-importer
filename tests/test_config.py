"""Unit tests for src/config.py."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.config import Config, load_config


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def config_file(tmp_path):
    """Return a helper that writes a JSON config into a temp file and cleans up."""
    files = []

    def _write(data):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
            dir=tmp_path, encoding="utf-8"
        )
        json.dump(data, f)
        f.flush()
        f.close()
        files.append(f.name)
        return f.name

    yield _write

    for path in files:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Default-value tests
# ---------------------------------------------------------------------------

class TestLoadConfigDefaults:
    """load_config() with no arguments should return all default values."""

    def test_returns_config_instance(self):
        cfg = load_config()
        assert isinstance(cfg, Config)

    def test_default_host(self):
        assert load_config().host == "localhost"

    def test_default_port(self):
        assert load_config().port == 3306

    def test_default_database(self):
        assert load_config().database == ""

    def test_default_username(self):
        assert load_config().username == ""

    def test_default_password(self):
        assert load_config().password == ""

    def test_default_alias_file(self):
        assert load_config().alias_file == "alias_table.jsonl"

    def test_default_entity_file(self):
        assert load_config().entity_file == "entities.jsonl"

    def test_default_output_dir(self):
        assert load_config().output_dir == "./output"

    def test_default_batch_size(self):
        assert load_config().batch_size == 1000

    def test_default_max_file_size_mb(self):
        assert load_config().max_file_size_mb == 50

    def test_default_execute(self):
        assert load_config().execute is False


# ---------------------------------------------------------------------------
# File-based loading tests
# ---------------------------------------------------------------------------

FULL_CONFIG_DATA = {
    "database": {
        "host": "db.example.com",
        "port": 3307,
        "database": "entrez_gene",
        "username": "root",
        "password": "secret",
    },
    "files": {
        "alias_file": "alias_table.jsonl",
        "entity_file": "entities.jsonl",
        "output_dir": "/tmp/output",
    },
    "processing": {
        "batch_size": 500,
        "max_file_size_mb": 100,
    },
}


class TestLoadConfigFromFile:
    """load_config() with a JSON file should apply those values."""

    def test_reads_host(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.host == "db.example.com"

    def test_reads_port(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.port == 3307

    def test_reads_database(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.database == "entrez_gene"

    def test_reads_username(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.username == "root"

    def test_reads_password(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.password == "secret"

    def test_reads_output_dir(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.output_dir == "/tmp/output"

    def test_reads_batch_size(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.batch_size == 500

    def test_reads_max_file_size_mb(self, config_file):
        cfg = load_config(config_path=config_file(FULL_CONFIG_DATA))
        assert cfg.max_file_size_mb == 100

    def test_missing_sections_use_defaults(self, config_file):
        path = config_file({"database": {"host": "myhost"}})
        cfg = load_config(config_path=path)
        assert cfg.host == "myhost"
        assert cfg.batch_size == 1000  # processing section missing -> default


# ---------------------------------------------------------------------------
# Override tests
# ---------------------------------------------------------------------------

OVERRIDE_CONFIG_DATA = {
    "database": {
        "host": "file-host",
        "port": 3306,
        "database": "file_db",
        "username": "file_user",
        "password": "file_pass",
    },
    "files": {
        "alias_file": "file_alias.jsonl",
        "entity_file": "file_entity.jsonl",
        "output_dir": "./file_output",
    },
    "processing": {
        "batch_size": 200,
        "max_file_size_mb": 25,
    },
}


class TestLoadConfigOverrides:
    """load_config() overrides should take precedence over file values."""

    def test_override_host(self, config_file):
        cfg = load_config(config_path=config_file(OVERRIDE_CONFIG_DATA), host="override-host")
        assert cfg.host == "override-host"

    def test_override_port(self, config_file):
        cfg = load_config(config_path=config_file(OVERRIDE_CONFIG_DATA), port=5432)
        assert cfg.port == 5432

    def test_override_database(self, config_file):
        cfg = load_config(config_path=config_file(OVERRIDE_CONFIG_DATA), database="override_db")
        assert cfg.database == "override_db"

    def test_override_batch_size(self, config_file):
        cfg = load_config(config_path=config_file(OVERRIDE_CONFIG_DATA), batch_size=9999)
        assert cfg.batch_size == 9999

    def test_non_overridden_file_values_preserved(self, config_file):
        cfg = load_config(config_path=config_file(OVERRIDE_CONFIG_DATA), host="new-host")
        assert cfg.database == "file_db"
        assert cfg.batch_size == 200

    def test_none_override_does_not_overwrite_file_value(self, config_file):
        """Passing None as an override should not replace the file value."""
        cfg = load_config(config_path=config_file(OVERRIDE_CONFIG_DATA), host=None)
        assert cfg.host == "file-host"

    def test_overrides_without_file(self):
        cfg = load_config(host="standalone-host", port=9999)
        assert cfg.host == "standalone-host"
        assert cfg.port == 9999
        assert cfg.database == ""  # default unchanged

    def test_override_execute_true(self):
        cfg = load_config(execute=True)
        assert cfg.execute is True

    def test_override_execute_false(self):
        cfg = load_config(execute=False)
        assert cfg.execute is False


# ---------------------------------------------------------------------------
# Range-validation tests
# ---------------------------------------------------------------------------

class TestConfigValidation:
    """Config.__post_init__ should reject out-of-range numeric fields."""

    # port validation
    def test_port_zero_raises(self):
        with pytest.raises(ValueError, match="port"):
            Config(port=0)

    def test_port_negative_raises(self):
        with pytest.raises(ValueError, match="port"):
            Config(port=-1)

    def test_port_too_large_raises(self):
        with pytest.raises(ValueError, match="port"):
            Config(port=65536)

    def test_port_min_valid(self):
        cfg = Config(port=1)
        assert cfg.port == 1

    def test_port_max_valid(self):
        cfg = Config(port=65535)
        assert cfg.port == 65535

    # batch_size validation
    def test_batch_size_zero_raises(self):
        with pytest.raises(ValueError, match="batch_size"):
            Config(batch_size=0)

    def test_batch_size_negative_raises(self):
        with pytest.raises(ValueError, match="batch_size"):
            Config(batch_size=-5)

    def test_batch_size_one_valid(self):
        cfg = Config(batch_size=1)
        assert cfg.batch_size == 1

    # max_file_size_mb validation
    def test_max_file_size_mb_zero_raises(self):
        with pytest.raises(ValueError, match="max_file_size_mb"):
            Config(max_file_size_mb=0)

    def test_max_file_size_mb_negative_raises(self):
        with pytest.raises(ValueError, match="max_file_size_mb"):
            Config(max_file_size_mb=-10)

    def test_max_file_size_mb_one_valid(self):
        cfg = Config(max_file_size_mb=1)
        assert cfg.max_file_size_mb == 1

    # load_config propagates validation errors from file
    def test_invalid_port_in_file_raises(self, config_file):
        data = {"database": {"port": 0}}
        with pytest.raises(ValueError, match="port"):
            load_config(config_path=config_file(data))

    def test_invalid_batch_size_in_file_raises(self, config_file):
        data = {"processing": {"batch_size": 0}}
        with pytest.raises(ValueError, match="batch_size"):
            load_config(config_path=config_file(data))
