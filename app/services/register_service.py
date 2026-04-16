from __future__ import annotations

from app.core.permissions import ROLE_ADMIN, ROLE_STAFF, ROLE_USER, normalize_role
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository


class RegisterService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def register(self, username: str, password: str, role_id: int, *, allow_admin_role: bool = False) -> int:
        username = username.strip()
        if not username:
            raise ValueError("Username không được để trống.")
        if len(password) < 4:
            raise ValueError("Mật khẩu tối thiểu 4 ký tự.")
        if role_id <= 0:
            raise ValueError("Role không hợp lệ.")

        role = self._users.get_role_by_id(role_id)
        if role and normalize_role(role.get("name")) == ROLE_ADMIN and not allow_admin_role:
            raise ValueError("Không thể tạo tài khoản admin từ màn hình đăng ký công khai.")

        existed = self._users.find_by_username(username)
        if existed:
            raise ValueError("Username đã tồn tại.")

        return self._users.create_user(username, hash_password(password), role_id)

    def list_roles(self) -> list[dict]:
        return self._users.list_roles()

    def list_roles_for_public_registration(self) -> list[dict]:
        """Đăng ký tại login: không hiển thị admin. Ưu tiên role `user` đứng đầu (mặc định)."""
        roles = [r for r in self._users.list_roles() if normalize_role(r.get("name")) != ROLE_ADMIN]

        def sort_key(r: dict) -> tuple[int, int]:
            n = normalize_role(r.get("name"))
            if n == ROLE_USER:
                return (0, int(r["id"]))
            if n == ROLE_STAFF:
                return (1, int(r["id"]))
            return (2, int(r["id"]))

        return sorted(roles, key=sort_key)

    def get_default_public_role_id(self) -> int:
        """
        Đăng ký công khai: không cần chọn — luôn gán role `user` nếu có trong DB,
        nếu chưa có thì lấy role đầu tiên (không phải admin).
        """
        roles = self.list_roles_for_public_registration()
        for r in roles:
            if normalize_role(r.get("name")) == ROLE_USER:
                return int(r["id"])
        if roles:
            return int(roles[0]["id"])
        raise ValueError(
            "Chưa có role trong CSDL. Chạy: python db/seed.py "
            "(cần ít nhất role user hoặc staff)."
        )

