"""用户注册与登录存储（本地 JSON，MVP）。"""
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from desktop_pet.config import AUTH_DATA_DIR, ensure_dirs
from desktop_pet.auth.models import User


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode()).hexdigest()


class AuthStore:
    """用户存储：按 username 索引，支持注册与登录验证。"""
    _index_file = "users.json"

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or AUTH_DATA_DIR
        ensure_dirs()

    def _index_path(self) -> Path:
        return self.base_dir / self._index_file

    def _user_path(self, user_id: str) -> Path:
        return self.base_dir / f"user_{user_id}.json"

    def _load_index(self) -> dict:
        if not self._index_path().exists():
            return {"by_username": {}, "ids": []}
        with open(self._index_path(), "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, data: dict) -> None:
        with open(self._index_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def register(self, username: str, password: str) -> Optional[str]:
        """注册新用户。成功返回 user_id，用户名已存在返回 None。"""
        username = username.strip().lower()
        if not username or not password:
            return None
        index = self._load_index()
        if username in index.get("by_username", {}):
            return None
        user_id = secrets.token_hex(8)
        salt = secrets.token_hex(16)
        password_hash = _hash_password(password, salt)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        user = User(
            id=user_id,
            username=username,
            password_hash=password_hash,
            salt=salt,
            created_at=now,
        )
        path = self._user_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(user.model_dump_json(indent=2))
        index.setdefault("by_username", {})[username] = user_id
        index.setdefault("ids", []).append(user_id)
        self._save_index(index)
        return user_id

    def login(self, username: str, password: str) -> Optional[User]:
        """登录：验证账号密码，成功返回 User，否则 None。"""
        username = username.strip().lower()
        if not username or not password:
            return None
        index = self._load_index()
        user_id = index.get("by_username", {}).get(username)
        if not user_id:
            return None
        path = self._user_path(user_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            user = User.model_validate(json.load(f))
        if _hash_password(password, user.salt) != user.password_hash:
            return None
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """按 user_id 获取用户。"""
        path = self._user_path(user_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return User.model_validate(json.load(f))
