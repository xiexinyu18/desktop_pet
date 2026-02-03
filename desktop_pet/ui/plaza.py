"""广场：展示别人的小猫（访客只能看广场，不能创建）。"""
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QGridLayout,
    QFrame,
)

from desktop_pet.profile.models import PetProfile
from desktop_pet.profile.store import ProfileStore
from desktop_pet.auth.store import AuthStore


class PlazaWindow(QWidget):
    """广场窗口：以网格展示所有公开的桌宠（别人的小猫）。"""

    def __init__(
        self,
        profile_store: Optional[ProfileStore] = None,
        auth_store: Optional[AuthStore] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._profile_store = profile_store or ProfileStore()
        self._auth_store = auth_store or AuthStore()
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("广场 - 看看别人的小猫")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)

        title = QLabel("🐱 广场 - 别人的小猫")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("访客只能在这里浏览，无法创建自己的小猫。登录/注册后可拥有自己的桌宠。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        self._grid = QGridLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._refresh()

    def _refresh(self) -> None:
        """清空网格并重新加载公开宠物列表。"""
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        pets = self._profile_store.list_public()
        if not pets:
            no_label = QLabel("广场里还没有小猫，快去注册并上传你的猫咪吧～")
            no_label.setStyleSheet("color: gray; padding: 20px;")
            self._grid.addWidget(no_label, 0, 0)
            return
        cols = 3
        for i, pet in enumerate(pets):
            row, col = i // cols, i % cols
            card = self._make_card(pet)
            self._grid.addWidget(card, row, col)

    def _make_card(self, pet: PetProfile) -> QFrame:
        """单个宠物卡片：头像 + 名字。"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("QFrame { background: #f5f5f5; border-radius: 8px; padding: 8px; }")
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 头像：有 avatar_path 则尝试加载，否则占位
        pixmap: Optional[QPixmap] = None
        if pet.avatar_path and Path(pet.avatar_path).exists():
            pixmap = QPixmap(pet.avatar_path)
        if pixmap is None or pixmap.isNull():
            label_img = QLabel("🐱")
            label_img.setStyleSheet("font-size: 48px;")
            label_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_img.setFixedSize(80, 80)
            layout.addWidget(label_img)
        else:
            label_img = QLabel()
            scaled = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            label_img.setPixmap(scaled)
            label_img.setFixedSize(80, 80)
            label_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label_img)

        name = QLabel(pet.name or "未命名")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        layout.addWidget(name)
        return frame
