"""宠物档案本地存储。"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from desktop_pet.config import PROFILES_DIR, ensure_dirs
from desktop_pet.profile.models import PetProfile


class ProfileStore:
    """档案存储（JSON 文件，便于 MVP；后续可换 SQLite）。"""
    _index_file = "index.json"

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or PROFILES_DIR
        ensure_dirs()

    def _index_path(self) -> Path:
        return self.base_dir / self._index_file

    def _profile_path(self, pet_id: str) -> Path:
        return self.base_dir / f"{pet_id}.json"

    def list_ids(self) -> List[str]:
        """列出所有宠物 ID。"""
        if not self._index_path().exists():
            return []
        with open(self._index_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ids", [])

    def load(self, pet_id: str) -> Optional[PetProfile]:
        """加载一只宠物档案。"""
        path = self._profile_path(pet_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PetProfile.model_validate(data)

    def save(self, profile: PetProfile) -> None:
        """保存宠物档案并更新索引。"""
        ensure_dirs()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if not profile.created_at:
            profile.created_at = now
        profile.updated_at = now

        path = self._profile_path(profile.id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2, exclude_none=False))

        ids = self.list_ids()
        if profile.id not in ids:
            ids.append(profile.id)
            with open(self._index_path(), "w", encoding="utf-8") as f:
                json.dump({"ids": ids}, f, indent=2, ensure_ascii=False)

    def delete(self, pet_id: str) -> bool:
        """删除档案。"""
        path = self._profile_path(pet_id)
        if not path.exists():
            return False
        path.unlink()
        ids = self.list_ids()
        if pet_id in ids:
            ids.remove(pet_id)
            with open(self._index_path(), "w", encoding="utf-8") as f:
                json.dump({"ids": ids}, f, indent=2, ensure_ascii=False)
        return True

    def list_by_owner(self, owner_id: str) -> List[PetProfile]:
        """列出某用户拥有的宠物（用于登录后加载「我的小猫」）。"""
        out = []
        for pet_id in self.list_ids():
            p = self.load(pet_id)
            if p and (p.owner_id or "") == owner_id:
                out.append(p)
        return out

    def list_public(self) -> List[PetProfile]:
        """列出广场可见的宠物（访客只能看别人的小猫）。"""
        out = []
        for pet_id in self.list_ids():
            p = self.load(pet_id)
            if p and p.is_public:
                out.append(p)
        return out
