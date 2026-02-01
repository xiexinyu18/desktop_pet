"""宠物状态与动效逻辑（眼睛一亮、待机等）。"""
from enum import Enum
from typing import Optional


class PetState(str, Enum):
    """宠物当前状态，用于切换动效。"""
    IDLE = "idle"           # 自然待机
    EYES_LIT = "eyes_lit"   # 检测到宠物，眼睛一亮
    DRAGGED = "dragged"     # 被拖拽
    INTERACT = "interact"   # 与用户互动（点击等）


def next_state_on_detection(current: PetState, pet_detected: bool) -> PetState:
    """根据摄像头是否检测到宠物更新状态。"""
    if pet_detected:
        return PetState.EYES_LIT
    if current == PetState.EYES_LIT:
        return PetState.IDLE
    return current
