from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from re import Pattern


def write_timestamped_report(
    report_text: str,
    target_dir: Path,
    workflow_label: str,
    suffix: str = ".txt",
) -> Path:
    """Write a timestamped report and return the saved path."""
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = workflow_label.replace(" ", "_").replace("/", "_")
    report_path = target_dir / f"{safe_name}_{timestamp}{suffix}"
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def append_once(report_text: str, marker: str, append_text: str) -> str:
    """Append text only when the marker is not already present."""
    clean_report = report_text.strip()
    if marker in clean_report:
        return clean_report
    return f"{clean_report}\n\n---\n\n{append_text}"


@lru_cache(maxsize=128)
def format_report_markdown_cached(
    report_text: str,
    heading_pattern: Pattern[str],
    numbered_pattern: Pattern[str],
) -> str:
    formatted_lines: list[str] = []
    seen_heading = False

    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        heading_match = heading_pattern.match(line)
        numbered_match = numbered_pattern.match(line)

        if heading_match:
            if seen_heading:
                formatted_lines.append("\n---\n")
            formatted_lines.append(f"### **{heading_match.group(1).strip()}**")
            seen_heading = True
        elif numbered_match:
            if seen_heading:
                formatted_lines.append("\n---\n")
            title = numbered_match.group(1).strip()
            rest = numbered_match.group(2).strip()
            formatted_lines.append(f"### **{title}**")
            if rest:
                formatted_lines.append(rest)
            seen_heading = True
        else:
            formatted_lines.append(raw_line)

    return "\n".join(formatted_lines)


@lru_cache(maxsize=64)
def format_heading_only_markdown_cached(report_text: str, heading_pattern: Pattern[str]) -> str:
    formatted_lines: list[str] = []
    seen_heading = False

    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        heading_match = heading_pattern.match(line)

        if heading_match:
            if seen_heading:
                formatted_lines.append("\n---\n")
            formatted_lines.append(f"### **{heading_match.group(1).strip()}**")
            seen_heading = True
        else:
            formatted_lines.append(raw_line)

    return "\n".join(formatted_lines)


def folder_uri(folder_path: Path) -> str:
    folder_path.mkdir(exist_ok=True)
    return folder_path.resolve().as_uri()


def save_markdown_file(text: str, target_dir: Path, filename_prefix: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = target_dir / f"{filename_prefix}_{timestamp}.md"
    file_path.write_text(text, encoding="utf-8")
    return file_path
