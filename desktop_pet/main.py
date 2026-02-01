"""桌宠入口：启动桌面宠物窗口、摄像头检测与健康提醒。"""
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from desktop_pet import __version__
from desktop_pet.app.window import PetWindow
from desktop_pet.camera.detector import CameraDetector
from desktop_pet.config import CAMERA_DETECT_INTERVAL_MS, ensure_dirs
from desktop_pet.profile.store import ProfileStore


def main() -> None:
    ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("桌宠")
    app.setApplicationVersion(__version__)

    # 宠物窗口（可传入 on_detection 做额外逻辑，如播放音效）
    def on_detection(detected: bool) -> None:
        if detected:
            pass  # 可在此播放「宠物出现」音效等

    window = PetWindow(on_detection=on_detection)
    window.show()

    # 摄像头检测定时器（可选：无摄像头时仅桌面宠物仍可运行）
    detector = CameraDetector(interval_ms=CAMERA_DETECT_INTERVAL_MS)

    def poll_camera() -> None:
        result = detector.detect()
        window.update_detection(result.pet_detected)

    timer = QTimer(window)
    timer.timeout.connect(poll_camera)
    timer.start(CAMERA_DETECT_INTERVAL_MS)

    # 退出时释放摄像头
    def on_quit() -> None:
        detector.release()

    app.aboutToQuit.connect(on_quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
