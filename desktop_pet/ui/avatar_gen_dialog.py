"""宠物形象生成：用即梦服务将上传的宠物照片生成 AI 分身形象。"""
import uuid
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QWidget,
)

from desktop_pet.config import AVATARS_DIR, JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY, ensure_dirs
from desktop_pet.jimeng.client import JimengClient
from desktop_pet.profile.models import PetProfile
from desktop_pet.profile.store import ProfileStore


class JimengWorker(QThread):
    """后台调用即梦图生图，避免阻塞 UI。"""
    finished_success = pyqtSignal(str)  # 新头像路径
    finished_fail = pyqtSignal(str)     # 错误信息

    def __init__(self, image_path: str, access_key: str, secret_key: str):
        super().__init__()
        self._image_path = image_path
        self._access_key = access_key
        self._secret_key = secret_key

    def run(self) -> None:
        try:
            client = JimengClient(self._access_key, self._secret_key)
            out, err = client.image_to_image(self._image_path)
            if out:
                ensure_dirs()
                dest = AVATARS_DIR / f"jimeng_{uuid.uuid4().hex[:12]}.png"
                dest.write_bytes(out)
                self.finished_success.emit(str(dest.resolve()))
            else:
                self.finished_fail.emit(err or "即梦接口返回失败或未返回图片，请检查密钥与网络。")
        except Exception as e:
            self.finished_fail.emit(f"生成异常: {e}")


class AvatarGenDialog(QDialog):
    """用即梦为当前宠物生成 AI 分身形象，生成后可替换桌宠头像。"""
    avatarUpdated = pyqtSignal(str)  # 新 avatar_path，供主窗口更新显示

    def __init__(
        self,
        pet: PetProfile,
        profile_store: Optional[ProfileStore] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._pet = pet
        self._store = profile_store or ProfileStore()
        self._worker: Optional[JimengWorker] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("宠物形象生成（即梦 AI 分身）")
        self.setFixedSize(400, 260)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("使用即梦服务，根据当前宠物照片生成统一风格的 AI 分身形象。"))
        layout.addWidget(QLabel(f"当前宠物：{self._pet.name}"))

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._btn_gen = QPushButton("生成 AI 形象")
        self._btn_gen.setMinimumHeight(40)
        self._btn_gen.clicked.connect(self._on_generate)
        layout.addWidget(self._btn_gen)

        self._label_status = QLabel("")
        layout.addWidget(self._label_status)

    def _on_generate(self) -> None:
        import sys
        print("[桌宠-即梦] 点击了「生成 AI 形象」", file=sys.stderr, flush=True)
        avatar_path = self._pet.avatar_path
        if not avatar_path or not Path(avatar_path).exists():
            QMessageBox.warning(self, "提示", "当前宠物没有可用的头像图片，请先上传照片。")
            return
        if not JIMENG_ACCESS_KEY or not JIMENG_SECRET_KEY:
            QMessageBox.warning(self, "配置缺失", "请设置即梦 Access Key 与 Secret Key（config 或环境变量）。")
            return
        self._btn_gen.setEnabled(False)
        self._progress.setVisible(True)
        self._label_status.setText("正在调用即梦生成…")
        self._worker = JimengWorker(avatar_path, JIMENG_ACCESS_KEY, JIMENG_SECRET_KEY)
        self._worker.finished_success.connect(self._on_success)
        self._worker.finished_fail.connect(self._on_fail)
        self._worker.start()

    def _on_success(self, new_path: str) -> None:
        self._progress.setVisible(False)
        self._btn_gen.setEnabled(True)
        self._label_status.setText("生成成功，已更新桌宠形象。")
        self._pet.avatar_path = new_path
        self._store.save(self._pet)
        # 先发信号让桌宠窗口立即换上新头像并重绘，再弹框、关闭
        new_path_abs = str(Path(new_path).resolve())
        self.avatarUpdated.emit(new_path_abs)
        QMessageBox.information(self, "完成", "AI 分身形象已生成并设为桌宠头像。")
        self.accept()
        # 关闭后把父窗口（桌宠）带到前台，方便用户看到新形象
        parent = self.parent()
        if parent is not None:
            parent.raise_()
            parent.activateWindow()

    def _on_fail(self, err: str) -> None:
        self._progress.setVisible(False)
        self._btn_gen.setEnabled(True)
        self._label_status.setText("生成失败")
        import sys
        print(f"[桌宠-即梦] 生成失败: {err}", file=sys.stderr, flush=True)
        self.raise_()
        self.activateWindow()
        QMessageBox.warning(self, "生成失败", err)
