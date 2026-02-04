"""桌宠全局配置与路径。"""
from pathlib import Path

# 项目根目录（desktop_pet 包所在目录的上一级）
ROOT_DIR = Path(__file__).resolve().parent.parent
# 数据目录：档案、相册、健康记录等
DATA_DIR = ROOT_DIR / "data"
PROFILES_DIR = DATA_DIR / "profiles"
ALBUMS_DIR = DATA_DIR / "albums"
HEALTH_DATA_DIR = DATA_DIR / "health"
AUTH_DATA_DIR = DATA_DIR / "auth"  # 用户与登录
AVATARS_DIR = DATA_DIR / "avatars"  # 用户上传/生成的猫咪形象
VOICE_DATA_DIR = DATA_DIR / "voice"  # 主人声音样本（供后续克隆/TTS）
VOICE_SAMPLES_DIR = VOICE_DATA_DIR / "samples"  # 按用户 ID 存录音

# 窗口默认
WINDOW_WIDTH = 200
WINDOW_HEIGHT = 200
WINDOW_FRAMELESS = True
WINDOW_ALWAYS_ON_TOP = True

# 摄像头（可选）
CAMERA_INDEX = 0
CAMERA_DETECT_INTERVAL_MS = 500

# 提醒默认（分钟）
FEED_REMIND_INTERVAL = 360  # 6 小时
GROOM_REMIND_INTERVAL = 10080  # 7 天
LITTER_REMIND_INTERVAL = 1440  # 1 天


def ensure_dirs() -> None:
    """确保数据目录存在。"""
    for d in (DATA_DIR, PROFILES_DIR, ALBUMS_DIR, HEALTH_DATA_DIR, AUTH_DATA_DIR, AVATARS_DIR, VOICE_DATA_DIR, VOICE_SAMPLES_DIR):
        d.mkdir(parents=True, exist_ok=True)
