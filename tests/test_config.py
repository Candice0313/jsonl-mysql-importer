"""Unit tests for src/config.py."""

import json
import tempfile
from pathlib import Path

import pytest

from src.config import Config, load_config


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


class TestLoadConfigFromFile:
    """load_config() with a JSON file should apply those values."""

    CONFIG_DATA = {
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

    def _write_config(self, data=None):
        if data is None:
            data = self.CONFIG_DATA
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(data, tmp)
        tmp.flush()
        tmp.close()
        return tmp.name

    def test_reads_host(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.host == "db.example.com"

    def test_reads_port(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.port == 3307

    def test_reads_database(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.database == "entrez_gene"

    def test_reads_username(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.username == "root"

    def test_reads_password(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.password == "secret"

    def test_reads_output_dir(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.output_dir == "/tmp/output"

    def test_reads_batch_size(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.batch_size == 500

    def test_reads_max_file_size_mb(self):
        path = self._write_config()
        cfg = load_config(config_path=path)
        assert cfg.max_file_size_mb == 100

    def test_missing_sections_use_defaults(self):
        path = self._write_config({"database": {"host": "myhost"}})
        cfg = load_config(config_path=path)
        assert cfg.host == "myhost"
        assert cfg.batch_size == 1000  # processing section missing -> default


class TestLoadConfigOverrides:
    """load_config() overrides should take precedence over file values."""

    CONFIG_DATA = {
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

    def _write_config(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(self.CONFIG_DATA, tmp)
        tmp.flush()
        tmp.close()
        return tmp.name

    def test_override_host(self):
        path = self._write_config()
        cfg = load_config(config_path=path, host="override-host")
        assert cfg.host == "override-host"

    def test_override_port(self):
        path = self._write_config()
        cfg = load_config(config_path=path, port=5432)
        assert cfg.port == 5432

    def test_override_database(self):
        path = self._write_config()
        cfg = load_config(config_path=path, database="override_db")
        assert cfg.database == "override_db"

    def test_override_batch_size(self):
        path = self._write_config()
        cfg = load_config(config_path=path, batch_size=9999)
        assert cfg.batch_size == 9999

    def test_non_overridden_file_values_preserved(self):
        path = self._write_config()
        cfg = load_config(config_path=path, host="new-host")
        # Other file values should still come from file
        assert cfg.database == "file_db"
        assert cfg.batch_size == 200

    def test_none_override_does_not_overwrite_file_value(self):
        """Passing None as an override should not replace the file value."""
        path = self._write_config()
        cfg = load_config(config_path=path, host=None)
        assert cfg.host == "file-host"

    def test_overrides_without_file(self):
        cfg = load_config(host="standalone-host", port=9999)
        assert cfg.host == "standalone-host"
        assert cfg.port == 9999
        assert cfg.database == ""  # default unchanged
