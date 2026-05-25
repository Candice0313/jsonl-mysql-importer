"""SQLGenerator: generates MySQL CREATE TABLE statements for the JSONL-to-MySQL import system."""


class SQLGenerator:
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    BATCH_SIZE = 1000

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
