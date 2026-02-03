"""桌宠入口：欢迎（登录/注册/访客）→ 桌宠或广场。"""
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from desktop_pet import __version__
from desktop_pet.app.window import PetWindow
from desktop_pet.camera.detector import CameraDetector
from desktop_pet.config import CAMERA_DETECT_INTERVAL_MS, ensure_dirs
from desktop_pet.auth.store import AuthStore
from desktop_pet.auth.session import Session
from desktop_pet.profile.store import ProfileStore
from desktop_pet.ui.welcome import WelcomeDialog
from desktop_pet.ui.onboarding import OnboardingDialog
from desktop_pet.ui.plaza import PlazaWindow


def main() -> None:
    ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("桌宠")
    app.setApplicationVersion(__version__)

    auth_store = AuthStore()
    profile_store = ProfileStore()

    # 1. 欢迎：登录 / 注册 / 访客
    welcome = WelcomeDialog(auth_store)
    if welcome.exec() != welcome.DialogCode.Accepted:
        sys.exit(0)

    choice = welcome.choice()
    user = welcome.logged_user()

    if choice == "guest":
        # 访客：只打开广场，不能创建小猫
        plaza = PlazaWindow(profile_store, auth_store)
        plaza.show()
        sys.exit(app.exec())
        return

    # 登录或注册成功
    Session.set_current(user)
    if not user:
        sys.exit(0)

    # 2. 检查是否已有桌宠
    my_pets = profile_store.list_by_owner(user.id)
    pet = my_pets[0] if my_pets else None

    if not pet:
        # 首次：引导上传猫咪照片并创建桌宠
        onboarding = OnboardingDialog(user)
        if onboarding.exec() != onboarding.DialogCode.Accepted:
            sys.exit(0)
        pet = onboarding.pet()
    if not pet:
        sys.exit(0)

    # 3. 打开桌宠窗口（使用该宠物的形象）
    def on_detection(detected: bool) -> None:
        if detected:
            pass  # 可在此播放「宠物出现」音效等

    window = PetWindow(avatar_path=pet.avatar_path, on_detection=on_detection)
    window.setWindowTitle(f"桌宠 - {pet.name}")
    window.show()

    detector = CameraDetector(interval_ms=CAMERA_DETECT_INTERVAL_MS)

    def poll_camera() -> None:
        result = detector.detect()
        window.update_detection(result.pet_detected)

    timer = QTimer(window)
    timer.timeout.connect(poll_camera)
    timer.start(CAMERA_DETECT_INTERVAL_MS)

    def on_quit() -> None:
        detector.release()

    app.aboutToQuit.connect(on_quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
