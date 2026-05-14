"""AI运营分身安装器启动器。

这个文件用于被 PyInstaller 打成单文件 exe。它不直接运行应用，
而是把内置的干净项目包解压到用户级安装目录，然后调用 install.py
继续完成依赖、API Key、后台密码和知识库索引等配置。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


APP_DIR_NAME = "AI_Ops_Agent"
PAYLOAD_NAME = "AI_Ops_Agent_payload.zip"


def resource_dir() -> Path:
    """返回 PyInstaller 临时资源目录；开发状态下返回当前文件目录。"""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


def user_install_dir() -> Path:
    """返回用户级安装目录，避免写入 Program Files 等只读目录。"""
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "Programs" / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_DIR_NAME


def find_python() -> str | None:
    """寻找系统 Python，用于运行解压后的 install.py。"""
    candidates = ["python", "py"]
    for candidate in candidates:
        path = shutil.which(candidate)
        if not path:
            continue
        try:
            result = subprocess.run(
                [path, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception:
            continue
        if result.returncode == 0:
            return path
    return None


def verify_payload(payload_path: Path) -> bool:
    """检查内置项目包是否包含关键文件。"""
    if not payload_path.exists():
        print(f"Payload not found: {payload_path}")
        return False
    required = {
        "app.py",
        "install.py",
        "requirements.txt",
        "README.md",
        "config/app.yaml",
        "works/agent-design-iteration.md",
    }
    with zipfile.ZipFile(payload_path) as payload:
        names = set(payload.namelist())
    missing = sorted(required - names)
    if missing:
        print("Payload is incomplete:")
        for item in missing:
            print(f"  - missing {item}")
        return False
    return True


def install_payload(payload_path: Path, install_dir: Path) -> None:
    """解压项目文件到用户级安装目录。"""
    install_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(payload_path) as payload:
        payload.extractall(install_dir)


def run_setup_wizard(install_dir: Path, python_exe: str) -> int:
    """调用解压后的 install.py，进入真正的安装向导。"""
    install_script = install_dir / "install.py"
    if not install_script.exists():
        print(f"install.py not found in {install_dir}")
        return 1
    return subprocess.call([python_exe, str(install_script)], cwd=install_dir)


def main() -> int:
    """安装器入口。"""
    parser = argparse.ArgumentParser(description="AI Ops Agent installer")
    parser.add_argument("--check", action="store_true", help="Only verify embedded payload.")
    args = parser.parse_args()

    payload_path = resource_dir() / PAYLOAD_NAME
    if not verify_payload(payload_path):
        return 1
    if args.check:
        print("Installer payload check passed.")
        return 0

    install_dir = user_install_dir()
    print("=" * 58)
    print("AI Ops Agent Setup")
    print("=" * 58)
    print(f"Install location: {install_dir}")
    print("Extracting application files...")
    install_payload(payload_path, install_dir)
    print("Files extracted.")

    python_exe = find_python()
    if not python_exe:
        print()
        print("Python 3.10 or later was not found.")
        print("Please install Python 3.10+, then run install.py in:")
        print(install_dir)
        input("Press Enter to exit...")
        return 1

    print(f"Using Python: {python_exe}")
    print("Starting setup wizard...")
    return_code = run_setup_wizard(install_dir, python_exe)
    input("Press Enter to exit...")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
