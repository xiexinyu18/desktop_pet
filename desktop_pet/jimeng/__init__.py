"""即梦（火山引擎）图生图服务：用上传的宠物照片生成 AI 分身形象。"""
from desktop_pet.jimeng.client import JimengClient
from desktop_pet.jimeng.prompt import JIMENG_AVATAR_PROMPT

__all__ = ["JimengClient", "JIMENG_AVATAR_PROMPT"]
