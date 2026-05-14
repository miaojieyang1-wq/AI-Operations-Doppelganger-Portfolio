"""运行时路径管理。

这个模块把“应用资源目录”和“用户可写数据目录”分开：
- 应用资源目录：项目代码、works、static、config 等随应用分发的只读资源。
- 用户数据目录：.env、数据库、报告、索引、缓存等运行时产生的文件。
"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from dotenv import load_dotenv


APP_NAME = "AI_Ops_Agent"
APP_DIR = Path(__file__).resolve().parent


def get_user_data_dir() -> Path:
    """返回当前系统推荐的用户级可写数据目录。"""
    override = os.getenv("AI_OPS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    system = platform.system().lower()
    if system == "windows":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME


USER_DATA_DIR = get_user_data_dir()
RUNTIME_ENV_FILE = USER_DATA_DIR / ".env"
RUNTIME_SECURITY_FILE = USER_DATA_DIR / "security.json"


def ensure_runtime_dirs() -> Path:
    """创建用户数据目录及常用子目录。"""
    for path in [
        USER_DATA_DIR,
        USER_DATA_DIR / "reports",
        USER_DATA_DIR / "reports" / "json",
        USER_DATA_DIR / "reports" / "collaboration",
        USER_DATA_DIR / "activity_plans",
        USER_DATA_DIR / "cache",
        USER_DATA_DIR / "db",
        USER_DATA_DIR / "chroma_db",
    ]:
        if path.exists() and not path.is_dir():
            backup_path = path.with_name(f"{path.name}.file_backup")
            backup_index = 1
            while backup_path.exists():
                backup_path = path.with_name(f"{path.name}.file_backup_{backup_index}")
                backup_index += 1
            path.rename(backup_path)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            if path.is_dir():
                continue
            backup_path = path.with_name(f"{path.name}.file_backup")
            backup_index = 1
            while backup_path.exists():
                backup_path = path.with_name(f"{path.name}.file_backup_{backup_index}")
                backup_index += 1
            path.rename(backup_path)
            path.mkdir(parents=True, exist_ok=True)
    return USER_DATA_DIR


def data_path(*parts: str | Path) -> Path:
    """返回用户数据目录下的路径。"""
    ensure_runtime_dirs()
    return USER_DATA_DIR.joinpath(*map(Path, parts))


def legacy_project_file(name: str) -> Path:
    """返回旧版本项目根目录下的文件路径，仅用于兼容读取。"""
    return APP_DIR / name


def migrate_file_once(legacy_file: Path, target_file: Path) -> bool:
    """把旧位置文件复制到新位置；非破坏性，不删除旧文件。"""
    if target_file.exists() or not legacy_file.exists():
        return False
    target_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy_file, target_file)
    return True


def migrate_runtime_files() -> None:
    """迁移旧版运行时文件到用户数据目录。"""
    ensure_runtime_dirs()
    migrate_file_once(APP_DIR / ".env", RUNTIME_ENV_FILE)
    migrate_file_once(APP_DIR / "local_demo.db", USER_DATA_DIR / "db" / "local_demo.db")


def load_runtime_env() -> None:
    """加载运行时环境变量，兼容旧项目根目录 .env。"""
    migrate_runtime_files()
    load_dotenv(RUNTIME_ENV_FILE, override=False)
    legacy_env = APP_DIR / ".env"
    if legacy_env.exists():
        load_dotenv(legacy_env, override=False)


def default_database_url() -> str:
    """返回默认 SQLite 数据库连接串，位置在用户数据目录。"""
    db_file = data_path("db", "local_demo.db")
    return f"sqlite:///{db_file.as_posix()}"
