"""Unit tests for SQLGenerator schema generation."""

import pytest
from pathlib import Path
from src.sql_generator import SQLGenerator


@pytest.fixture
def generator():
    return SQLGenerator()


class TestGenerateAliasTableSchema:
    def test_contains_table_name(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "alias_table" in sql

    def test_contains_alias_id_column(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "alias_id INT" in sql

    def test_contains_cui_column(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "cui VARCHAR(50)" in sql

    def test_contains_alias_column(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "alias TEXT" in sql

    def test_contains_index(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "idx_cui" in sql

    def test_engine_innodb(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "ENGINE=InnoDB" in sql

    def test_charset_utf8mb4(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "DEFAULT CHARSET=utf8mb4" in sql

    def test_alias_id_not_null(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "alias_id INT NOT NULL" in sql

    def test_cui_not_null(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "cui VARCHAR(50) NOT NULL" in sql

    def test_alias_not_null(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "alias TEXT NOT NULL" in sql

    def test_contains_primary_key(self, generator):
        sql = generator.generate_alias_table_schema()
        assert "id INT AUTO_INCREMENT PRIMARY KEY" in sql


class TestGenerateEntitiesTableSchema:
    def test_contains_table_name(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "entities_table" in sql

    def test_contains_aliases_json_column(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "aliases JSON" in sql

    def test_contains_types_json_column(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "types JSON" in sql

    def test_contains_charset(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "utf8mb4" in sql

    def test_contains_index(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "idx_cui" in sql

    def test_engine_innodb(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "ENGINE=InnoDB" in sql

    def test_charset_utf8mb4(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "DEFAULT CHARSET=utf8mb4" in sql

    def test_contains_primary_key(self, generator):
        sql = generator.generate_entities_table_schema()
        assert "id INT AUTO_INCREMENT PRIMARY KEY" in sql


class TestGenerateSchemas:
    def test_contains_both_tables(self, generator):
        sql = generator.generate_schemas()
        assert "alias_table" in sql
        assert "entities_table" in sql

    def test_alias_table_comes_first(self, generator):
        sql = generator.generate_schemas()
        alias_pos = sql.index("alias_table")
        entities_pos = sql.index("entities_table")
        assert alias_pos < entities_pos

    def test_both_statements_present(self, generator):
        sql = generator.generate_schemas()
        alias_sql = generator.generate_alias_table_schema()
        entities_sql = generator.generate_entities_table_schema()
        assert alias_sql in sql
        assert entities_sql in sql

    def test_blank_line_separator(self, generator):
        sql = generator.generate_schemas()
        assert "\n\n" in sql


class TestSQLGeneratorConstants:
    def test_max_file_size(self):
        assert SQLGenerator.MAX_FILE_SIZE == 50 * 1024 * 1024

    def test_batch_size(self):
        assert SQLGenerator.BATCH_SIZE == 1000


class TestEscaping:
    def test_escape_string_no_special_chars(self, generator):
        """escape_string with no special chars returns unchanged string."""
        result = generator.escape_string("hello world")
        assert result == "hello world"

    def test_escape_string_single_quote(self, generator):
        """escape_string escapes single quote: "it's" → "it\\'s"."""
        result = generator.escape_string("it's")
        assert result == "it\\'s"

    def test_escape_string_backslash(self, generator):
        """escape_string escapes backslash: "a\\b" → "a\\\\b"."""
        result = generator.escape_string("a\\b")
        assert result == "a\\\\b"

    def test_escape_string_both(self, generator):
        """escape_string escapes both: "it's a\\b" → "it\\'s a\\\\b"."""
        result = generator.escape_string("it's a\\b")
        assert result == "it\\'s a\\\\b"

    def test_escape_string_empty(self, generator):
        """escape_string with empty string returns empty string."""
        result = generator.escape_string("")
        assert result == ""

    def test_to_json_string_simple_list(self, generator):
        """to_json_string with simple list → valid JSON array string."""
        result = generator.to_json_string([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_to_json_string_non_ascii(self, generator):
        """to_json_string preserves non-ASCII characters (ensure_ascii=False)."""
        result = generator.to_json_string(["hello", "世界"])
        assert "世界" in result
        assert isinstance(result, str)

    def test_to_json_string_empty_list(self, generator):
        """to_json_string with empty list → "[]"."""
        result = generator.to_json_string([])
        assert result == "[]"


class TestGenerateInserts:
    def test_empty_records_returns_empty_list(self, generator, tmp_path):
        """Empty records iterator → returns empty list, no files created."""
        result = generator.generate_inserts(iter([]), "alias_table", tmp_path)
        assert result == []
        assert list(tmp_path.iterdir()) == []

    def test_single_alias_record_creates_one_file(self, generator, tmp_path):
        """Single alias record → one file created with correct INSERT statement."""
        record = {"alias_id": 1, "cui": "C001", "alias": "test alias"}
        result = generator.generate_inserts(iter([record]), "alias_table", tmp_path)

        assert len(result) == 1
        assert result[0].name == "alias_table_part001.sql"

        content = result[0].read_text(encoding="utf-8")
        assert "INSERT INTO alias_table (alias_id, cui, alias) VALUES" in content
        assert "(1, 'C001', 'test alias');" in content

    def test_single_entity_record_creates_one_file(self, generator, tmp_path):
        """Single entity record → one file with correct INSERT, JSON fields properly formatted."""
        import json
        record = {
            "cui": "C001",
            "name": "Test Entity",
            "aliases": ["alias1", "alias2"],
            "tax_id": "9606",
            "definition": "A test entity",
            "organism": "Homo sapiens",
            "types": ["Gene", "Protein"],
        }
        result = generator.generate_inserts(iter([record]), "entities_table", tmp_path)

        assert len(result) == 1
        assert result[0].name == "entities_table_part001.sql"

        content = result[0].read_text(encoding="utf-8")
        assert "INSERT INTO entities_table (cui, name, aliases, tax_id, definition, organism, types) VALUES" in content
        assert "'C001'" in content
        assert "'Test Entity'" in content
        # JSON fields should appear as escaped JSON strings
        assert "alias1" in content
        assert "alias2" in content
        assert "Gene" in content

    def test_1001_alias_records_two_batches_in_one_file(self, generator, tmp_path):
        """1001 alias records → one file with 2 INSERT batches (batch of 1000 + batch of 1)."""
        records = [{"alias_id": i, "cui": "C{:04d}".format(i), "alias": "alias{}".format(i)} for i in range(1001)]
        result = generator.generate_inserts(iter(records), "alias_table", tmp_path)

        # All 1001 records are small — should fit in a single file with 2 INSERT blocks
        assert len(result) == 1
        content = result[0].read_text(encoding="utf-8")
        # Two INSERT statements
        assert content.count("INSERT INTO alias_table") == 2

    def test_file_size_limit_creates_second_file(self, generator, tmp_path):
        """When records would exceed 50MB, a second file is created."""
        # Each alias string is large enough that a batch of 1000 exceeds 50MB
        large_alias = "x" * 55000  # ~55KB per record × 1000 = ~55MB per batch
        records = ({"alias_id": i, "cui": "C{:04d}".format(i), "alias": large_alias} for i in range(2000))
        result = generator.generate_inserts(records, "alias_table", tmp_path)

        assert len(result) >= 2

    def test_file_naming_pattern(self, generator, tmp_path):
        """File naming follows pattern: alias_table_part001.sql, alias_table_part002.sql."""
        large_alias = "x" * 55000
        records = ({"alias_id": i, "cui": "C{:04d}".format(i), "alias": large_alias} for i in range(2000))
        result = generator.generate_inserts(records, "alias_table", tmp_path)

        assert result[0].name == "alias_table_part001.sql"
        assert result[1].name == "alias_table_part002.sql"

    def test_null_handling_missing_optional_fields(self, generator, tmp_path):
        """Missing optional fields → NULL in INSERT."""
        record = {"alias_id": 1, "cui": "C001"}  # alias is missing
        result = generator.generate_inserts(iter([record]), "alias_table", tmp_path)

        assert len(result) == 1
        content = result[0].read_text(encoding="utf-8")
        assert "NULL" in content

    def test_null_handling_entity_missing_fields(self, generator, tmp_path):
        """Missing optional entity fields → NULL in INSERT."""
        record = {"cui": "C001", "name": "Test"}  # most fields missing
        result = generator.generate_inserts(iter([record]), "entities_table", tmp_path)

        assert len(result) == 1
        content = result[0].read_text(encoding="utf-8")
        assert "NULL" in content

    def test_output_dir_created_if_not_exists(self, generator, tmp_path):
        """output_dir is created if it doesn't exist."""
        new_dir = tmp_path / "subdir" / "output"
        record = {"alias_id": 1, "cui": "C001", "alias": "a"}
        result = generator.generate_inserts(iter([record]), "alias_table", new_dir)
        assert new_dir.exists()
        assert len(result) == 1

    def test_string_escaping_in_alias(self, generator, tmp_path):
        """Special characters in alias values are properly escaped."""
        record = {"alias_id": 1, "cui": "C001", "alias": "it's a test\\value"}
        result = generator.generate_inserts(iter([record]), "alias_table", tmp_path)

        content = result[0].read_text(encoding="utf-8")
        assert "it\\'s a test\\\\value" in content
