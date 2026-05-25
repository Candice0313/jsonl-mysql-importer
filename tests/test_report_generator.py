"""Unit tests for ReportGenerator."""

from pathlib import Path
from datetime import datetime, timedelta
import pytest

from src.report_generator import ReportGenerator, TableStats


@pytest.fixture
def report_generator():
    return ReportGenerator()


class TestReportGeneratorBasics:
    """Test basic functionality of ReportGenerator."""

    def test_generate_creates_file(self, report_generator, tmp_path):
        """generate() creates the output file."""
        report_generator.start()
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        assert report_path.exists()
        assert report_path.name == "import_report.txt"

    def test_generate_returns_path(self, report_generator, tmp_path):
        """generate() returns a Path object."""
        report_generator.start()
        report_generator.finish()
        result = report_generator.generate(tmp_path)

        assert isinstance(result, Path)

    def test_generate_includes_header(self, report_generator, tmp_path):
        """Report contains the expected header."""
        report_generator.start()
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "JSONL to MySQL Import Report" in content
        assert "=============================" in content


class TestTableRegistration:
    """Test table registration and tracking."""

    def test_add_table_registers_table(self, report_generator):
        """add_table() registers a table for tracking."""
        report_generator.add_table("test_table")
        assert "test_table" in report_generator.tables
        assert report_generator.tables["test_table"].name == "test_table"

    def test_generate_includes_table_name(self, report_generator, tmp_path):
        """Report contains registered table name."""
        report_generator.start()
        report_generator.add_table("alias_table")
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Table: alias_table" in content


class TestRowCounting:
    """Test row count tracking."""

    def test_record_rows_stores_count(self, report_generator):
        """record_rows() stores the row count."""
        report_generator.add_table("test_table")
        report_generator.record_rows("test_table", 1000)

        assert report_generator.tables["test_table"].row_count == 1000

    def test_generate_includes_row_count(self, report_generator, tmp_path):
        """Report shows correct row count."""
        report_generator.start()
        report_generator.add_table("alias_table")
        report_generator.record_rows("alias_table", 1234567)
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Total rows:        1234567" in content


class TestScriptTracking:
    """Test script file tracking."""

    def test_record_scripts_stores_paths(self, report_generator, tmp_path):
        """record_scripts() stores script paths and updates file_count."""
        # Create some dummy files
        script1 = tmp_path / "alias_table_part001.sql"
        script2 = tmp_path / "alias_table_part002.sql"
        script1.write_text("SELECT 1;", encoding="utf-8")
        script2.write_text("SELECT 2;", encoding="utf-8")

        report_generator.add_table("alias_table")
        report_generator.record_scripts("alias_table", [script1, script2])

        assert report_generator.tables["alias_table"].file_count == 2
        assert report_generator.tables["alias_table"].script_paths == [script1, script2]

    def test_record_scripts_calculates_total_size(self, report_generator, tmp_path):
        """record_scripts() updates total_size_bytes."""
        # Create dummy files with known sizes
        script1 = tmp_path / "alias_table_part001.sql"
        script2 = tmp_path / "alias_table_part002.sql"
        script1.write_text("x" * 1024, encoding="utf-8")  # 1024 bytes
        script2.write_text("y" * 2048, encoding="utf-8")  # 2048 bytes

        report_generator.add_table("alias_table")
        report_generator.record_scripts("alias_table", [script1, script2])

        # Should be 1024 + 2048 = 3072 bytes
        assert report_generator.tables["alias_table"].total_size_bytes == 3072

    def test_generate_includes_file_count(self, report_generator, tmp_path):
        """Report shows correct file count."""
        # Create dummy script files
        script1 = tmp_path / "alias_table_part001.sql"
        script2 = tmp_path / "alias_table_part002.sql"
        script3 = tmp_path / "alias_table_part003.sql"
        script1.write_text("", encoding="utf-8")
        script2.write_text("", encoding="utf-8")
        script3.write_text("", encoding="utf-8")

        report_generator.start()
        report_generator.add_table("alias_table")
        report_generator.record_scripts("alias_table", [script1, script2, script3])
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "SQL files:         3" in content

    def test_generate_includes_total_size(self, report_generator, tmp_path):
        """Report shows total size in MB."""
        # Create a file with 1MB of data
        script1 = tmp_path / "alias_table_part001.sql"
        script1.write_text("x" * (1024 * 1024), encoding="utf-8")  # 1MB

        report_generator.start()
        report_generator.add_table("alias_table")
        report_generator.record_scripts("alias_table", [script1])
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        # Should show 1.00 MB
        assert "Total SQL size:    1.00 MB" in content

    def test_generate_includes_script_paths(self, report_generator, tmp_path):
        """Report lists script file paths."""
        script1 = tmp_path / "alias_table_part001.sql"
        script2 = tmp_path / "alias_table_part002.sql"
        script1.write_text("", encoding="utf-8")
        script2.write_text("", encoding="utf-8")

        report_generator.start()
        report_generator.add_table("alias_table")
        report_generator.record_scripts("alias_table", [script1, script2])
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert str(script1) in content
        assert str(script2) in content
        assert "Script files:" in content


