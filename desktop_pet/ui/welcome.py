"""欢迎界面：登录 / 注册 / 访客进入。"""
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from desktop_pet.config import ROOT_DIR
from desktop_pet.ui.login import LoginDialog
from desktop_pet.ui.register import RegisterDialog
from desktop_pet.auth.session import Session
from desktop_pet.auth.store import AuthStore
from desktop_pet.auth.models import User

# 欢迎页背景图路径
WELCOME_BG_PATH = ROOT_DIR / "assets" / "welcome_bg.png"


class WelcomeDialog(QDialog):
    """入口：选择登录、注册或访客。"""

    def __init__(self, auth_store: Optional[AuthStore] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._auth_store = auth_store or AuthStore()
        self._logged_user: Optional[User] = None
        self._choice: str = ""  # "login" | "register" | "guest"
        self._bg_pixmap: Optional[QPixmap] = None
        if WELCOME_BG_PATH.exists():
            self._bg_pixmap = QPixmap(str(WELCOME_BG_PATH))
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("桌宠 - 欢迎")
        self.setFixedSize(420, 380)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 按钮与文字样式（背景图在 paintEvent 中绘制，避免 Qt 样式表 url 路径问题）
        self.setStyleSheet("""
            QLabel {
                color: #2c1810;
                background: transparent;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px;
                color: #333;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.98);
            }
        """)

        title = QLabel("🐱 桌宠")
        title.setStyleSheet("font-size: 24px; font-weight: bold; background: transparent; color: #2c1810;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("选择方式进入")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("background: transparent; color: #3d2817;")
        layout.addWidget(subtitle)

        btn_login = QPushButton("登录")
        btn_login.setMinimumHeight(40)
        btn_login.clicked.connect(self._on_login)
        layout.addWidget(btn_login)

        btn_register = QPushButton("注册")
        btn_register.setMinimumHeight(40)
        btn_register.clicked.connect(self._on_register)
        layout.addWidget(btn_register)

        btn_guest = QPushButton("访客进入（仅逛广场）")
        btn_guest.setMinimumHeight(40)
        btn_guest.clicked.connect(self._on_guest)
        layout.addWidget(btn_guest)

        btn_quit = QPushButton("退出")
        btn_quit.setMinimumHeight(36)
        btn_quit.clicked.connect(self.reject)
        layout.addWidget(btn_quit)

    def _on_login(self) -> None:
        dlg = LoginDialog(self._auth_store, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._logged_user = dlg.user()
            self._choice = "login"
            self.accept()

    def _on_register(self) -> None:
        dlg = RegisterDialog(self._auth_store, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._logged_user = dlg.user()
            self._choice = "register"
            self.accept()

    def _on_guest(self) -> None:
        Session.set_current(None)
        self._logged_user = None
        self._choice = "guest"
        self.accept()

    def paintEvent(self, event) -> None:
        """先绘制背景图（小王子星空，按比例铺满并居中），再绘制控件。"""
        if self._bg_pixmap and not self._bg_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            scaled = self._bg_pixmap.scaled(
                self.width(), self.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = (scaled.width() - self.width()) // 2
            sy = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, sx, sy, self.width(), self.height())
            painter.end()
        super().paintEvent(event)

    def choice(self) -> str:
        return self._choice

    def logged_user(self) -> Optional[User]:
        return self._logged_user
