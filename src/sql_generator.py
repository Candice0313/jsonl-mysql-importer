"""SQLGenerator: generates MySQL CREATE TABLE statements for the JSONL-to-MySQL import system."""

import json
from pathlib import Path
from typing import Iterator, List


class SQLGenerator:
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    BATCH_SIZE = 1000

    def escape_string(self, value: str) -> str:
        """Escape backslashes and single quotes for MySQL string literals."""
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def to_json_string(self, value: list) -> str:
        """Convert a Python list to a MySQL-compatible JSON string."""
        return json.dumps(value, ensure_ascii=False)

    def generate_alias_table_schema(self) -> str:
        """Return the CREATE TABLE SQL for alias_table."""
        return (
            "CREATE TABLE IF NOT EXISTS alias_table (\n"
            "    id INT AUTO_INCREMENT PRIMARY KEY,\n"
            "    alias_id INT NOT NULL,\n"
            "    cui VARCHAR(50) NOT NULL,\n"
            "    alias TEXT NOT NULL,\n"
            "    INDEX idx_cui (cui)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        )

    def generate_entities_table_schema(self) -> str:
        """Return the CREATE TABLE SQL for entities_table."""
        return (
            "CREATE TABLE IF NOT EXISTS entities_table (\n"
            "    id INT AUTO_INCREMENT PRIMARY KEY,\n"
            "    cui VARCHAR(50) NOT NULL,\n"
            "    name TEXT NOT NULL,\n"
            "    aliases JSON NOT NULL,\n"
            "    tax_id VARCHAR(50) NOT NULL,\n"
            "    definition TEXT NOT NULL,\n"
            "    organism VARCHAR(255) NOT NULL,\n"
            "    types JSON NOT NULL,\n"
            "    INDEX idx_cui (cui)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        )

    def generate_schemas(self) -> str:
        """Return both CREATE TABLE statements concatenated."""
        return self.generate_alias_table_schema() + "\n\n" + self.generate_entities_table_schema()

    def _format_alias_row(self, record: dict) -> str:
        """Format a single alias_table record as a SQL VALUES row string."""
        alias_id = record.get("alias_id")
        cui = record.get("cui")
        alias = record.get("alias")

        alias_id_sql = str(alias_id) if alias_id is not None else "NULL"
        cui_sql = "'{}'".format(self.escape_string(cui)) if cui is not None else "NULL"
        alias_sql = "'{}'".format(self.escape_string(alias)) if alias is not None else "NULL"

        return "({}, {}, {})".format(alias_id_sql, cui_sql, alias_sql)

    def _format_entity_row(self, record: dict) -> str:
        """Format a single entities_table record as a SQL VALUES row string."""
        def esc(val):
            return "'{}'".format(self.escape_string(val)) if val is not None else "NULL"

        cui = esc(record.get("cui"))
        name = esc(record.get("name"))

        aliases_val = record.get("aliases")
        aliases_sql = "'{}'".format(self.escape_string(self.to_json_string(aliases_val))) if aliases_val is not None else "NULL"

        tax_id = esc(record.get("tax_id"))
        definition = esc(record.get("definition"))
        organism = esc(record.get("organism"))

        types_val = record.get("types")
        types_sql = "'{}'".format(self.escape_string(self.to_json_string(types_val))) if types_val is not None else "NULL"

        return "({}, {}, {}, {}, {}, {}, {})".format(
            cui, name, aliases_sql, tax_id, definition, organism, types_sql
        )

    def generate_inserts(self, records: Iterator[dict], table_name: str, output_dir: Path) -> List[Path]:
        """
        Generate multi-row INSERT statements from records, split into files <= MAX_FILE_SIZE (50MB).

        Args:
            records: iterator of dicts (one per row)
            table_name: "alias_table" or "entities_table"
            output_dir: directory to write .sql files into

        Returns:
            List of Path objects for the generated .sql files, in order.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if table_name == "alias_table":
            columns = "(alias_id, cui, alias)"
            format_row = self._format_alias_row
        else:
            columns = "(cui, name, aliases, tax_id, definition, organism, types)"
            format_row = self._format_entity_row

        header = "INSERT INTO {} {} VALUES\n".format(table_name, columns)

        generated_files: List[Path] = []
        file_index = 0
        current_file_content = ""
        current_file_size = 0

        def flush_batch(batch_rows: list) -> None:
            nonlocal current_file_content, current_file_size, file_index

            if not batch_rows:
                return

            lines = []
            for i, row in enumerate(batch_rows):
                if i < len(batch_rows) - 1:
                    lines.append("  {},".format(row))
                else:
                    lines.append("  {};".format(row))

            batch_text = header + "\n".join(lines) + "\n"
            batch_bytes = len(batch_text.encode("utf-8"))

            # If adding this batch would exceed MAX_FILE_SIZE and we already have content,
            # write out current file and start fresh.
            if current_file_content and (current_file_size + batch_bytes > self.MAX_FILE_SIZE):
                file_index += 1
                file_path = output_dir / "{}_part{:03d}.sql".format(table_name, file_index)
                file_path.write_text(current_file_content, encoding="utf-8")
                generated_files.append(file_path)
                current_file_content = ""
                current_file_size = 0

            current_file_content += batch_text
            current_file_size += batch_bytes

        batch: List[str] = []
        for record in records:
            row_str = format_row(record)
            batch.append(row_str)
            if len(batch) >= self.BATCH_SIZE:
                flush_batch(batch)
                batch = []

        # Flush remaining rows
        if batch:
            flush_batch(batch)

        # Write final file if there's content
        if current_file_content:
            file_index += 1
            file_path = output_dir / "{}_part{:03d}.sql".format(table_name, file_index)
            file_path.write_text(current_file_content, encoding="utf-8")
            generated_files.append(file_path)

        return generated_files
