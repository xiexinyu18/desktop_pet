"""宠物档案与权限测试。"""
import tempfile
from pathlib import Path

import pytest

from desktop_pet.profile.models import PetProfile, UserRole
from desktop_pet.profile.permission import PermissionChecker, get_role_from_profile
from desktop_pet.profile.store import ProfileStore


def test_get_role_from_profile() -> None:
    profile = PetProfile(id="p1", name="喵喵", species="cat")
    assert get_role_from_profile(profile, is_owner=True) == UserRole.OWNER
    assert get_role_from_profile(profile, is_owner=False) == UserRole.GUEST
    assert get_role_from_profile(None, is_owner=True) == UserRole.GUEST


def test_permission_checker() -> None:
    assert PermissionChecker.can_use_camera_and_real_pet(UserRole.OWNER) is True
    assert PermissionChecker.can_use_camera_and_real_pet(UserRole.GUEST) is False
    assert PermissionChecker.can_manage_health(UserRole.OWNER) is True
    assert PermissionChecker.can_virtual_interact(UserRole.GUEST) is True


def test_profile_store_save_load() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        store = ProfileStore(base_dir=base)
        profile = PetProfile(id="test-cat", name="小白", species="cat", breed="橘猫")
        store.save(profile)
        assert profile.id in store.list_ids()
        loaded = store.load(profile.id)
        assert loaded is not None
        assert loaded.name == profile.name
        assert loaded.species == profile.species
