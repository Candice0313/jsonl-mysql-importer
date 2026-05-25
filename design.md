# Design Document: JSONL to MySQL Import System

## Overview

A Python script to import large JSONL files into MySQL database tables. The system:
- Parses JSONL files line-by-line (memory efficient)
- Generates SQL scripts with 50MB file splitting
- Executes directly against MySQL database
- Produces an import report

### Technology
- **Language**: Python 3.8+
- **Database Driver**: mysql-connector-python

---

## Architecture

```
┌─────────────────┐
│   main.py       │  CLI entry point
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ JSONLParser     │────▶│ SQLGenerator    │────▶│ DatabaseExecutor│
│ (streaming)     │     │ (file split)    │     │ (MySQL)         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │ ReportGenerator │
                                              └─────────────────┘
```

---

## Components and Interfaces

### 1. JSONLParser
Stream-based JSONL file parser with validation.

```python
class JSONLParser:
    def parse_file(self, file_path: Path) -> Iterator[Tuple[int, dict]]:
        """Yield (line_number, parsed_dict) for each valid line."""
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    yield (line_num, data)
                except json.JSONDecodeError:
                    log_error(line_num, line)
```

### 2. SQLGenerator
Generates SQL schemas and INSERT statements with automatic file splitting.

```python
class SQLGenerator:
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    BATCH_SIZE = 1000
    
    def generate_inserts(self, records: Iterator, table_name: str, output_dir: Path) -> List[Path]:
        """Generate multi-row INSERT statements, split files at 50MB."""
        
    def escape_string(self, value: str) -> str:
        """Escape single quotes and special characters."""
        return value.replace("\\", "\\\\").replace("'", "\\'")
        
    def to_json_string(self, value: list) -> str:
        """Convert Python list to MySQL JSON string."""
        return json.dumps(value, ensure_ascii=False)
```

### 3. DatabaseExecutor
Manages MySQL connection and executes SQL scripts.

```python
class DatabaseExecutor:
    def __init__(self, host: str, port: int, database: str, username: str, password: str):
        self.config = {...}
        
    def connect(self) -> bool:
        """Connect with retry logic (3 attempts, 5s delay)."""
        
    def execute_schema(self, schema_sql: str):
        """Execute CREATE TABLE statements."""
        
    def execute_script(self, script_path: Path):
        """Execute SQL script file, commit after completion."""
```

### 4. ReportGenerator
Generates import summary report.

```python
class ReportGenerator:
    def generate(self, stats: dict) -> Path:
        """Create import_report.txt with:
        - Row counts per table
        - File counts and sizes
        - Skipped lines
        - Duration
        """
```

---

## Data Models

### Input JSONL Formats

**Alias Record:**
```json
{
  "alias_id": 11,
  "cui": "801486",
  "alias": "rrnL3b"
}
```

**Entity Record:**
```json
{
  "cui": "2828139",
  "name": "NEWENTRY",
  "aliases": ["NEWENTRY"],
  "tax_id": "1773",
  "definition": "...",
  "organism": "Mycobacterium tuberculosis",
  "types": ["other"]
}
```

### MySQL Table Schemas

### alias_table
```sql
CREATE TABLE IF NOT EXISTS alias_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alias_id INT NOT NULL,
    cui VARCHAR(50) NOT NULL,
    alias TEXT NOT NULL,
    INDEX idx_cui (cui)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### entities_table
```sql
CREATE TABLE IF NOT EXISTS entities_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cui VARCHAR(50) NOT NULL,
    name TEXT NOT NULL,
    aliases JSON NOT NULL,
    tax_id VARCHAR(50) NOT NULL,
    definition TEXT NOT NULL,
    organism VARCHAR(255) NOT NULL,
    types JSON NOT NULL,
    INDEX idx_cui (cui)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Data Flow

### Input Format

**alias_table.jsonl:**
```json
{"alias_id": 11, "cui": "801486", "alias": "rrnL3b"}
{"alias_id": 12, "cui": "801487", "alias": "rrnL3a"}
```

**entities.jsonl:**
```json
{"cui": "2828139", "name": "NEWENTRY", "aliases": ["NEWENTRY"], "tax_id": "1773", "definition": "...", "organism": "...", "types": ["other"]}
```

### Output Structure

```
output/
├── schemas.sql                 # CREATE TABLE statements
├── alias_table_part001.sql     # INSERT statements (≤50MB)
├── alias_table_part002.sql
├── entities_table_part001.sql
├── entities_table_part002.sql
├── import_report.txt           # Summary report
└── import_errors.log           # Error log
```

---

## CLI Usage

```bash
# Generate SQL scripts only
python main.py --config import_config.json

# Generate and execute against database
python main.py --config import_config.json --execute

# Override with CLI args
python main.py \
    --alias-file alias_table.jsonl \
    --entity-file entities.jsonl \
    --host localhost --port 3306 \
    --database entrez_gene \
    --username root --password secret \
    --output-dir ./output \
    --execute
```

---

## Configuration File

**import_config.json:**
```json
{
  "database": {
    "host": "localhost",
    "port": 3306,
    "database": "entrez_gene",
    "username": "root",
    "password": "secret"
  },
  "files": {
    "alias_file": "alias_table.jsonl",
    "entity_file": "entities.jsonl",
    "output_dir": "./output"
  },
  "processing": {
    "batch_size": 1000,
    "max_file_size_mb": 50
  }
}
```

---

## Correctness Properties

### Property 1: JSON Round-Trip
For any valid JSON object, parsing → serializing → parsing SHALL produce an equivalent object.

**Validates: Requirements 1.3, 1.4**

### Property 2: SQL File Size Limit
All generated SQL files SHALL be ≤ 50MB.

**Validates: Requirements 3.1**

### Property 3: SQL String Escaping
Special characters (quotes, backslashes) SHALL be properly escaped in SQL statements.

**Validates: Requirements 3.3, 3.4**

### Property 4: Report Accuracy
Reported counts (rows, files, sizes) SHALL match actual results.

**Validates: Requirements 5.2, 5.3, 5.4, 5.5**

---

## Testing Strategy

- **Unit tests**: Parser, SQL generator, string escaping
- **Integration tests**: Database connection, script execution
- **Performance tests**: Memory efficiency, file processing speed

---

## Error Handling

| Error Type | Action |
|------------|--------|
| Invalid JSON line | Log line number, skip, continue |
| Missing required field | Log warning, skip record, continue |
| Connection failure | Retry 3 times with 5s delay |
| SQL execution error | Log error, continue next statement |
| Database not exists | Offer to create or abort |

---

## File Structure

```
src/
├── main.py              # CLI entry point
├── parser.py            # JSONL parsing
├── sql_generator.py     # SQL generation
├── database_executor.py # MySQL execution
├── report_generator.py  # Report generation
└── config.py            # Configuration handling
```
