from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.db import Database
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.register_service import RegisterService
from app.windows.login_window import LoginWindow
from app.windows.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Billiards Manager")

    try:
        db = Database()
    except Exception as e:
        QMessageBox.critical(None, "Không kết nối được MySQL", str(e))
        return 1
    users = UserRepository(db)
    auth = AuthService(users)
    register = RegisterService(users)

    login = LoginWindow(auth, register)
    if login.exec() != LoginWindow.DialogCode.Accepted or not login.user:
        return 0

    window = MainWindow(login.user, db)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

