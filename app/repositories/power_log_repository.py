from __future__ import annotations

from app.core.db import Database


class PowerLogRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def log(
        self,
        table_id: int,
        action: str,
        user_id: int | None = None,
        note: str | None = None,
    ) -> int:
        if action not in ("on", "off"):
            raise ValueError("action phải là 'on' hoặc 'off'")
        return self._db.execute(
            "INSERT INTO power_logs(table_id, action, user_id, note) VALUES(%s,%s,%s,%s)",
            (int(table_id), action, (int(user_id) if user_id else None), note),
        )

    def list_for_table(self, table_id: int, limit: int = 200) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT pl.id, pl.action, pl.action_time, pl.note,
                   u.username AS user_name, t.name AS table_name
            FROM power_logs pl
            LEFT JOIN users u ON u.id = pl.user_id
            LEFT JOIN tables t ON t.id = pl.table_id
            WHERE pl.table_id=%s
            ORDER BY pl.action_time DESC, pl.id DESC
            LIMIT %s
            """.strip(),
            (int(table_id), int(limit)),
        )

    def list_recent(self, limit: int = 200) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT pl.id, pl.action, pl.action_time, pl.note,
                   u.username AS user_name, t.name AS table_name
            FROM power_logs pl
            LEFT JOIN users u ON u.id = pl.user_id
            LEFT JOIN tables t ON t.id = pl.table_id
            ORDER BY pl.action_time DESC, pl.id DESC
            LIMIT %s
            """.strip(),
            (int(limit),),
        )
