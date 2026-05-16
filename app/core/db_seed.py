from __future__ import annotations

from app.core.db import Database
from app.core.security import hash_password


def ensure_default_seed(db: Database) -> None:
    """Tạo role mặc định và tài khoản admin nếu chưa có."""
    for role_name in ("admin", "user", "staff"):
        db.execute("INSERT IGNORE INTO roles(name) VALUES(%s)", (role_name,))

    admin_role = db.fetch_one("SELECT id FROM roles WHERE name=%s", ("admin",))
    if not admin_role:
        return

    existing = db.fetch_one("SELECT id FROM users WHERE username=%s", ("admin",))
    if existing:
        return

    db.execute(
        "INSERT INTO users(username, password, role_id) VALUES(%s, %s, %s)",
        ("admin", hash_password("admin123"), int(admin_role["id"])),
    )
