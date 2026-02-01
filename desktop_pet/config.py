"""桌宠全局配置与路径。"""
from pathlib import Path

# 项目根目录（desktop_pet 包所在目录的上一级）
ROOT_DIR = Path(__file__).resolve().parent.parent
# 数据目录：档案、相册、健康记录等
DATA_DIR = ROOT_DIR / "data"
PROFILES_DIR = DATA_DIR / "profiles"
ALBUMS_DIR = DATA_DIR / "albums"
HEALTH_DATA_DIR = DATA_DIR / "health"

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
    for d in (DATA_DIR, PROFILES_DIR, ALBUMS_DIR, HEALTH_DATA_DIR):
        d.mkdir(parents=True, exist_ok=True)
