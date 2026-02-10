"""即梦图生视频后台 Worker（QThread），在图生图完成后用生成的 AI 图调用图生视频并保存。"""
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from desktop_pet.jimeng.i2v_client import generate_video_from_image


class I2VWorker(QThread):
    """用一张图（通常为图生图生成的 AI 图）生成短视频，保存到指定目录。"""
    finished_success = pyqtSignal(str)  # 视频保存路径
    finished_fail = pyqtSignal(str)     # 错误信息

    def __init__(self, image_path: str | Path, access_key: str, secret_key: str, save_dir: str | Path):
        super().__init__()
        self._image_path = Path(image_path)
        self._access_key = access_key
        self._secret_key = secret_key
        self._save_dir = Path(save_dir)

    def run(self) -> None:
        path = generate_video_from_image(
            self._access_key,
            self._secret_key,
            self._image_path,
            self._save_dir,
        )
        if path is not None:
            self.finished_success.emit(str(path.resolve()))
        else:
            self.finished_fail.emit("图生视频失败或超时")
