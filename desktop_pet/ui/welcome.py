"""欢迎界面：登录 / 注册 / 访客进入。"""
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QMessageBox,
)

from desktop_pet.ui.login import LoginDialog
from desktop_pet.ui.register import RegisterDialog
from desktop_pet.auth.session import Session
from desktop_pet.auth.store import AuthStore
from desktop_pet.auth.models import User


class WelcomeDialog(QDialog):
    """入口：选择登录、注册或访客。"""

    def __init__(self, auth_store: Optional[AuthStore] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._auth_store = auth_store or AuthStore()
        self._logged_user: Optional[User] = None
        self._choice: str = ""  # "login" | "register" | "guest"
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("桌宠 - 欢迎")
        self.setFixedSize(360, 280)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("🐱 桌宠")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("选择方式进入")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

    def choice(self) -> str:
        return self._choice

    def logged_user(self) -> Optional[User]:
        return self._logged_user
