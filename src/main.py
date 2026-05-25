"""Entry point for the JSONL-to-MySQL import system."""

import argparse
from pathlib import Path

from src.config import load_config
from src.parser import JSONLParser
from src.sql_generator import SQLGenerator
from src.database_executor import DatabaseExecutor
from src.report_generator import ReportGenerator


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Import JSONL files into a MySQL database."
    )
    parser.add_argument("--config", help="Path to import_config.json")
    parser.add_argument("--alias-file", dest="alias_file", help="Path to alias JSONL file")
    parser.add_argument("--entity-file", dest="entity_file", help="Path to entity JSONL file")
    parser.add_argument("--host", help="MySQL host")
    parser.add_argument("--port", type=int, help="MySQL port")
    parser.add_argument("--database", help="MySQL database name")
    parser.add_argument("--username", help="MySQL username")
    parser.add_argument("--password", help="MySQL password")
    parser.add_argument("--output-dir", dest="output_dir", help="Output directory for generated SQL")
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Execute SQL against the database (default: dry-run only)",
    )
    return parser.parse_args(argv)


def _process_file(parser, file_path, table_name, report, config):
    """Stream records from a JSONL file, validate, track progress and skips."""
    records = []
    row_count = 0
    parser.reset()
    for line_num, record in parser.parse_file(Path(file_path)):
        # Validate
        if table_name == "alias_table":
            parser.validate_alias_record(line_num, record)
        else:
            parser.validate_entity_record(line_num, record)
        records.append(record)
        row_count += 1
        if row_count % 10_000 == 0:
            print(f"  {table_name}: processed {row_count:,} rows...")
    report.record_rows(table_name, row_count)
    report.record_skipped_lines(table_name, parser.skipped_lines)
    return records


def main(argv=None):
    args = parse_args(argv)
    config = load_config(
        config_path=args.config,
        host=args.host, port=args.port, database=args.database,
        username=args.username, password=args.password,
        alias_file=args.alias_file, entity_file=args.entity_file,
        output_dir=args.output_dir, execute=args.execute,
    )

    # Setup
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = ReportGenerator()
    generator = SQLGenerator()
    parser = JSONLParser()
    report.start()

    # Process alias_table.jsonl
    print(f"Processing {config.alias_file}...")
    report.add_table("alias_table")
    alias_records = _process_file(parser, config.alias_file, "alias_table", report, config)
    alias_scripts = generator.generate_inserts(iter(alias_records), "alias_table", output_dir)
    report.record_scripts("alias_table", alias_scripts)

    # Process entities.jsonl
    print(f"Processing {config.entity_file}...")
    report.add_table("entities_table")
    entity_records = _process_file(parser, config.entity_file, "entities_table", report, config)
    entity_scripts = generator.generate_inserts(iter(entity_records), "entities_table", output_dir)
    report.record_scripts("entities_table", entity_scripts)

    # Write schemas.sql
    schemas_path = output_dir / "schemas.sql"
    schemas_path.write_text(generator.generate_schemas(), encoding="utf-8")
    print(f"Schemas written to {schemas_path}")

    # Execute against DB if requested
    if config.execute:
        executor = DatabaseExecutor(
            config.host, config.port, config.database,
            config.username, config.password
        )
        if executor.connect():
            executor.execute_schema(generator.generate_alias_table_schema(), "alias_table")
            executor.execute_schema(generator.generate_entities_table_schema(), "entities_table")
            for script in sorted(alias_scripts + entity_scripts):
                print(f"Executing {script}...")
                executor.execute_script(script)
            executor.close()

    # Generate report
    report.finish()
    report_path = report.generate(output_dir)
    print(f"Import report written to {report_path}")


if __name__ == "__main__":
    main()
