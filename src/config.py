"""Configuration module for the JSONL-to-MySQL import system."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    # Database settings
    host: str = "localhost"
    port: int = 3306
    database: str = ""
    username: str = ""
    password: str = ""

    # File settings
    alias_file: str = "alias_table.jsonl"
    entity_file: str = "entities.jsonl"
    output_dir: str = "./output"

    # Processing settings
    batch_size: int = 1000
    max_file_size_mb: int = 50

    # Execution mode
    execute: bool = False

    def __post_init__(self):
        if not (1 <= self.port <= 65535):
            raise ValueError(f"port must be between 1 and 65535, got {self.port}")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be > 0, got {self.batch_size}")
        if self.max_file_size_mb <= 0:
            raise ValueError(f"max_file_size_mb must be > 0, got {self.max_file_size_mb}")


def load_config(config_path: Optional[str] = None, **overrides) -> Config:
    """Load configuration from an optional JSON file and apply CLI overrides.

    Args:
        config_path: Path to import_config.json. If None, defaults are used.
        **overrides: Key/value pairs that override any file-sourced values.

    Returns:
        A fully-populated Config instance.
    """
    # Start with dataclass defaults
    kwargs: dict = {}

    if config_path is not None:
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        db = data.get("database", {})
        if "host" in db:
            kwargs["host"] = db["host"]
        if "port" in db:
            kwargs["port"] = int(db["port"])
        if "database" in db:
            kwargs["database"] = db["database"]
        if "username" in db:
            kwargs["username"] = db["username"]
        if "password" in db:
            kwargs["password"] = db["password"]

        files = data.get("files", {})
        if "alias_file" in files:
            kwargs["alias_file"] = files["alias_file"]
        if "entity_file" in files:
            kwargs["entity_file"] = files["entity_file"]
        if "output_dir" in files:
            kwargs["output_dir"] = files["output_dir"]

        processing = data.get("processing", {})
        if "batch_size" in processing:
            kwargs["batch_size"] = int(processing["batch_size"])
        if "max_file_size_mb" in processing:
            kwargs["max_file_size_mb"] = int(processing["max_file_size_mb"])

    # Apply CLI overrides last (only non-None values)
    for key, value in overrides.items():
        if value is not None:
            kwargs[key] = value

    return Config(**kwargs)
