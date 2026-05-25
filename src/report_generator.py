"""Report generator module for the JSONL-to-MySQL import system."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import os


@dataclass
class TableStats:
    """Statistics for a single table during import."""

    name: str
    row_count: int = 0
    file_count: int = 0
    total_size_bytes: int = 0
    script_paths: List[Path] = field(default_factory=list)
    skipped_lines: List[Tuple[int, str]] = field(default_factory=list)


class ReportGenerator:
    """Tracks import statistics and generates a report file."""

    def __init__(self):
        """Initialize the ReportGenerator with empty state."""
        self.start_time: datetime = None
        self.end_time: datetime = None
        self.tables: dict[str, TableStats] = {}

    def start(self):
        """Record start time."""
        self.start_time = datetime.now()

    def finish(self):
        """Record end time."""
        self.end_time = datetime.now()

    def add_table(self, table_name: str):
        """Register a table for tracking.

        Args:
            table_name: The name of the table to register.
        """
        self.tables[table_name] = TableStats(name=table_name)

    def record_rows(self, table_name: str, count: int):
        """Add row count for a table.

        Args:
            table_name: The name of the table.
            count: The number of rows processed.
        """
        if table_name in self.tables:
            self.tables[table_name].row_count = count

    def record_scripts(self, table_name: str, script_paths: List[Path]):
        """Record generated script file paths for a table.

        Updates file_count and total_size_bytes based on the actual files.

        Args:
            table_name: The name of the table.
            script_paths: List of Path objects to the generated SQL script files.
        """
        if table_name in self.tables:
            self.tables[table_name].script_paths = script_paths
            self.tables[table_name].file_count = len(script_paths)
            # Calculate total size of all script files
            total_size = 0
            for path in script_paths:
                if path.exists():
                    total_size += path.stat().st_size
            self.tables[table_name].total_size_bytes = total_size

    def record_skipped_lines(self, table_name: str, skipped: List[Tuple[int, str]]):
        """Record skipped line info (line_number, reason) for a table.

        Args:
            table_name: The name of the table.
            skipped: List of tuples (line_number, reason) for skipped lines.
        """
        if table_name in self.tables:
            self.tables[table_name].skipped_lines = skipped

    def generate(self, output_path: Path) -> Path:
        """Write the import_report.txt file and return its path.

        Generates a comprehensive report including start/end times, duration, and
        per-table statistics (row counts, file counts, sizes, skipped lines, and file paths).

        Args:
            output_path: Directory where the report file should be written.

        Returns:
            Path to the generated import_report.txt file.
        """
        output_path.mkdir(parents=True, exist_ok=True)
        report_file = output_path / "import_report.txt"

        with open(report_file, "w", encoding="utf-8") as f:
            # Write header
            f.write("JSONL to MySQL Import Report\n")
            f.write("=============================\n")

            # Write timing information
            if self.start_time:
                f.write(f"Start time:  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if self.end_time:
                f.write(f"End time:    {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Calculate and write duration
            if self.start_time and self.end_time:
                duration_seconds = (self.end_time - self.start_time).total_seconds()
                f.write(f"Duration:    {duration_seconds:.2f} seconds\n")

            f.write("\n")

            # Write per-table statistics
            for table_name in sorted(self.tables.keys()):
                stats = self.tables[table_name]
                f.write(f"Table: {stats.name}\n")
                f.write(f"  Total rows:        {stats.row_count}\n")
                f.write(f"  SQL files:         {stats.file_count}\n")

                # Convert total size to MB
                size_mb = stats.total_size_bytes / (1024 * 1024)
                f.write(f"  Total SQL size:    {size_mb:.2f} MB\n")

                # Write skipped lines
                f.write(f"  Skipped lines:     {len(stats.skipped_lines)}\n")
                for line_num, reason in stats.skipped_lines:
                    f.write(f"    Line {line_num}: {reason}\n")

                # Write script file paths
                f.write("  Script files:\n")
                for script_path in stats.script_paths:
                    f.write(f"    {script_path}\n")

                f.write("\n")

        return report_file
