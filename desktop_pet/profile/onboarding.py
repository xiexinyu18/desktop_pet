"""注册后引导：上传猫咪照片 → 生成 AI 形象 → 创建桌宠。"""
import shutil
import uuid
from pathlib import Path
from typing import Optional

from desktop_pet.config import AVATARS_DIR, ensure_dirs
from desktop_pet.profile.models import PetProfile
from desktop_pet.profile.store import ProfileStore


def save_avatar_from_path(user_id: str, source_path: Path) -> Optional[str]:
    """将用户选择的照片保存为头像目录下的文件，返回相对路径或绝对路径（供档案使用）。"""
    ensure_dirs()
    ext = source_path.suffix.lower() or ".png"
    name = f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
    dest = AVATARS_DIR / name
    try:
        shutil.copy2(source_path, dest)
        return str(dest)
    except Exception:
        return None


def create_pet_from_photo(
    user_id: str,
    photo_path: Path,
    pet_name: str,
    profile_store: Optional[ProfileStore] = None,
) -> Optional[PetProfile]:
    """用上传的猫咪照片创建宠物档案（复制照片到头像目录）。"""
    store = profile_store or ProfileStore()
    avatar_path = save_avatar_from_path(user_id, photo_path)
    if not avatar_path:
        return None
    return create_pet_with_avatar(user_id, avatar_path, pet_name, store)


def create_pet_with_avatar(
    user_id: str,
    avatar_path: str,
    pet_name: str,
    profile_store: Optional[ProfileStore] = None,
) -> Optional[PetProfile]:
    """用已有头像路径创建宠物档案（不复制文件，用于即梦生成图等）。"""
    store = profile_store or ProfileStore()
    pet_id = f"pet_{user_id}_{uuid.uuid4().hex[:8]}"
    profile = PetProfile(
        id=pet_id,
        name=pet_name.strip() or "我的小猫",
        species="cat",
        avatar_path=avatar_path,
        owner_id=user_id,
        is_public=True,
    )
    store.save(profile)
    return profile
