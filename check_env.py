"""AI 运营分身环境检查脚本。

此脚本不修改任何项目入口，只用于手动检查：
- 必要环境变量是否存在，或是否已开启演示模式
- 用户数据目录是否可写
- 关键项目目录是否存在
- Python 版本是否满足要求
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
REQUIRED_DIRS = ["config", "works", "static"]
OPTIONAL_ENV_VARS = [
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "AI_OPS_DATA_DIR",
    "AI_OPS_ADMIN_PASSWORD_HASH",
    "AI_OPS_API_TOKEN",
    "AI_OPS_API_PERSISTENCE",
    "AI_OPS_ENABLE_LOCAL_SAVE",
    "AI_OPS_SAVE_JSON_SIDECAR",
    "DATABASE_URL",
]


def get_runtime_dir() -> Path:
    """返回用户级运行数据目录，不写入安装目录。"""
    override = os.getenv("AI_OPS_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if base:
            return Path(base) / "AI_Ops_Agent"
    return Path.home() / ".local" / "share" / "AI_Ops_Agent"


def check_python_version() -> tuple[bool, str]:
    """检查 Python 版本。"""
    version = sys.version_info
    ok = version >= (3, 10)
    message = f"Python {version.major}.{version.minor}.{version.micro}"
    return ok, message


def check_runtime_writable(runtime_dir: Path) -> tuple[bool, str]:
    """检查运行目录是否可写。"""
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=runtime_dir, delete=True):
            pass
        return True, str(runtime_dir)
    except OSError as exc:
        return False, f"{runtime_dir} 不可写：{exc}"


def check_required_dirs() -> list[tuple[bool, str]]:
    """检查关键目录。"""
    results = []
    for dirname in REQUIRED_DIRS:
        path = PROJECT_DIR / dirname
        results.append((path.exists() and path.is_dir(), str(path)))
    return results


def check_api_mode() -> tuple[bool, str]:
    """检查 API Key 或演示模式是否可用。"""
    demo_mode = os.getenv("AI_OPS_DEMO_MODE", "0").strip() == "1"
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if api_key:
        return True, "已检测到 DEEPSEEK_API_KEY"
    if demo_mode:
        return True, "未检测到 API Key，但已开启演示模式"
    return False, "未检测到 DEEPSEEK_API_KEY，且未开启 AI_OPS_DEMO_MODE=1"


def print_result(ok: bool, message: str) -> None:
    """输出友好的检查结果。"""
    prefix = "[OK]" if ok else "[FAIL]"
    print(f"{prefix} {message}")


def main() -> int:
    """执行环境检查。"""
    has_error = False

    ok, message = check_python_version()
    print_result(ok, message)
    has_error = has_error or not ok

    runtime_dir = get_runtime_dir()
    ok, message = check_runtime_writable(runtime_dir)
    print_result(ok, f"运行数据目录：{message}" if ok else message)
    has_error = has_error or not ok

    for ok, path in check_required_dirs():
        print_result(ok, f"关键目录：{path}")
        has_error = has_error or not ok

    ok, message = check_api_mode()
    print_result(ok, message)
    has_error = has_error or not ok

    for name in OPTIONAL_ENV_VARS:
        value = os.getenv(name, "").strip()
        print_result(True, f"可选环境变量 {name}：{'已设置' if value else '未设置'}")

    if has_error:
        print("\n环境检查未通过。请根据上方提示修复后再启动应用。")
        return 1

    print("\n环境检查通过，可以启动应用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
