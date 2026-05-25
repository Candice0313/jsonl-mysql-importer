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

    def validate_alias_record(self, line_num: int, record: dict) -> list[str]:
        """Validate an alias record from alias_table.jsonl.

        Checks for required fields and correct types. Does NOT skip records — returns
        a list of warning strings that were logged.

        Args:
            line_num: The line number of the record (1-indexed).
            record: The parsed record dictionary.

        Returns:
            List of warning strings (empty if valid).
        """
        warnings = []

        # Check alias_id: must be present and be an integer (not float/str)
        if "alias_id" not in record or not isinstance(record.get("alias_id"), int):
            warning = f"line {line_num}: alias_id missing or not an integer"
            warnings.append(warning)
            logger.warning(warning)

        # Check cui: must be present and be a non-empty string
        if not record.get("cui") or not isinstance(record.get("cui"), str):
            warning = f"line {line_num}: cui missing or empty"
            warnings.append(warning)
            logger.warning(warning)

        # Check alias: must be present
        if "alias" not in record:
            warning = f"line {line_num}: alias field missing"
            warnings.append(warning)
            logger.warning(warning)

        return warnings

    def validate_entity_record(self, line_num: int, record: dict) -> list[str]:
        """Validate an entity record from entities.jsonl.

        Checks for required fields and correct types. Does NOT skip records — returns
        a list of warning strings that were logged.

        Args:
            line_num: The line number of the record (1-indexed).
            record: The parsed record dictionary.

        Returns:
            List of warning strings (empty if valid).
        """
        warnings = []

        # Check cui: must be present and be a non-empty string
        if not record.get("cui") or not isinstance(record.get("cui"), str):
            warning = f"line {line_num}: cui missing or empty"
            warnings.append(warning)
            logger.warning(warning)

        # Check aliases: must be present and be a list
        if "aliases" not in record or not isinstance(record.get("aliases"), list):
            warning = f"line {line_num}: aliases missing or not a JSON array"
            warnings.append(warning)
            logger.warning(warning)

        # Check types: must be present and be a list
        if "types" not in record or not isinstance(record.get("types"), list):
            warning = f"line {line_num}: types missing or not a JSON array"
            warnings.append(warning)
            logger.warning(warning)

        return warnings
