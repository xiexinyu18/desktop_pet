"""宠物档案与用户角色数据模型。"""
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """用户角色：主人拥有完整功能，游客仅虚拟互动。"""
    OWNER = "owner"   # 宠物主人
    GUEST = "guest"   # 游客


class PetProfile(BaseModel):
    """宠物档案（基础）。"""
    id: str = Field(..., description="宠物唯一 ID")
    name: str = Field(..., description="宠物名字")
    species: str = Field(default="cat", description="物种，如 cat / dog")
    breed: Optional[str] = Field(None, description="品种")
    virtual_birthday: Optional[date] = Field(None, description="虚拟生日")
    weight_kg: Optional[float] = Field(None, description="体重 kg")
    avatar_path: Optional[str] = Field(None, description="头像/形象路径（上传照片或 AI 生成）")
    owner_id: Optional[str] = Field(None, description="主人用户 ID；无则视为本地旧数据")
    is_public: bool = Field(True, description="是否在广场展示")
    created_at: Optional[str] = Field(None, description="创建时间 ISO")
    updated_at: Optional[str] = Field(None, description="更新时间 ISO")

    model_config = ConfigDict(use_enum_values=True)
