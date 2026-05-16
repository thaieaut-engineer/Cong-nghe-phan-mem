from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.db import Database  # noqa: E402
from app.core.db_seed import ensure_default_seed  # noqa: E402


def main() -> int:
    db = Database()
    before = db.fetch_one("SELECT id FROM users WHERE username=%s", ("admin",))
    ensure_default_seed(db)
    after = db.fetch_one("SELECT id FROM users WHERE username=%s", ("admin",))
    if after and not before:
        print("Seeded admin user: admin/admin123")
    elif after:
        print("Admin user already exists.")
    else:
        print("Could not seed admin user (missing admin role).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
