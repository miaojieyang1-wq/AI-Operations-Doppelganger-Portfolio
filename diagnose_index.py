"""Diagnose local knowledge index status after moving devices.

Run:
    python diagnose_index.py

The index is runtime data, so it is intentionally not committed to GitHub.
This script does not modify files; it only reports what the new device sees.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import build_index
import rag_engine
import runtime_paths


SUPPORTED_SUFFIXES = {".md", ".docx"}


def print_item(ok: bool, title: str, detail: str = "") -> None:
    prefix = "[OK]" if ok else "[WARN]"
    print(f"{prefix} {title}")
    if detail:
        print(f"     {detail}")


def count_source_documents(source_dirs: list[Path]) -> tuple[int, list[Path]]:
    files: list[Path] = []
    for source_dir in source_dirs:
        if not source_dir.exists():
            continue
        files.extend(
            path
            for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        )
    return len(files), files


def read_vectorstore_summary() -> tuple[bool, int, str]:
    if not rag_engine.LOCAL_VECTORSTORE_FILE.exists():
        return False, 0, "local_vectors.json does not exist"
    try:
        data = json.loads(rag_engine.LOCAL_VECTORSTORE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - diagnostics should report all failures
        return False, 0, f"local_vectors.json cannot be read: {exc}"
    return True, len(data.get("documents", [])), "local_vectors.json is readable"


def main() -> int:
    runtime_dir = runtime_paths.ensure_runtime_dirs()
    source_dirs = build_index.get_source_dirs()
    source_count, source_files = count_source_documents(source_dirs)
    vector_exists, chunk_count, vector_message = read_vectorstore_summary()

    print("Knowledge index diagnostic report")
    print("=" * 40)
    print(f"Project directory: {build_index.PROJECT_DIR}")
    print(f"Runtime data directory: {runtime_dir}")
    print(f"Index directory: {rag_engine.CHROMA_DIR}")
    print(f"Index file: {rag_engine.LOCAL_VECTORSTORE_FILE}")
    print()

    print_item(build_index.WORKS_DIR.exists(), "works/ directory", str(build_index.WORKS_DIR))
    print_item(source_count > 0, "source documents found", f"{source_count} markdown/docx files")
    if source_files[:8]:
        print("     sample files:")
        for path in source_files[:8]:
            try:
                display = path.relative_to(build_index.PROJECT_DIR)
            except ValueError:
                display = path
            print(f"     - {display}")

    print_item(vector_exists, "local vector index file", vector_message)
    print_item(chunk_count > 0, "indexed chunks", f"{chunk_count} chunks")

    demo_mode = os.getenv("AI_OPS_DEMO_MODE", "0").strip() == "1"
    print_item(
        not demo_mode,
        "real-time mode",
        "AI_OPS_DEMO_MODE=1 bypasses RAG retrieval" if demo_mode else "RAG retrieval can be used",
    )

    sync_enabled = os.getenv(build_index.SYNC_ENABLED_ENV, "").strip()
    sync_dir = os.getenv(build_index.SYNC_DIR_ENV, "").strip()
    if sync_enabled:
        print_item(bool(sync_dir), "optional sync directory", sync_dir or "enabled but path is empty")

    print()
    if not vector_exists or chunk_count == 0:
        print("Suggested fix:")
        print("  1. Make sure works/ contains the portfolio markdown/docx files.")
        print("  2. Run: python build_index.py")
        print("  3. Run this script again and confirm indexed chunks > 0.")
        print("  4. Restart Streamlit, or use the sidebar rebuild button once more after refresh.")
        return 1

    print("Index looks available on this device.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
