"""Unit tests for JSONLParser."""

import json
import types
from pathlib import Path

import pytest

from src.parser import JSONLParser


@pytest.fixture
def parser():
    return JSONLParser()


def write_jsonl(path: Path, lines: list) -> Path:
    """Helper: write a list of strings (or dicts) to a JSONL file."""
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            if isinstance(line, dict):
                fh.write(json.dumps(line) + "\n")
            else:
                fh.write(line + "\n")
    return path


# ---------------------------------------------------------------------------
# Test: valid JSONL file yields correct (line_number, dict) tuples
# ---------------------------------------------------------------------------

def test_valid_jsonl_yields_correct_tuples(parser, tmp_path):
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]
    jsonl_file = write_jsonl(tmp_path / "data.jsonl", records)

    results = list(parser.parse_file(jsonl_file))

    assert len(results) == 3
    assert results[0] == (1, {"id": 1, "name": "Alice"})
    assert results[1] == (2, {"id": 2, "name": "Bob"})
    assert results[2] == (3, {"id": 3, "name": "Charlie"})


# ---------------------------------------------------------------------------
# Test: empty file yields nothing
# ---------------------------------------------------------------------------

def test_empty_file_yields_nothing(parser, tmp_path):
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("", encoding="utf-8")

    results = list(parser.parse_file(empty_file))

    assert results == []


# ---------------------------------------------------------------------------
# Test: file with one valid line yields that one record
# ---------------------------------------------------------------------------

def test_single_line_file_yields_one_record(parser, tmp_path):
    record = {"key": "value", "number": 42}
    jsonl_file = write_jsonl(tmp_path / "single.jsonl", [record])

    results = list(parser.parse_file(jsonl_file))

    assert len(results) == 1
    assert results[0] == (1, record)


# ---------------------------------------------------------------------------
# Test: parse_file returns a generator, not a list
# ---------------------------------------------------------------------------

def test_parse_file_returns_generator(parser, tmp_path):
    """Verify that parse_file returns a generator for lazy evaluation."""
    f = tmp_path / "test.jsonl"
    f.write_text('{"a": 1}\n', encoding="utf-8")
    result = parser.parse_file(f)
    assert isinstance(result, types.GeneratorType), "parse_file must return a generator, not a list"


# ---------------------------------------------------------------------------
# Test: multi-line file yields records in correct line-number order
# ---------------------------------------------------------------------------

def test_parse_file_yields_in_order(parser, tmp_path):
    """Verify results come in correct line-number order across many lines."""
    num_records = 100
    records = [{"index": i} for i in range(num_records)]
    jsonl_file = write_jsonl(tmp_path / "multi.jsonl", records)

    results = list(parser.parse_file(jsonl_file))

    assert len(results) == num_records
    for expected_line, (line_number, parsed) in enumerate(results, start=1):
        assert line_number == expected_line
        assert parsed == {"index": expected_line - 1}


# ---------------------------------------------------------------------------
# Test: invalid JSON lines are silently skipped
# ---------------------------------------------------------------------------

def test_invalid_lines_are_skipped(parser, tmp_path):
    lines = [
        '{"id": 1, "name": "Alice"}',
        "this is not json",
        '{"id": 3, "name": "Charlie"}',
    ]
    jsonl_file = tmp_path / "mixed.jsonl"
    jsonl_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    results = list(parser.parse_file(jsonl_file))

    assert len(results) == 2
    assert results[0] == (1, {"id": 1, "name": "Alice"})
    assert results[1] == (3, {"id": 3, "name": "Charlie"})


# ---------------------------------------------------------------------------
# Test: blank lines in the file are skipped
# ---------------------------------------------------------------------------

def test_blank_lines_are_skipped(parser, tmp_path):
    jsonl_file = tmp_path / "blanks.jsonl"
    jsonl_file.write_text(
        '{"a": 1}\n\n{"b": 2}\n\n', encoding="utf-8"
    )

    results = list(parser.parse_file(jsonl_file))

    assert len(results) == 2
    assert results[0] == (1, {"a": 1})
    assert results[1] == (3, {"b": 2})


