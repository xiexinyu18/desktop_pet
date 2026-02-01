"""健康提醒与记录数据模型。"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReminderType(str, Enum):
    """提醒类型。"""
    FEED = "feed"       # 喂食
    GROOM = "groom"     # 梳毛
    LITTER = "litter"   # 猫砂/狗窝清理


class HealthReminder(BaseModel):
    """单条提醒配置与上次执行时间。"""
    pet_id: str = Field(..., description="宠物 ID")
    reminder_type: ReminderType = Field(..., description="提醒类型")
    interval_minutes: int = Field(..., gt=0, description="间隔分钟")
    last_done_at: Optional[datetime] = Field(None, description="上次完成时间 ISO")
    next_at: Optional[datetime] = Field(None, description="下次提醒时间")
    enabled: bool = Field(True, description="是否启用")

    model_config = ConfigDict(use_enum_values=True)
