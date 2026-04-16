from __future__ import annotations

from app.core.security import verify_password
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def login(self, username: str, password: str) -> dict | None:
        user = self._users.find_by_username(username.strip())
        if not user:
            return None
        if not verify_password(password, user["password"]):
            return None
        return user