# ---------------------------------------------------------------------------
# Test: non-dict JSON lines (arrays, strings, numbers) are skipped
# ---------------------------------------------------------------------------

def test_non_dict_json_lines_are_skipped(parser, tmp_path):
    """Verify that arrays, strings, and numbers are skipped (only dicts are valid records)."""
    f = tmp_path / "test.jsonl"
    f.write_text('[1,2,3]\n"hello"\n42\n{"key": "val"}\n', encoding="utf-8")
    results = list(parser.parse_file(f))
    assert len(results) == 1
    assert results[0] == (4, {"key": "val"})


# ---------------------------------------------------------------------------
# Test: invalid JSON lines are added to skipped_lines with reason "invalid JSON"
# ---------------------------------------------------------------------------

def test_invalid_json_lines_tracked_in_skipped_lines(parser, tmp_path):
    """Verify that invalid JSON lines are tracked in skipped_lines with correct reason."""
    lines = [
        '{"id": 1, "name": "Alice"}',
        "this is not json",
        '{"id": 3, "name": "Charlie"}',
        "{invalid json]",
    ]
    jsonl_file = tmp_path / "mixed.jsonl"
    jsonl_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    results = list(parser.parse_file(jsonl_file))

    # Should have 2 valid records
    assert len(results) == 2
    # Should have 2 skipped lines with "invalid JSON" reason
    assert len(parser.skipped_lines) == 2
    assert parser.skipped_lines[0] == (2, "invalid JSON")
    assert parser.skipped_lines[1] == (4, "invalid JSON")


# ---------------------------------------------------------------------------
# Test: non-dict JSON lines are added to skipped_lines with reason "not a JSON object"
# ---------------------------------------------------------------------------

def test_non_dict_json_lines_tracked_in_skipped_lines(parser, tmp_path):
    """Verify that non-dict JSON lines are tracked in skipped_lines with correct reason."""
    f = tmp_path / "test.jsonl"
    f.write_text('[1,2,3]\n"hello"\n42\n{"key": "val"}\ntrue\n', encoding="utf-8")

    results = list(parser.parse_file(f))

    # Should have 1 valid record (the dict)
    assert len(results) == 1
    assert results[0] == (4, {"key": "val"})
    # Should have 4 skipped lines with "not a JSON object" reason
    assert len(parser.skipped_lines) == 4
    assert parser.skipped_lines[0] == (1, "not a JSON object")
    assert parser.skipped_lines[1] == (2, "not a JSON object")
    assert parser.skipped_lines[2] == (3, "not a JSON object")
    assert parser.skipped_lines[3] == (5, "not a JSON object")


# ---------------------------------------------------------------------------
# Test: valid lines are NOT added to skipped_lines
# ---------------------------------------------------------------------------

def test_valid_lines_not_added_to_skipped_lines(parser, tmp_path):
    """Verify that valid JSON dict lines are not added to skipped_lines."""
    records = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]
    jsonl_file = write_jsonl(tmp_path / "data.jsonl", records)

    results = list(parser.parse_file(jsonl_file))

    # Should have 3 valid records
    assert len(results) == 3
    # Should have no skipped lines
    assert len(parser.skipped_lines) == 0


# ---------------------------------------------------------------------------
# Test: reset() clears skipped_lines
# ---------------------------------------------------------------------------

def test_reset_clears_skipped_lines(parser, tmp_path):
    """Verify that reset() clears the skipped_lines list."""
    # Parse a file with invalid lines
    lines = [
        '{"id": 1}',
        "invalid",
        "[1,2,3]",
    ]
    jsonl_file = tmp_path / "mixed.jsonl"
    jsonl_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    list(parser.parse_file(jsonl_file))
    assert len(parser.skipped_lines) == 2

    # Reset and verify skipped_lines is empty
    parser.reset()
    assert len(parser.skipped_lines) == 0
    assert parser.skipped_lines == []
