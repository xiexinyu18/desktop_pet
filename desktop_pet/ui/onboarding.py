"""注册后引导：上传猫咪照片 → 生成 AI 形象（即梦）→ 填写名字，创建桌宠。"""
import uuid
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QWidget,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from desktop_pet.auth.models import User
from desktop_pet.config import AVATARS_DIR, JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY, VIDEOS_DIR, ensure_dirs
from desktop_pet.profile.models import PetProfile
from desktop_pet.profile.onboarding import create_pet_from_photo, create_pet_with_avatar
from desktop_pet.profile.store import ProfileStore

try:
    from desktop_pet.jimeng.client import JimengClient
    from desktop_pet.jimeng.i2v_worker import I2VWorker
    _HAS_JIMENG = True
except Exception as e:
    import sys
    print(f"[桌宠-引导] 即梦模块导入失败: {e}", file=sys.stderr, flush=True)
    _HAS_JIMENG = False
    I2VWorker = None


class JimengOnboardingWorker(QThread):
    """创建桌宠时在后台调用即梦生成 AI 形象。"""
    finished_success = pyqtSignal(str)   # 生成图保存路径
    finished_fail = pyqtSignal(str)      # 错误信息

    def __init__(self, photo_path: Path, access_key: str, secret_key: str):
        super().__init__()
        self._photo_path = photo_path
        self._access_key = access_key
        self._secret_key = secret_key

    def run(self) -> None:
        try:
            client = JimengClient(self._access_key, self._secret_key)
            out, err = client.image_to_image(self._photo_path)
            if out:
                ensure_dirs()
                dest = AVATARS_DIR / f"jimeng_{uuid.uuid4().hex[:12]}.png"
                dest.write_bytes(out)
                self.finished_success.emit(str(dest.resolve()))
            else:
                self.finished_fail.emit(err or "即梦未返回图片")
        except Exception as e:
            self.finished_fail.emit(f"生成异常: {e}")


