"""权限管控：主人可联动真实宠物与健康管理，游客仅虚拟互动。"""
from typing import Optional

from desktop_pet.profile.models import PetProfile, UserRole


def get_role_from_profile(profile: Optional[PetProfile], is_owner: bool) -> UserRole:
    """根据「是否主人」与档案返回当前角色。无档案或非主人视为游客。"""
    if profile is None:
        return UserRole.GUEST
    return UserRole.OWNER if is_owner else UserRole.GUEST


class PermissionChecker:
    """功能权限检查。"""

    @staticmethod
    def can_use_camera_and_real_pet(role: UserRole) -> bool:
        """是否允许摄像头检测与真实宠物联动（喂食、逗猫等）。"""
        return role == UserRole.OWNER

    @staticmethod
    def can_manage_health(role: UserRole) -> bool:
        """是否允许健康管理（喂食/梳毛/猫砂提醒、健康档案）。"""
        return role == UserRole.OWNER

    @staticmethod
    def can_edit_profile(role: UserRole) -> bool:
        """是否允许编辑宠物档案。"""
        return role == UserRole.OWNER

    @staticmethod
    def can_virtual_interact(role: UserRole) -> bool:
        """是否允许虚拟互动（拖拽、点击、桌面动效）。所有人均可。"""
        return True
