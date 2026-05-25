"""Integration-style tests for src/main.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.main import main, _process_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_alias_jsonl(path: Path, count: int = 2):
    """Write a minimal alias_table JSONL file with `count` records."""
    with path.open("w", encoding="utf-8") as fh:
        for i in range(count):
            fh.write(json.dumps({"alias_id": i, "cui": f"C{i:07d}", "alias": f"alias_{i}"}) + "\n")


def _write_entity_jsonl(path: Path, count: int = 2):
    """Write a minimal entities JSONL file with `count` records."""
    with path.open("w", encoding="utf-8") as fh:
        for i in range(count):
            fh.write(json.dumps({
                "cui": f"C{i:07d}",
                "name": f"name_{i}",
                "aliases": [],
                "tax_id": "9606",
                "definition": "def",
                "organism": "Human",
                "types": ["T001"],
            }) + "\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMainCreatesOutputDir:
    """test_main_creates_output_dir — verify output_dir is created."""

    def test_main_creates_output_dir(self, tmp_path):
        alias_file = tmp_path / "alias_table.jsonl"
        entity_file = tmp_path / "entities.jsonl"
        _write_alias_jsonl(alias_file)
        _write_entity_jsonl(entity_file)

        output_dir = tmp_path / "out" / "nested"
        # Directory does not exist yet
        assert not output_dir.exists()

        main([
            "--alias-file", str(alias_file),
            "--entity-file", str(entity_file),
            "--output-dir", str(output_dir),
        ])

        assert output_dir.exists()
        assert output_dir.is_dir()


class TestMainGeneratesSchemasFile:
    """test_main_generates_schemas_file — verify schemas.sql is created."""

    def test_main_generates_schemas_file(self, tmp_path):
        alias_file = tmp_path / "alias_table.jsonl"
        entity_file = tmp_path / "entities.jsonl"
        _write_alias_jsonl(alias_file)
        _write_entity_jsonl(entity_file)

        output_dir = tmp_path / "output"

        main([
            "--alias-file", str(alias_file),
            "--entity-file", str(entity_file),
            "--output-dir", str(output_dir),
        ])

        schemas_path = output_dir / "schemas.sql"
        assert schemas_path.exists(), "schemas.sql not created"
        content = schemas_path.read_text(encoding="utf-8")
        assert "alias_table" in content
        assert "entities_table" in content


class TestMainGeneratesReport:
    """test_main_generates_report — verify import_report.txt is created."""

    def test_main_generates_report(self, tmp_path):
        alias_file = tmp_path / "alias_table.jsonl"
        entity_file = tmp_path / "entities.jsonl"
        _write_alias_jsonl(alias_file)
        _write_entity_jsonl(entity_file)

        output_dir = tmp_path / "output"

        main([
            "--alias-file", str(alias_file),
            "--entity-file", str(entity_file),
            "--output-dir", str(output_dir),
        ])

        report_path = output_dir / "import_report.txt"
        assert report_path.exists(), "import_report.txt not created"
        content = report_path.read_text(encoding="utf-8")
        assert "JSONL to MySQL Import Report" in content


class TestMainNoExecuteSkipsDB:
    """test_main_no_execute_skips_db — verify DB is NOT touched without --execute."""

    def test_main_no_execute_skips_db(self, tmp_path):
        alias_file = tmp_path / "alias_table.jsonl"
        entity_file = tmp_path / "entities.jsonl"
        _write_alias_jsonl(alias_file)
        _write_entity_jsonl(entity_file)

        output_dir = tmp_path / "output"

        with patch("src.main.DatabaseExecutor") as mock_executor_cls:
            main([
                "--alias-file", str(alias_file),
                "--entity-file", str(entity_file),
                "--output-dir", str(output_dir),
            ])

            # DatabaseExecutor should not be instantiated (no --execute flag)
            mock_executor_cls.assert_not_called()
            # And certainly connect() should not be called
            mock_executor_cls.return_value.connect.assert_not_called()


class TestMainProgressReported:
    """test_main_progress_reported — verify print is called every 10,000 rows."""

    def test_main_progress_reported(self, tmp_path):
        alias_file = tmp_path / "alias_table.jsonl"
        entity_file = tmp_path / "entities.jsonl"
        # Write 10,001 alias records to trigger the progress print at 10,000
        _write_alias_jsonl(alias_file, count=10_001)
        _write_entity_jsonl(entity_file)

        output_dir = tmp_path / "output"

        with patch("builtins.print") as mock_print:
            main([
                "--alias-file", str(alias_file),
                "--entity-file", str(entity_file),
                "--output-dir", str(output_dir),
            ])

        # Collect all print call args as strings
        printed = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        progress_msgs = [m for m in printed if "alias_table: processed" in m and "rows" in m]
        assert len(progress_msgs) >= 1, (
            f"Expected at least one progress print for alias_table but got: {printed}"
        )
        assert "10,000" in progress_msgs[0]
