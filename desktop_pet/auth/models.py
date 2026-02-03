"""用户与登录数据模型。"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """用户（账号密码注册）。"""
    id: str = Field(..., description="用户唯一 ID")
    username: str = Field(..., description="登录账号")
    password_hash: str = Field(..., description="密码哈希")
    salt: str = Field(..., description="盐")
    created_at: Optional[str] = Field(None, description="创建时间 ISO")

    model_config = ConfigDict(use_enum_values=True)
