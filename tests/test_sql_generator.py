"""Unit tests for SQLGenerator schema generation."""

import pytest
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
