from __future__ import annotations

from app.core.security import hash_password
from app.repositories.user_repository import UserRepository


class RegisterService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def register(self, username: str, password: str, role_id: int) -> int:
        username = username.strip()
        if not username:
            raise ValueError("Username không được để trống.")
        if len(password) < 4:
            raise ValueError("Mật khẩu tối thiểu 4 ký tự.")
        if role_id <= 0:
            raise ValueError("Role không hợp lệ.")

        existed = self._users.find_by_username(username)
        if existed:
            raise ValueError("Username đã tồn tại.")

        return self._users.create_user(username, hash_password(password), role_id)

    def list_roles(self) -> list[dict]:
        return self._users.list_roles()

