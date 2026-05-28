# Design: gene_info.gz TSV Converter

## Overview

Add support for importing NCBI `gene_info.gz` (tab-separated, gzipped) directly into `entities_table`, bypassing the intermediate JSONL format. A new `GeneInfoParser` feeds into the existing SQL generation and database execution pipeline unchanged.

---

## Background

`gene_info.gz` is the raw NCBI Gene source file (~68.8M rows). Its columns map directly to `entities_table`:

| gene_info column | entities_table column | Notes |
|---|---|---|
| `GeneID` | `cui` | string |
| `Symbol` | `name` | string |
| `Synonyms` | `aliases` | pipe-separated → JSON array |
| `tax_id` | `tax_id` | string |
| `description` | `definition` | string |
| `type_of_gene` | `types` | single value → JSON array |
| *(missing)* | `organism` | left empty for now |

NCBI uses `-` to indicate no data — these are converted to empty string `""`.

---

## Components

### 1. `src/gene_info_parser.py` — GeneInfoParser

Reads a gzipped TSV file line-by-line using Python's `gzip` module. Yields `(line_number, dict)` tuples with the same interface as `JSONLParser.parse_file()` so the rest of the pipeline works unchanged.

```python
class GeneInfoParser:
    def __init__(self):
        self.skipped_lines: list[tuple[int, str]] = []

    def parse_file(self, file_path: Path) -> Iterator[Tuple[int, dict]]:
        """Yield (line_number, dict) for each valid data row in gene_info.gz."""

    def reset(self):
        """Clear skipped_lines for reuse across files."""
```

**Column mapping logic:**
- Skip header row (line 1, starts with `#`)
- For each row, split on `\t` — expect exactly 16 columns
- Convert all `-` values to `""`
- `Synonyms`: split on `|` → list; if `-` → `[]`
- `type_of_gene`: wrap in list → `["rRNA"]`; if `-` → `[]`
- `organism`: always `""`

**Error handling:**
- Wrong column count → log `"unexpected column count: got N, expected 16"`, append to `skipped_lines`, skip row
- Missing `GeneID` or `Symbol` (empty after `-` conversion) → log warning, still yield the record
- Gzip read error → let exception propagate with clear message

---

### 2. CLI changes — `src/main.py`

Add `--gene-info-file` flag to `parse_args()` and `Config`.

**Mutual exclusivity:** `--entity-file` and `--gene-info-file` cannot both be set — exit with error if both are provided.

**Workflow when `--gene-info-file` is set:**
- Use `GeneInfoParser` instead of `JSONLParser` for `entities_table` processing
- All other steps unchanged: SQL generation, file splitting, DB execution, report

**CLI usage:**
```bash
# gene_info.gz as entity source
python -m src.main \
  --alias-file alias_table.jsonl \
  --gene-info-file data/gene_info.gz \
  --output-dir ./output

# With database execution
python -m src.main \
  --alias-file alias_table.jsonl \
  --gene-info-file data/gene_info.gz \
  --output-dir ./output \
  --host localhost --port 3306 \
  --database mydb --username root --password secret \
  --execute
```

---

## Data Flow

```
gene_info.gz
     │
     ▼
GeneInfoParser.parse_file()    yields (line_num, dict)
     │
     ▼
SQLGenerator.generate_inserts("entities_table", records, output_dir)
     │
     ▼
entities_table_part001.sql, entities_table_part002.sql, ...
     │
     ▼
DatabaseExecutor.execute_script()   (if --execute)
```

---

## Error Handling

| Error | Action |
|---|---|
| Wrong column count | Log line number + reason, skip row, continue |
| Empty GeneID or Symbol | Log warning, yield record anyway |
| Gzip read error | Raise exception, stop processing |
| Both `--entity-file` and `--gene-info-file` set | Print error, exit(1) |
| Neither `--entity-file` nor `--gene-info-file` set | Skip entities_table processing — only alias_table is imported |

---

## Testing (`tests/test_gene_info_parser.py`)

All tests use `tmp_path` with small in-memory gzipped TSV files.

| Test | Verifies |
|---|---|
| Valid row | All 6 fields mapped correctly |
| `-` values | Converted to `""` |
| Multi-synonym | `"cob\|cytochrome b"` → `["cob", "cytochrome b"]` |
| Single synonym | `"rrnL2a"` → `["rrnL2a"]` |
| No synonyms | `"-"` → `[]` |
| type_of_gene | `"rRNA"` → `["rRNA"]` |
| Header skipped | Line 1 not yielded |
| Returns generator | `isinstance(result, types.GeneratorType)` |
| Wrong column count | Skipped, added to `skipped_lines` |
| Integration | Output feeds into `SQLGenerator.generate_inserts` without error |

---

## Out of Scope

- `organism` name lookup from taxonomy files (future work)
- Filtering by `tax_id` or `type_of_gene`
- Incremental/resume support for interrupted large imports
