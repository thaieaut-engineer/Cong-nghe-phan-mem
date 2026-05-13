from __future__ import annotations

from app.core.db import Database


class ShiftHandoverRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self, limit: int = 200) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT h.id, h.handover_time, h.cash_amount, h.note,
                   uf.username AS from_user, ut.username AS to_user
            FROM shift_handovers h
            LEFT JOIN users uf ON uf.id = h.from_user_id
            LEFT JOIN users ut ON ut.id = h.to_user_id
            ORDER BY h.handover_time DESC, h.id DESC
            LIMIT %s
            """.strip(),
            (int(limit),),
        )

    def create(
        self,
        from_user_id: int | None,
        to_user_id: int | None,
        cash_amount: float,
        note: str | None,
    ) -> int:
        return self._db.execute(
            "INSERT INTO shift_handovers(from_user_id, to_user_id, cash_amount, note) "
            "VALUES(%s,%s,%s,%s)",
            (
                (int(from_user_id) if from_user_id else None),
                (int(to_user_id) if to_user_id else None),
                float(cash_amount),
                note,
            ),
        )
