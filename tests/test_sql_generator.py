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
