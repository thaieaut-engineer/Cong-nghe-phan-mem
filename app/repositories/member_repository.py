from __future__ import annotations

from app.core.db import Database


class MemberRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            "SELECT id, code, name, phone, email, discount_percent, total_spent, created_at "
            "FROM members ORDER BY name ASC"
        )

    def search(self, q: str) -> list[dict]:
        like = f"%{q.strip()}%"
        return self._db.fetch_all(
            "SELECT id, code, name, phone, email, discount_percent, total_spent "
            "FROM members WHERE code LIKE %s OR name LIKE %s OR phone LIKE %s "
            "ORDER BY name ASC LIMIT 50",
            (like, like, like),
        )

    def get(self, member_id: int) -> dict | None:
        return self._db.fetch_one(
            "SELECT id, code, name, phone, email, discount_percent, total_spent "
            "FROM members WHERE id=%s",
            (int(member_id),),
        )

    def get_by_code(self, code: str) -> dict | None:
        return self._db.fetch_one(
            "SELECT id, code, name, phone, email, discount_percent, total_spent "
            "FROM members WHERE code=%s",
            (code.strip(),),
        )

    def create(
        self,
        code: str,
        name: str,
        phone: str | None,
        email: str | None,
        discount_percent: float,
    ) -> int:
        return self._db.execute(
            "INSERT INTO members(code, name, phone, email, discount_percent) "
            "VALUES(%s,%s,%s,%s,%s)",
            (code.strip(), name.strip(), (phone or "").strip() or None, (email or "").strip() or None, float(discount_percent)),
        )

    def update(
        self,
        member_id: int,
        code: str,
        name: str,
        phone: str | None,
        email: str | None,
        discount_percent: float,
    ) -> None:
        self._db.execute(
            "UPDATE members SET code=%s, name=%s, phone=%s, email=%s, discount_percent=%s WHERE id=%s",
            (
                code.strip(),
                name.strip(),
                (phone or "").strip() or None,
                (email or "").strip() or None,
                float(discount_percent),
                int(member_id),
            ),
        )

    def delete(self, member_id: int) -> None:
        self._db.execute("DELETE FROM members WHERE id=%s", (int(member_id),))

    def add_spent(self, member_id: int, amount: float) -> None:
        self._db.execute(
            "UPDATE members SET total_spent = total_spent + %s WHERE id=%s",
            (float(amount), int(member_id)),
        )

    # ----- session_members -----
    def assign_to_session(self, session_id: int, member_id: int, discount_percent: float) -> None:
        self._db.execute(
            "REPLACE INTO session_members(session_id, member_id, applied_discount_percent) "
            "VALUES(%s,%s,%s)",
            (int(session_id), int(member_id), float(discount_percent)),
        )

    def unassign_session(self, session_id: int) -> None:
        self._db.execute("DELETE FROM session_members WHERE session_id=%s", (int(session_id),))

    def get_session_member(self, session_id: int) -> dict | None:
        return self._db.fetch_one(
            """
            SELECT sm.session_id, sm.member_id, sm.applied_discount_percent,
                   m.code, m.name, m.phone, m.email
            FROM session_members sm
            JOIN members m ON m.id = sm.member_id
            WHERE sm.session_id=%s
            """.strip(),
            (int(session_id),),
        )
