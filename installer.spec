# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_dir = Path.cwd()


def collect_tree(relative_path: str):
    source = project_dir / relative_path
    if not source.exists():
        return []
    datas = []
    for file_path in source.rglob("*"):
        if file_path.is_file():
            parts = set(file_path.parts)
            if "__pycache__" in parts or ".git" in parts:
                continue
            if any(part.startswith(("tmp_", "chroma_db_backup")) for part in parts):
                continue
            if file_path.suffix.lower() in {".tmp", ".log", ".pyc", ".db"}:
                continue
            datas.append((str(file_path), str(file_path.parent.relative_to(project_dir))))
    return datas


datas = []
for pattern in ["*.py", "*.yaml", "*.yml", "*.txt", "*.md", "*.json"]:
    for file_path in project_dir.glob(pattern):
        if file_path.name.startswith(".") or file_path.name.endswith(".tmp"):
            continue
        if file_path.name in {"local_demo.db"}:
            continue
        datas.append((str(file_path), "."))

for folder in ["config", "works", "static", "archive/prompt_txt_backup"]:
    datas.extend(collect_tree(folder))


a = Analysis(
    ["install.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "streamlit",
        "openai",
        "dotenv",
        "yaml",
        "sqlalchemy",
        "fastapi",
        "uvicorn",
        "sklearn",
        "matplotlib",
        "langgraph",
        "pydantic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["__pycache__", "pytest", "unittest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="install",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
