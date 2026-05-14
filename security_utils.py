"""后台认证与 API Token 工具。

后台密码只保存带盐哈希，不保存明文；API Token 只从环境变量读取。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

import runtime_paths


HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """生成可保存的带盐密码哈希。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, encoded_hash: str | None) -> bool:
    """校验明文密码与保存的哈希是否匹配。"""
    if not password or not encoded_hash:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded_hash.split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations_text),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _read_security_file() -> dict:
    path = runtime_paths.RUNTIME_SECURITY_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_security_file(data: dict) -> None:
    runtime_paths.ensure_runtime_dirs()
    runtime_paths.RUNTIME_SECURITY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_admin_password_hash() -> str | None:
    """读取后台密码哈希；未初始化时返回 None。"""
    env_hash = os.getenv("AI_OPS_ADMIN_PASSWORD_HASH")
    if env_hash:
        return env_hash
    return _read_security_file().get("admin_password_hash")


def is_admin_initialized() -> bool:
    """后台是否已经完成安全初始化。"""
    return bool(get_admin_password_hash())


def set_admin_password(password: str) -> None:
    """初始化或更新后台密码。"""
    data = _read_security_file()
    data["admin_password_hash"] = hash_password(password)
    _write_security_file(data)


def verify_admin_password(password: str) -> bool:
    """后台登录校验。"""
    return verify_password(password, get_admin_password_hash())


def get_api_token() -> str | None:
    """读取 API Bearer Token；为空时代表仅本机开发模式。"""
    token = os.getenv("AI_OPS_API_TOKEN", "").strip()
    return token or None


def mask_secret(value: str | None) -> str:
    """脱敏展示密钥。"""
    if not value:
        return "未配置"
    if len(value) <= 8:
        return value[:2] + "****"
    return f"{value[:3]}****{value[-4:]}"

