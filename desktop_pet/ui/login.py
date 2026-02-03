"""登录对话框：账号、密码。"""
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QMessageBox,
    QWidget,
)
from PyQt6.QtCore import Qt

from desktop_pet.auth.store import AuthStore
from desktop_pet.auth.models import User
from desktop_pet.auth.session import Session


class LoginDialog(QDialog):
    """登录：输入账号密码，验证通过后设置 Session。"""

    def __init__(self, auth_store: AuthStore, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._auth_store = auth_store
        self._user: Optional[User] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("登录")
        self.setFixedSize(320, 180)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._username = QLineEdit()
        self._username.setPlaceholderText("请输入账号")
        form.addRow("账号:", self._username)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("请输入密码")
        form.addRow("密码:", self._password)
        layout.addLayout(form)

        btn_login = QPushButton("登录")
        btn_login.clicked.connect(self._do_login)
        layout.addWidget(btn_login)
        btn_back = QPushButton("返回")
        btn_back.clicked.connect(self.reject)
        layout.addWidget(btn_back)

    def _do_login(self) -> None:
        username = self._username.text().strip()
        password = self._password.text()
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入账号和密码")
            return
        user = self._auth_store.login(username, password)
        if not user:
            QMessageBox.warning(self, "登录失败", "账号或密码错误")
            return
        self._user = user
        Session.set_current(user)
        self.accept()

    def user(self) -> Optional[User]:
        return self._user
