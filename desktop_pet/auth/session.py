"""当前登录会话（进程内；可选持久化到文件）。"""
from pathlib import Path
from typing import Optional

from desktop_pet.config import AUTH_DATA_DIR, ensure_dirs
from desktop_pet.auth.models import User


class Session:
    """当前用户：登录后设置，访客为 None。"""
    _current: Optional[User] = None

    @classmethod
    def set_current(cls, user: Optional[User]) -> None:
        cls._current = user

    @classmethod
    def get_current(cls) -> Optional[User]:
        return cls._current

    @classmethod
    def is_guest(cls) -> bool:
        return cls._current is None
