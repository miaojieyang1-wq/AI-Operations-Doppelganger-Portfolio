"""
AI运营分身安装向导。

这个脚本面向非技术用户，负责完成环境检查、依赖安装、API 配置、
知识库索引构建、桌面启动器创建和应用启动。
"""

from __future__ import annotations

import importlib
import platform
import shutil
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

import runtime_paths
import security_utils

PROJECT_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"
ENV_FILE = runtime_paths.RUNTIME_ENV_FILE
CONFIG_FILE = PROJECT_DIR / "config" / "app.yaml"


PACKAGE_IMPORT_MAP = {
    "python-dotenv": "dotenv",
    "scikit-learn": "sklearn",
    "PyYAML": "yaml",
    "SQLAlchemy": "sqlalchemy",
}


class Color:
    """终端彩色输出。"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def color(text: str, code: str) -> str:
    """给文字加颜色；不支持颜色的终端也能显示原文。"""
    return f"{code}{text}{Color.RESET}"


def ok(text: str) -> None:
    """显示成功项。"""
    print(color(f"✓ {text}", Color.GREEN))


def fail(text: str, suggestion: str = "") -> None:
    """显示失败项和修复建议。"""
    print(color(f"✗ {text}", Color.RED))
    if suggestion:
        print(color(f"  修复建议：{suggestion}", Color.YELLOW))


def info(text: str) -> None:
    """显示普通提示。"""
    print(color(text, Color.BLUE))


def ask_yes_no(question: str, default: bool = True) -> bool:
    """询问是否执行某步骤。"""
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{question} ({suffix})：").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes", "是", "好", "1"}


def show_welcome() -> None:
    """显示欢迎界面。"""
    print()
    print("=" * 62)
    print(color("欢迎使用AI运营分身安装向导", Color.BOLD + Color.BLUE))
    print("=" * 62)
    print("我会帮您检查环境、安装依赖、写入配置并创建启动脚本。")
    print()


def check_environment() -> None:
    """检查基础运行环境。"""
    info("第一步：环境自检")
    if sys.version_info >= (3, 10):
        ok(f"Python版本：{platform.python_version()}")
    else:
        fail("Python版本低于3.10", "请安装 Python 3.10 或更高版本后再运行。")

    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True, text=True)
        ok("pip可用")
    except Exception:
        fail("pip不可用", "请重新安装 Python，并勾选 pip 组件。")

    if shutil.which("git"):
        ok("git可用")
    else:
        print(color("! git未检测到（可选项，不影响基础运行）", Color.YELLOW))

    try:
        importlib.import_module("streamlit")
        ok("Streamlit已可用")
    except Exception:
        print(color("! Streamlit暂未安装，稍后会通过 requirements.txt 安装。", Color.YELLOW))
    print()


def read_requirements() -> list[str]:
    """读取依赖列表。"""
    if not REQUIREMENTS_FILE.exists():
        fail("未找到 requirements.txt", "请确认安装向导位于项目根目录。")
        return []
    packages: list[str] = []
    for line in REQUIREMENTS_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        item = line.strip()
        if item and not item.startswith("#"):
            packages.append(item)
    return packages


def package_to_import_name(package: str) -> str:
    """将 pip 包名转换成常见 import 名。"""
    base = package.split("==")[0].split(">=")[0].split("<=")[0].strip()
    return PACKAGE_IMPORT_MAP.get(base, base.replace("-", "_").lower())


def install_dependencies() -> None:
    """安装并验证依赖。"""
    packages = read_requirements()
    if not packages:
        return

    info("第二步：依赖安装")
    print("将安装以下依赖：")
    for package in packages:
        print(f"  - {package}")

    if not ask_yes_no("是否现在安装/检查这些依赖", True):
        print(f"已跳过依赖安装。后续可手动运行：{sys.executable} -m pip install -r {REQUIREMENTS_FILE}")
        return

    command = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)]
    process = subprocess.Popen(command, cwd=PROJECT_DIR)
    return_code = process.wait()
    if return_code != 0:
        fail("依赖安装未完全成功", f"请手动运行：{sys.executable} -m pip install -r {REQUIREMENTS_FILE}")
        return

    ok("依赖安装完成")
    print("正在验证依赖导入：")
    for index, package in enumerate(packages, start=1):
        import_name = package_to_import_name(package)
        bar = "#" * index + "-" * max(0, len(packages) - index)
        try:
            importlib.import_module(import_name)
            ok(f"[{bar}] {package}")
        except Exception:
            fail(f"[{bar}] {package}导入失败", f"请尝试：{sys.executable} -m pip install {package}")
    print()


def write_env_file(api_key: str) -> None:
    """写入 .env 文件。"""
    runtime_paths.ensure_runtime_dirs()
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = [
            line
            for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            if not line.startswith("DEEPSEEK_API_KEY=")
        ]
    lines.append(f"DEEPSEEK_API_KEY={api_key}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_admin_password(password: str) -> None:
    """初始化管理后台密码哈希，明文不会写入配置文件。"""
    try:
        security_utils.set_admin_password(password)
        ok(f"管理后台密码哈希已写入用户数据目录：{runtime_paths.RUNTIME_SECURITY_FILE}")
    except Exception:
        fail("管理后台密码初始化失败", "请稍后在网页管理后台首次打开时完成初始化。")


def configure_project() -> None:
    """引导用户完成 API 和后台密码配置。"""
    info("第三步：配置文件设置")
    if ENV_FILE.exists():
        print(".env 已存在。")
        if not ask_yes_no("是否重新设置 DeepSeek API Key", False):
            pass
        else:
            if ask_yes_no("是否现在填写 DeepSeek API Key", True):
                while True:
                    api_key = input("请输入 DeepSeek API Key（以 sk- 开头，支持粘贴）：").strip()
                    if api_key.startswith("sk-"):
                        write_env_file(api_key)
                        ok(".env 已创建/更新")
                        break
                    fail("API Key 格式看起来不正确", "DeepSeek API Key 通常以 sk- 开头，请重新输入。")
    elif ask_yes_no("是否现在填写 DeepSeek API Key", True):
        while True:
            api_key = input("请输入 DeepSeek API Key（以 sk- 开头，支持粘贴）：").strip()
            if api_key.startswith("sk-"):
                write_env_file(api_key)
                ok(".env 已创建/更新")
                break
            fail("API Key 格式看起来不正确", "DeepSeek API Key 通常以 sk- 开头，请重新输入。")
    else:
        print("已跳过 API Key 配置。首次打开网页时仍可选择演示模式。")

    if not security_utils.is_admin_initialized():
        print("管理后台尚未初始化。为避免公开默认口令，必须设置一个后台密码。")
        while True:
            password = input("请设置管理后台密码（至少 8 位）：").strip()
            confirm = input("请再次输入管理后台密码：").strip()
            if len(password) < 8:
                fail("密码太短", "请设置至少 8 位密码。")
            elif password != confirm:
                fail("两次输入不一致", "请重新输入。")
            else:
                update_admin_password(password)
                break
    else:
        print("管理后台密码已初始化。如需重置，请删除用户数据目录中的 security.json 后重新运行安装向导。")
    print()


def build_knowledge_index() -> None:
    """构建知识库索引。"""
    info("第四步：知识库索引构建")
    if not ask_yes_no("是否立即构建知识库索引", True):
        print("已跳过。后续可手动运行：python build_index.py")
        return
    process = subprocess.Popen([sys.executable, "build_index.py"], cwd=PROJECT_DIR)
    return_code = process.wait()
    if return_code == 0:
        ok("知识库索引构建完成")
    else:
        fail("知识库索引构建失败", "请稍后手动运行 python build_index.py，并根据提示处理。")
    print()


def find_free_port(start: int = 8501, limit: int = 20) -> int:
    """寻找可用端口。"""
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def create_desktop_launcher() -> None:
    """Create a desktop launcher."""
    info("Step 5: create desktop launcher")
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        desktop = PROJECT_DIR

    if platform.system().lower().startswith("win"):
        launcher = desktop / "AI_Ops_Agent-run.bat"
        content = f"""@echo off
