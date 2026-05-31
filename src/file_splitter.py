"""FileSplitter: splits a large text file into size-bounded chunks on line boundaries."""

import argparse
from pathlib import Path
from typing import List


class FileSplitter:
    DEFAULT_CHUNK_SIZE = 500 * 1024 * 1024  # 500 MB

    def split(self, input_path: Path, output_dir: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[Path]:
        """
        Split input_path into files of at most chunk_size bytes in output_dir.

        Each output file ends on a complete line boundary.
        Returns the list of created file paths in order.
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stem = input_path.stem
        suffix = input_path.suffix

        parts: List[Path] = []
        part_index = 0
        current_bytes = 0
        current_file = None

        def _open_next() -> None:
            nonlocal part_index, current_bytes, current_file
            part_index += 1
            path = output_dir / "{}_{}{:03d}{}".format(stem, "part", part_index, suffix)
            current_file = open(path, "wb")
            parts.append(path)
            current_bytes = 0

        with open(input_path, "rb") as src:
            for line in src:
                if current_file is None:
                    _open_next()
                current_file.write(line)
                current_bytes += len(line)
                if current_bytes >= chunk_size:
                    current_file.close()
                    current_file = None

        if current_file is not None:
            current_file.close()

        return parts


def main() -> None:
    parser = argparse.ArgumentParser(description="Split a large text file into chunks.")
    parser.add_argument("input", help="Path to the input file")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: same directory as input)")
    parser.add_argument("--chunk-size-mb", type=int, default=500, help="Maximum chunk size in MB (default: 500)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    chunk_size = args.chunk_size_mb * 1024 * 1024

    print("Splitting {} into {} MB chunks → {}/".format(input_path, args.chunk_size_mb, output_dir))
    parts = FileSplitter().split(input_path, output_dir, chunk_size=chunk_size)
    print("Done: {} file(s) created".format(len(parts)))
    for p in parts:
        print("  {}".format(p))


if __name__ == "__main__":
    main()
