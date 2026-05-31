from pathlib import Path
from src.file_splitter import FileSplitter


def _make_file(path: Path, lines: list[bytes]) -> Path:
    path.write_bytes(b"".join(lines))
    return path


def test_splits_into_correct_number_of_files(tmp_path):
    line = b"A" * 99 + b"\n"
    src = _make_file(tmp_path / "data.tsv", [line] * 3)
    out = tmp_path / "out"

    parts = FileSplitter().split(src, out, chunk_size=150)

    assert len(parts) == 2


def test_every_output_file_ends_with_newline(tmp_path):
    line = b"A" * 99 + b"\n"
    src = _make_file(tmp_path / "data.tsv", [line] * 4)
    out = tmp_path / "out"

    parts = FileSplitter().split(src, out, chunk_size=150)

    for p in parts:
        assert p.read_bytes().endswith(b"\n"), f"{p.name} does not end with newline"


def test_no_line_is_split_across_files(tmp_path):
    line = b"COL1\tCOL2\tCOL3\n"
    src = _make_file(tmp_path / "data.tsv", [line] * 10)
    out = tmp_path / "out"

    parts = FileSplitter().split(src, out, chunk_size=50)

    for p in parts:
        for raw_line in p.read_bytes().splitlines():
            assert raw_line == b"COL1\tCOL2\tCOL3"


def test_all_lines_are_preserved(tmp_path):
    lines = [f"row{i}\n".encode() for i in range(20)]
    src = _make_file(tmp_path / "data.tsv", lines)
    out = tmp_path / "out"

    parts = FileSplitter().split(src, out, chunk_size=50)

    combined = b"".join(p.read_bytes() for p in parts)
    assert combined == b"".join(lines)


def test_output_filenames_are_sequential(tmp_path):
    line = b"x" * 99 + b"\n"
    src = _make_file(tmp_path / "data.tsv", [line] * 5)
    out = tmp_path / "out"

    parts = FileSplitter().split(src, out, chunk_size=150)

    names = [p.name for p in parts]
    assert names == ["data_part001.tsv", "data_part002.tsv", "data_part003.tsv"]


def test_single_chunk_when_file_fits(tmp_path):
    line = b"small\n"
    src = _make_file(tmp_path / "data.tsv", [line] * 3)
    out = tmp_path / "out"

    parts = FileSplitter().split(src, out, chunk_size=500 * 1024 * 1024)

    assert len(parts) == 1
    assert parts[0].read_bytes() == b"small\n" * 3


def test_empty_file_returns_empty_list(tmp_path):
    src = _make_file(tmp_path / "data.tsv", [])
    out = tmp_path / "out"

    parts = FileSplitter().split(src, out, chunk_size=500)

    assert parts == []
