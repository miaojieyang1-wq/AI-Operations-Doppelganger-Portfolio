# -*- coding: utf-8 -*-
"""Utility functions for the standalone knowledge governance console."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

DEFAULT_DATA_DIR = "data"
DEFAULT_CONFIG_FILE = "config.yaml"
KNOWLEDGE_BASE_KEY = "knowledge_base_file"
BADCASE_LOG_KEY = "badcase_log_file"


def _read_simple_yaml(path: Path) -> dict[str, str]:
    """Read the tiny config file without requiring PyYAML."""
    config: dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            for raw_line in file_obj:
                line = raw_line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                config[key.strip()] = value.strip().strip("\"'")
    except OSError as exc:
        LOGGER.warning("Unable to read config file %s: %s", path, exc)
    return config


def load_config() -> dict[str, str]:
    config_path = Path(DEFAULT_CONFIG_FILE)
    config = {
        "data_dir": DEFAULT_DATA_DIR,
        KNOWLEDGE_BASE_KEY: "knowledge_base.json",
        BADCASE_LOG_KEY: "badcase_log.json",
    }
    if config_path.exists():
        config.update({key: value for key, value in _read_simple_yaml(config_path).items() if value})
    return config


def get_data_path(config_key: str) -> Path:
    config = load_config()
    data_dir = Path(config.get("data_dir", DEFAULT_DATA_DIR))
    file_name = config.get(config_key)
    if not file_name:
        raise ValueError(f"Missing required config value: {config_key}")
    return data_dir / file_name


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc
    except OSError as exc:
        raise OSError(f"Unable to read JSON file: {path}") from exc
    if not isinstance(data, list):
        raise ValueError(f"JSON root must be a list: {path}")
    return data


def _save_json_list(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8", newline="\n") as file_obj:
            json.dump(data, file_obj, ensure_ascii=False, indent=2)
            file_obj.write("\n")
    except OSError as exc:
        raise OSError(f"Unable to write JSON file: {path}") from exc


def load_knowledge_base() -> list[dict[str, Any]]:
    """Load knowledge units from the configured JSON file."""
    return _load_json_list(get_data_path(KNOWLEDGE_BASE_KEY))


def save_knowledge_base(data: list[dict[str, Any]]) -> None:
    """Save knowledge units to the configured JSON file."""
    _save_json_list(get_data_path(KNOWLEDGE_BASE_KEY), data)


def load_badcase_log() -> list[dict[str, Any]]:
    """Load badcase records from the configured JSON file."""
    return _load_json_list(get_data_path(BADCASE_LOG_KEY))


def save_badcase_log(data: list[dict[str, Any]]) -> None:
    """Save badcase records to the configured JSON file."""
    _save_json_list(get_data_path(BADCASE_LOG_KEY), data)


def generate_kid() -> str:
    """Generate KID-YYYYMMDD-NNN using the current day's existing records."""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"KID-{today}-"
    existing_ids = [
        item.get("knowledge_id", "")
        for item in load_knowledge_base()
        if str(item.get("knowledge_id", "")).startswith(prefix)
    ]
    next_number = len(existing_ids) + 1
    return f"{prefix}{next_number:03d}"
