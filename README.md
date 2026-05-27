# JSONL to MySQL Importer

A Python tool that streams large JSONL files into MySQL database tables. Handles files of any size by reading line-by-line and splitting SQL output into 50MB chunks.

## Features

- Streams JSONL files without loading them into memory
- Generates multi-row INSERT scripts split at 50MB
- Validates records and logs warnings for bad data
- Optionally executes directly against a MySQL database
- Produces an import report with row counts, file sizes, and skipped lines

## Tables

The tool imports two table types:

**`alias_table`** — entity alias mappings
```json
{"alias_id": 310, "cui": "5715051", "alias": "uncharacterized protein"}
```

**`entities_table`** — full entity records
```json
{"cui": "801477", "name": "rrnL2a", "aliases": ["rrnL2a"], "tax_id": "3055", "definition": "L2a ribosomal RNA", "organism": "Chlamydomonas reinhardtii", "types": ["rRNA"]}
```

## Installation

```bash
pip install mysql-connector-python
```

## Usage

### Generate SQL scripts only

```bash
python -m src.main \
  --alias-file alias_table.jsonl \
  --entity-file entities.jsonl \
  --output-dir ./output
```

### Generate and execute against a database

```bash
python -m src.main \
  --alias-file alias_table.jsonl \
  --entity-file entities.jsonl \
  --output-dir ./output \
  --host localhost --port 3306 \
  --database mydb \
  --username root --password secret \
  --execute
```

### Using a config file

```bash
python -m src.main --config import_config.json --execute
```

**`import_config.json`:**
```json
{
  "database": {
    "host": "localhost",
    "port": 3306,
    "database": "mydb",
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

## Output

```
output/
├── schemas.sql                  # CREATE TABLE statements
├── alias_table_part001.sql      # INSERT statements (≤50MB each)
├── alias_table_part002.sql
├── entities_table_part001.sql
├── import_report.txt            # Summary report
└── import_errors.log            # Error log (if any)
```

## Running Tests

```bash
python -m pytest tests/ -v
```

166 tests across all components.
