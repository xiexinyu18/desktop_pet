"""注册对话框：账号、密码、确认密码。"""
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QMessageBox,
    QWidget,
)

from desktop_pet.auth.store import AuthStore
from desktop_pet.auth.models import User
from desktop_pet.auth.session import Session


class RegisterDialog(QDialog):
    """注册：账号、密码、确认密码；成功后创建用户并设置 Session。"""

    def __init__(self, auth_store: AuthStore, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._auth_store = auth_store
        self._user: Optional[User] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("注册")
        self.setFixedSize(320, 220)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._username = QLineEdit()
        self._username.setPlaceholderText("请输入账号（用于登录）")
        form.addRow("账号:", self._username)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("请输入密码")
        form.addRow("密码:", self._password)
        self._password2 = QLineEdit()
        self._password2.setEchoMode(QLineEdit.EchoMode.Password)
        self._password2.setPlaceholderText("再次输入密码")
        form.addRow("确认密码:", self._password2)
        layout.addLayout(form)

        btn_register = QPushButton("注册")
        btn_register.clicked.connect(self._do_register)
        layout.addWidget(btn_register)
        btn_back = QPushButton("返回")
        btn_back.clicked.connect(self.reject)
        layout.addWidget(btn_back)

    def _do_register(self) -> None:
        username = self._username.text().strip()
        password = self._password.text()
        password2 = self._password2.text()
        if not username:
            QMessageBox.warning(self, "提示", "请输入账号")
            return
        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return
        if password != password2:
            QMessageBox.warning(self, "提示", "两次密码不一致")
            return
        if len(password) < 4:
            QMessageBox.warning(self, "提示", "密码至少 4 位")
            return
        user_id = self._auth_store.register(username, password)
        if not user_id:
            QMessageBox.warning(self, "注册失败", "该账号已被注册")
            return
        user = self._auth_store.get_user(user_id)
        if user:
            self._user = user
            Session.set_current(user)
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "注册成功但无法加载用户，请重新登录")

    def user(self) -> Optional[User]:
        return self._user
