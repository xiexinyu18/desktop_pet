"""注册后引导：上传猫咪照片 → 生成 AI 形象 → 填写名字，创建桌宠。"""
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
from PyQt6.QtCore import QTimer, Qt

from desktop_pet.auth.models import User
from desktop_pet.profile.models import PetProfile
from desktop_pet.profile.onboarding import create_pet_from_photo
from desktop_pet.profile.store import ProfileStore


class OnboardingDialog(QDialog):
    """上传猫咪照片 → 生成形象（MVP 直接使用照片）→ 输入名字 → 创建宠物。"""

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
        # MVP：直接创建，无真实 AI；用定时器模拟“生成中”
        QTimer.singleShot(800, self._finish_create)

    def _finish_create(self) -> None:
        self._progress.setVisible(False)
        pet = create_pet_from_photo(
            self._user.id,
            self._photo_path,
            self._name_edit.text().strip() or "我的小猫",
            self._store,
        )
        if pet:
            self._pet = pet
            QMessageBox.information(self, "完成", f"桌宠「{pet.name}」已创建！")
            self.accept()
        else:
            QMessageBox.warning(self, "失败", "创建桌宠失败，请重试")
            self._btn_create.setEnabled(True)

    def pet(self) -> Optional[PetProfile]:
        return self._pet
