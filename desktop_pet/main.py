"""桌宠入口：欢迎（登录/注册/访客）→ 桌宠或广场；各界面可返回欢迎页切换模式。"""
import sys

from PyQt6.QtCore import QTimer, QEventLoop
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
from desktop_pet.ui.voice_record import VoiceRecordDialog
from desktop_pet.voice.store import VoiceProfileStore
from desktop_pet.voice.tts import TTSEngine


def main() -> None:
    ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("桌宠")
    app.setApplicationVersion(__version__)

    auth_store = AuthStore()
    profile_store = ProfileStore()

    while True:
        # 1. 欢迎：登录 / 注册 / 访客 / 退出
        welcome = WelcomeDialog(auth_store)
        if welcome.exec() != welcome.DialogCode.Accepted:
            break

        choice = welcome.choice()
        user = welcome.logged_user()

        if choice == "guest":
            # 访客：只打开广场；可点「返回欢迎页」回到这里
            plaza = PlazaWindow(profile_store, auth_store)
            loop = QEventLoop()
            plaza.returnToWelcomeRequested.connect(loop.quit)
            plaza.show()
            loop.exec()
            continue

        # 登录或注册成功
        Session.set_current(user)
        if not user:
            continue

        # 2. 检查是否已有桌宠
        my_pets = profile_store.list_by_owner(user.id)
        pet = my_pets[0] if my_pets else None

        if not pet:
            # 首次：引导上传猫咪照片并创建桌宠；可点「返回」回到欢迎页
            onboarding = OnboardingDialog(user)
            if onboarding.exec() != onboarding.DialogCode.Accepted:
                continue
            pet = onboarding.pet()
        if not pet:
            continue

        # 2.5 可选：录入主人声音（用于后续模拟主人声线、TTS 与宠物对话）
        voice_store = VoiceProfileStore()
        if not voice_store.has_voice(user.id):
            voice_dlg = VoiceRecordDialog(user, voice_store)
            voice_dlg.exec()  # 可点「暂不录入」跳过

        # 3. 打开桌宠窗口（右上角「≡」返回欢迎页，「说」打开与宠物说话）
        def on_detection(detected: bool) -> None:
            if detected:
                pass  # 可在此播放「宠物出现」音效等

        tts_engine = TTSEngine(voice_store)
        window = PetWindow(
            avatar_path=pet.avatar_path,
            on_detection=on_detection,
            tts_engine=tts_engine,
            user_id=user.id,
            pet=pet,
            profile_store=profile_store,
        )
        window.setWindowTitle(f"桌宠 - {pet.name}")

        detector = CameraDetector(interval_ms=CAMERA_DETECT_INTERVAL_MS)
        timer = QTimer(window)
        timer.timeout.connect(lambda: window.update_detection(detector.detect().pet_detected))
        timer.start(CAMERA_DETECT_INTERVAL_MS)

        loop = QEventLoop()
        def on_return() -> None:
            timer.stop()
            detector.release()
            window.close()
            loop.quit()
        window.returnToWelcomeRequested.connect(on_return)

        window.show()
        loop.exec()
        # 用户点了返回欢迎页，继续下一轮循环

    sys.exit(0)


if __name__ == "__main__":
    main()