chcp 65001 >nul
cd /d "{PROJECT_DIR}"
"{sys.executable}" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or later is required.
  pause
  exit /b 1
)
"{sys.executable}" -m streamlit run app.py
pause
"""
    else:
        launcher = desktop / "AI_Ops_Agent-run.sh"
        content = f"""#!/usr/bin/env bash
set -e
cd "{PROJECT_DIR}"
"{sys.executable}" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(1)
PY
"{sys.executable}" -m streamlit run app.py
"""
    launcher.write_text(content, encoding="utf-8")
    try:
        launcher.chmod(0o755)
    except Exception:
        pass
    ok(f"Launcher created: {launcher}")
    print()

def start_application() -> None:
    """询问是否启动应用。"""
    info("第六步：启动应用")
    print(color("安装完成！", Color.GREEN + Color.BOLD))
    if not ask_yes_no("是否立即启动应用", True):
        print("稍后可运行桌面启动脚本，或执行：streamlit run app.py")
        return
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"正在启动应用：{url}")
    webbrowser.open(url)
    subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(port)], cwd=PROJECT_DIR)


def main() -> None:
    """安装向导主流程。"""
    try:
        show_welcome()
        check_environment()
        install_dependencies()
        configure_project()
        build_knowledge_index()
        create_desktop_launcher()
        start_application()
    except KeyboardInterrupt:
        print("\n安装已取消。下次重新运行 install.py 可继续配置。")
    except Exception as exc:
        fail("安装向导遇到问题，但项目文件不会被破坏", f"错误信息：{exc}")


if __name__ == "__main__":
    main()