class TestTimingTracking:
    """Test timing information tracking."""

    def test_start_records_time(self, report_generator):
        """start() records the start time."""
        before = datetime.now()
        report_generator.start()
        after = datetime.now()

        assert report_generator.start_time is not None
        assert before <= report_generator.start_time <= after

    def test_finish_records_time(self, report_generator):
        """finish() records the end time."""
        before = datetime.now()
        report_generator.finish()
        after = datetime.now()

        assert report_generator.end_time is not None
        assert before <= report_generator.end_time <= after

    def test_generate_includes_start_time(self, report_generator, tmp_path):
        """Report contains start time."""
        start_dt = datetime(2024, 1, 15, 10, 30, 0)
        report_generator.start_time = start_dt
        report_generator.end_time = start_dt + timedelta(seconds=1)
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Start time:  2024-01-15 10:30:00" in content

    def test_generate_includes_end_time(self, report_generator, tmp_path):
        """Report contains end time."""
        start_dt = datetime(2024, 1, 15, 10, 30, 0)
        end_dt = datetime(2024, 1, 15, 10, 35, 42)
        report_generator.start_time = start_dt
        report_generator.end_time = end_dt
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "End time:    2024-01-15 10:35:42" in content

    def test_generate_includes_duration(self, report_generator, tmp_path):
        """Report contains "Duration:" line with correct calculation."""
        start_dt = datetime(2024, 1, 15, 10, 30, 0)
        end_dt = datetime(2024, 1, 15, 10, 35, 42)  # 342 seconds
        report_generator.start_time = start_dt
        report_generator.end_time = end_dt
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Duration:" in content
        assert "342.00 seconds" in content


class TestSkippedLines:
    """Test skipped line tracking."""

    def test_record_skipped_lines_stores_lines(self, report_generator):
        """record_skipped_lines() stores skipped line info."""
        report_generator.add_table("alias_table")
        skipped = [(45, "invalid JSON"), (102, "not a JSON object")]
        report_generator.record_skipped_lines("alias_table", skipped)

        assert report_generator.tables["alias_table"].skipped_lines == skipped

    def test_generate_includes_skipped_lines(self, report_generator, tmp_path):
        """Report lists skipped lines with line numbers and reasons."""
        report_generator.start()
        report_generator.add_table("alias_table")
        skipped = [(45, "invalid JSON"), (102, "not a JSON object")]
        report_generator.record_skipped_lines("alias_table", skipped)
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Skipped lines:     2" in content
        assert "Line 45: invalid JSON" in content
        assert "Line 102: not a JSON object" in content

    def test_generate_zero_skipped_lines(self, report_generator, tmp_path):
        """'Skipped lines: 0' when no skips."""
        report_generator.start()
        report_generator.add_table("alias_table")
        report_generator.record_skipped_lines("alias_table", [])
        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Skipped lines:     0" in content


class TestMultipleTableReport:
    """Test report generation with multiple tables."""

    def test_generate_with_multiple_tables(self, report_generator, tmp_path):
        """Report includes all registered tables."""
        # Create dummy script files
        alias_script = tmp_path / "alias_table_part001.sql"
        entities_script = tmp_path / "entities_table_part001.sql"
        alias_script.write_text("", encoding="utf-8")
        entities_script.write_text("", encoding="utf-8")

        report_generator.start()

        # Add and populate first table
        report_generator.add_table("alias_table")
        report_generator.record_rows("alias_table", 1234567)
        report_generator.record_scripts("alias_table", [alias_script])
        report_generator.record_skipped_lines("alias_table", [(45, "invalid JSON"), (102, "not a JSON object")])

        # Add and populate second table
        report_generator.add_table("entities_table")
        report_generator.record_rows("entities_table", 987654)
        report_generator.record_scripts("entities_table", [entities_script])
        report_generator.record_skipped_lines("entities_table", [])

        report_generator.finish()
        report_path = report_generator.generate(tmp_path)

        content = report_path.read_text(encoding="utf-8")
        # Both tables should be present
        assert "Table: alias_table" in content
        assert "Table: entities_table" in content
        # Correct row counts
        assert "Total rows:        1234567" in content
        assert "Total rows:        987654" in content
        # Correct file counts
        assert "SQL files:         1" in content


class TestTableStatisticsDataclass:
    """Test the TableStats dataclass."""

    def test_table_stats_initialization(self):
        """TableStats initializes with correct defaults."""
        stats = TableStats(name="test_table")
        assert stats.name == "test_table"
        assert stats.row_count == 0
        assert stats.file_count == 0
        assert stats.total_size_bytes == 0
        assert stats.script_paths == []
        assert stats.skipped_lines == []

    def test_table_stats_custom_values(self):
        """TableStats accepts custom values."""
        paths = [Path("a.sql"), Path("b.sql")]
        skipped = [(1, "invalid")]
        stats = TableStats(
            name="test",
            row_count=100,
            file_count=2,
            total_size_bytes=5000,
            script_paths=paths,
            skipped_lines=skipped,
        )
        assert stats.row_count == 100
        assert stats.file_count == 2
        assert stats.total_size_bytes == 5000
        assert stats.script_paths == paths
        assert stats.skipped_lines == skipped
