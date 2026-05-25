"""Entry point for the JSONL-to-MySQL import system."""

import argparse

from src.config import load_config


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


def main(argv=None):
    args = parse_args(argv)

    config = load_config(
        config_path=args.config,
        alias_file=args.alias_file,
        entity_file=args.entity_file,
        host=args.host,
        port=args.port,
        database=args.database,
        username=args.username,
        password=args.password,
        output_dir=args.output_dir,
        execute=args.execute,
    )

    print("Config loaded")
    return config


if __name__ == "__main__":
    main()
