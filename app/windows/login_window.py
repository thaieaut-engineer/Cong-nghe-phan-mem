from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.ui import get_child, load_ui
from app.services.auth_service import AuthService
from app.services.register_service import RegisterService


class LoginWindow(QDialog):
    def __init__(self, auth: AuthService, register: RegisterService) -> None:
        super().__init__()
        self._auth = auth
        self._register = register
        self.user: dict | None = None

        self.setWindowTitle("Billiards Manager - Đăng nhập")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._ui: QWidget = load_ui("login.ui", self)
        root.addWidget(self._ui)

        self._line_user = get_child(self._ui, QLineEdit, "lineEditUsername")
        self._line_pass = get_child(self._ui, QLineEdit, "lineEditPassword")
        self._btn_login = get_child(self._ui, QPushButton, "btnLogin")
        self._btn_register = get_child(self._ui, QPushButton, "btnRegister")

        self._line_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._btn_login.clicked.connect(self._on_login)
        self._btn_register.clicked.connect(self._on_register)

    def _on_login(self) -> None:
        username = self._line_user.text().strip()
        password = self._line_pass.text()

        if not username or not password:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ tài khoản và mật khẩu.")
            return

        user = self._auth.login(username, password)
        if not user:
            QMessageBox.critical(self, "Sai thông tin", "Tài khoản hoặc mật khẩu không đúng.")
            return

        self.user = user
        self.setResult(QDialog.DialogCode.Accepted)
        self.accept()

    def _on_register(self) -> None:
        dlg = load_ui("dialog_register.ui", self)
        line_user = get_child(dlg, QLineEdit, "lineUsername")
        line_pass1 = get_child(dlg, QLineEdit, "linePassword")
        line_pass2 = get_child(dlg, QLineEdit, "linePassword2")
        get_child(dlg, QLabel, "labelRole").hide()
        combo_role = get_child(dlg, QWidget, "comboRole")
        combo_role.hide()
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        line_pass1.setEchoMode(QLineEdit.EchoMode.Password)
        line_pass2.setEchoMode(QLineEdit.EchoMode.Password)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            username = line_user.text().strip()
            p1 = line_pass1.text()
            p2 = line_pass2.text()
            if p1 != p2:
                QMessageBox.warning(self, "Sai", "Mật khẩu nhập lại không khớp.")
                return
            try:
                role_id = self._register.get_default_public_role_id()
            except ValueError as e:
                QMessageBox.warning(self, "Cấu hình", str(e))
                return
            try:
                self._register.register(username, p1, role_id)
            except Exception as e:
                QMessageBox.critical(self, "Không tạo được tài khoản", str(e))
                return
            QMessageBox.information(
                self,
                "Thành công",
                "Đã tạo tài khoản với quyền user (nhân viên). Bạn có thể đăng nhập ngay.",
            )
            self._line_user.setText(username)
            self._line_pass.setText("")

