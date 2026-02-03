"""登录与注册测试。"""
import tempfile
from pathlib import Path

from desktop_pet.auth.store import AuthStore
from desktop_pet.auth.models import User


def test_register_and_login() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = AuthStore(base_dir=Path(tmp))
        user_id = store.register("alice", "pass1234")
        assert user_id is not None
        user = store.login("alice", "pass1234")
        assert user is not None
        assert user.username == "alice"
        assert user.id == user_id


def test_register_duplicate_username() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = AuthStore(base_dir=Path(tmp))
        assert store.register("bob", "pw") is not None
        assert store.register("bob", "other") is None


def test_login_wrong_password() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = AuthStore(base_dir=Path(tmp))
        store.register("cat", "secret")
        assert store.login("cat", "wrong") is None
        assert store.login("cat", "secret") is not None
