"""JSONL parser module for the JSONL-to-MySQL import system."""

import json
from pathlib import Path
from typing import Iterator, Tuple


class JSONLParser:
    """Streaming parser for JSONL (JSON Lines) files."""

    def parse_file(self, file_path: Path) -> Iterator[Tuple[int, dict]]:
        """Yield (line_number, parsed_dict) for each valid JSON line.

        Reads the file line-by-line without loading the entire file into memory.
        Lines that fail to parse as JSON are silently skipped.

        Args:
            file_path: Path to the JSONL file to parse.

        Yields:
            Tuples of (line_number, parsed_dict) where line_number starts at 1.
        """
        with open(file_path, encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    yield (line_number, parsed)