class OnboardingDialog(QDialog):
    """上传猫咪照片 → 点击「生成桌宠」调即梦生成 AI 形象 → 输入名字 → 创建宠物。"""

    def __init__(self, user: User, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._user = user
        self._photo_path: Optional[Path] = None
        self._pet: Optional[PetProfile] = None
        self._store = ProfileStore()
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("创建你的桌宠")
        self.setFixedSize(400, 320)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("🐱 上传一张猫咪的照片，我们将为你生成桌宠形象"))
        self._btn_upload = QPushButton("选择猫咪照片")
        self._btn_upload.clicked.connect(self._choose_photo)
        layout.addWidget(self._btn_upload)

        self._label_photo = QLabel("尚未选择照片")
        self._label_photo.setWordWrap(True)
        layout.addWidget(self._label_photo)

        layout.addWidget(QLabel("为你的小猫取个名字："))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如：喵喵、小白")
        layout.addWidget(self._name_edit)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)  # 不确定进度
        layout.addWidget(self._progress)

        self._btn_create = QPushButton("生成桌宠")
        self._btn_create.setEnabled(False)
        self._btn_create.clicked.connect(self._create_pet)
        layout.addWidget(self._btn_create)
        btn_back = QPushButton("返回")
        btn_back.clicked.connect(self.reject)
        layout.addWidget(btn_back)

    def _choose_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择猫咪照片",
            "",
            "图片 (*.png *.jpg *.jpeg *.gif *.bmp)",
        )
        if path:
            self._photo_path = Path(path)
            self._label_photo.setText(f"已选择：{self._photo_path.name}")
            self._btn_create.setEnabled(True)

    def _create_pet(self) -> None:
        if not self._photo_path or not self._photo_path.exists():
            QMessageBox.warning(self, "提示", "请先选择一张照片")
            return
        name = self._name_edit.text().strip() or "我的小猫"
        self._btn_create.setEnabled(False)
        self._progress.setVisible(True)
        self._label_photo.setText("正在生成桌宠形象…")
        # 调试：打印即梦状态
        import sys
        print(f"[桌宠-引导] 点击「生成桌宠」", file=sys.stderr, flush=True)
        print(f"[桌宠-引导] _HAS_JIMENG={_HAS_JIMENG}, JIMENG_ACCESS_KEY={'有' if JIMENG_ACCESS_KEY else '无'}, JIMENG_SECRET_KEY={'有' if JIMENG_SECRET_KEY else '无'}", file=sys.stderr, flush=True)
        # 有即梦且已配置密钥：先调即梦生成 AI 形象，再创建桌宠
        if _HAS_JIMENG and JIMENG_ACCESS_KEY and JIMENG_SECRET_KEY:
            print("[桌宠-引导] 开始调用即梦生成 AI 形象...", file=sys.stderr, flush=True)
            self._worker = JimengOnboardingWorker(
                self._photo_path, JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY
            )
            self._worker.finished_success.connect(self._on_jimeng_success)
            self._worker.finished_fail.connect(self._on_jimeng_fail)
            self._worker.start()
        else:
            # 无即梦或未配置：直接用原图创建
            reason = []
            if not _HAS_JIMENG:
                reason.append("即梦模块未导入")
            if not JIMENG_ACCESS_KEY:
                reason.append("未配置 ACCESS_KEY")
            if not JIMENG_SECRET_KEY:
                reason.append("未配置 SECRET_KEY")
            print(f"[桌宠-引导] 跳过即梦，原因: {', '.join(reason)}，将用原图创建", file=sys.stderr, flush=True)
            self._finish_create_with_photo()

    def _on_jimeng_success(self, avatar_path: str) -> None:
        import sys
        print(f"[桌宠-引导] 即梦生成成功，头像路径: {avatar_path}", file=sys.stderr, flush=True)
        self._progress.setVisible(False)
        self._btn_create.setEnabled(True)
        self._label_photo.setText("已选择：" + self._photo_path.name)
        pet = create_pet_with_avatar(
            self._user.id,
            avatar_path,
            self._name_edit.text().strip() or "我的小猫",
            self._store,
        )
        if pet:
            self._pet = pet
            QMessageBox.information(
                self,
                "完成",
                "桌宠「" + pet.name + "」已创建！（已使用即梦 AI 形象）\n正在后台生成短视频，完成后会提示。",
            )
            self.accept()
            # 图生图完成后直接调用图生视频，用生成的 AI 图做首尾帧，保存到专用目录
            if I2VWorker is not None and JIMENG_ACCESS_KEY and JIMENG_SECRET_KEY:
                ensure_dirs()
                self._i2v_worker = I2VWorker(
                    avatar_path, JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY, VIDEOS_DIR
                )
                self._i2v_worker.finished_success.connect(self._on_i2v_success)
                self._i2v_worker.finished_fail.connect(self._on_i2v_fail)
                self._i2v_worker.start()
        else:
            QMessageBox.warning(self, "失败", "创建桌宠失败，请重试")
            self._btn_create.setEnabled(True)

    def _on_i2v_success(self, video_path: str) -> None:
        QMessageBox.information(None, "短视频", f"已保存至：\n{video_path}")

    def _on_i2v_fail(self, err: str) -> None:
        QMessageBox.warning(None, "短视频生成未完成", err)

    def _on_jimeng_fail(self, err: str) -> None:
        import sys
        print(f"[桌宠-引导] 即梦生成失败: {err}", file=sys.stderr, flush=True)
        self._progress.setVisible(False)
        self._btn_create.setEnabled(True)
        self._label_photo.setText("已选择：" + self._photo_path.name)
        # 即梦失败则用原图创建
        QMessageBox.warning(
            self,
            "AI 形象生成未成功",
            f"即梦生成失败，将使用原图创建桌宠。\n\n{err}",
        )
        self._finish_create_with_photo()

    def _finish_create_with_photo(self) -> None:
        """用原图创建桌宠（即梦未用或失败时的回退）。"""
        import sys
        print("[桌宠-引导] 使用原图创建桌宠", file=sys.stderr, flush=True)
        self._progress.setVisible(True)
        self._label_photo.setText("正在创建桌宠…")
        pet = create_pet_from_photo(
            self._user.id,
            self._photo_path,
            self._name_edit.text().strip() or "我的小猫",
            self._store,
        )
        self._progress.setVisible(False)
        self._btn_create.setEnabled(True)
        self._label_photo.setText("已选择：" + self._photo_path.name)
        if pet:
            self._pet = pet
            QMessageBox.information(self, "完成", f"桌宠「{pet.name}」已创建！")
            self.accept()
        else:
            QMessageBox.warning(self, "失败", "创建桌宠失败，请重试")

    def pet(self) -> Optional[PetProfile]:
        return self._pet
