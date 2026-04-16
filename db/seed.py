from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_db_config  # noqa: E402
from app.core.security import hash_password  # noqa: E402

import mysql.connector  # noqa: E402


def main() -> int:
    cfg = get_db_config()
    conn = mysql.connector.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
    )
    cur = conn.cursor()

    # roles: admin / user (mặc định đăng ký) / staff
    cur.execute("INSERT IGNORE INTO roles(name) VALUES(%s)", ("admin",))
    cur.execute("INSERT IGNORE INTO roles(name) VALUES(%s)", ("user",))
    cur.execute("INSERT IGNORE INTO roles(name) VALUES(%s)", ("staff",))
    conn.commit()

    cur.execute("SELECT id FROM roles WHERE name=%s", ("admin",))
    admin_role_id = int(cur.fetchone()[0])

    # admin user
    cur.execute("SELECT id FROM users WHERE username=%s", ("admin",))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users(username, password, role_id) VALUES(%s,%s,%s)",
            ("admin", hash_password("admin123"), admin_role_id),
        )
        conn.commit()
        print("Seeded admin user: admin/admin123")
    else:
        print("Admin user already exists.")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

