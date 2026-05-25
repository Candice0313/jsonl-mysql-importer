"""JSONL parser module for the JSONL-to-MySQL import system."""

import json
import logging
from pathlib import Path
from typing import Iterator, Tuple

logger = logging.getLogger(__name__)


class JSONLParser:
    """Streaming parser for JSONL (JSON Lines) files."""

    def __init__(self):
        """Initialize the JSONLParser with an empty skipped_lines list."""
        self.skipped_lines: list[tuple[int, str]] = []

    def parse_file(self, file_path: Path) -> Iterator[Tuple[int, dict]]:
        """Yield (line_number, parsed_dict) for each valid JSON line.

        Reads the file line-by-line without loading the entire file into memory.
        Lines that fail to parse as JSON are logged and skipped. Non-dict JSON values
        (arrays, scalars, etc.) are also skipped since they cannot represent table records.
        Skipped lines are tracked in self.skipped_lines with their line numbers and reasons.

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
                except json.JSONDecodeError as e:
                    logger.warning(f"Line {line_number}: invalid JSON - {e}")
                    self.skipped_lines.append((line_number, "invalid JSON"))
                    continue
                # Non-dict JSON values (arrays, scalars) are not valid table records and are skipped
                if isinstance(parsed, dict):
                    yield (line_number, parsed)
                else:
                    self.skipped_lines.append((line_number, "not a JSON object"))

    def reset(self) -> None:
        """Reset the parser state by clearing the skipped_lines list.

        This allows the parser to be reused across multiple files.
        """
        self.skipped_lines = []
