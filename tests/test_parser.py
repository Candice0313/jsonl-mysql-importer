"""Unit tests for JSONLParser."""

import json
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
# Test: multi-line file is read line-by-line (streaming, not all at once)
# ---------------------------------------------------------------------------

def test_parse_file_reads_line_by_line(parser, tmp_path):
    """Verify streaming: results come in correct line-number order across many lines."""
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
