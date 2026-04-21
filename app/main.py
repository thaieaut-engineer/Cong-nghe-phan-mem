from __future__ import annotations

import sys

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.theme import apply_theme
from app.core.db import Database
from app.core.db_migrate import ensure_service_images_columns
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.register_service import RegisterService
from app.windows.login_window import LoginWindow
from app.windows.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Billiards Manager")
    apply_theme(app)

    try:
        db = Database()
        ensure_service_images_columns(db)
    except Exception as e:
        QMessageBox.critical(None, "Không kết nối được MySQL", str(e))
        return 1
    users = UserRepository(db)
    auth = AuthService(users)
    register = RegisterService(users)

    while True:
        login = LoginWindow(auth, register)
        if login.exec() != LoginWindow.DialogCode.Accepted or not login.user:
            return 0

        close_result = ["relogin"]
        window = MainWindow(login.user, db, close_result)
        wait_close = QEventLoop()
        window.destroyed.connect(wait_close.quit)
        window.show()
        wait_close.exec()
        if close_result[0] == "quit":
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

