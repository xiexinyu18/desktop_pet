"""将 MP4 视频转为 GIF，供桌宠窗口播放（避免 QMediaPlayer 内存泄漏）。"""
import subprocess
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from desktop_pet.config import GIFS_DIR, ensure_dirs


def video_path_to_gif_path(video_path: str | Path) -> Path:
    """
    视频路径 -> GIF 路径映射。
    data/videos/xxx.mp4 -> data/gifs/xxx.gif
    """
    video_path = Path(video_path)
    return GIFS_DIR / video_path.with_suffix(".gif").name


def video_to_gif(video_path: str | Path, fps: int = 30, width: int = 320) -> Optional[Path]:
    """
    将 MP4 转为 GIF，保存到 data/gifs/，与视频路径一一映射。
    直接用 ffmpeg 转换，避免 moviepy + NumPy 2.0 的 tostring 兼容性问题。
    返回 GIF 路径，失败返回 None。
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return None
    gif_path = video_path_to_gif_path(video_path)
    ensure_dirs()
    try:
        # 单次 ffmpeg 调用：palettegen + paletteuse 生成高质量 GIF
        # -loop -1 = 播放一次（不循环）
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖已存在文件
            "-i", str(video_path),
            "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            "-loop", "-1",
            str(gif_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not gif_path.exists():
            import sys
            print(f"[桌宠-GIF] ffmpeg 转换失败: {result.stderr or result.stdout}", file=sys.stderr, flush=True)
            return None
        return gif_path
    except FileNotFoundError:
        import sys
        print("[桌宠-GIF] 未找到 ffmpeg，请安装: brew install ffmpeg", file=sys.stderr, flush=True)
        return None
    except subprocess.TimeoutExpired:
        import sys
        print("[桌宠-GIF] 转换超时", file=sys.stderr, flush=True)
        return None
    except Exception as e:
        import sys
        print(f"[桌宠-GIF] 转换失败: {e}", file=sys.stderr, flush=True)
        return None


class VideoToGifWorker(QThread):
    """后台将已有视频转为 GIF，用于已有宠物档案的按需转换。"""
    finished_success = pyqtSignal(str, str, float)  # video_path, gif_path, elapsed_seconds
    finished_fail = pyqtSignal(str)

    def __init__(self, video_path: str | Path, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._video_path = Path(video_path)

    def run(self) -> None:
        if not self._video_path.exists():
            self.finished_fail.emit("视频文件不存在")
            return
        t0 = time.perf_counter()
        gif_path_obj = video_to_gif(self._video_path)
        elapsed = time.perf_counter() - t0
        if gif_path_obj:
            self.finished_success.emit(
                str(self._video_path.resolve()),
                str(gif_path_obj.resolve()),
                elapsed,
            )
        else:
            self.finished_fail.emit("视频转 GIF 失败")
