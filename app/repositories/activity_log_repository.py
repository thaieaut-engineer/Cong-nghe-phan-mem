from __future__ import annotations

from app.core.db import Database


class ActivityLogRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def log(
        self,
        user_id: int | None,
        username: str | None,
        action: str,
        target_type: str | None = None,
        target_id: int | None = None,
        detail: str | None = None,
    ) -> int:
        return self._db.execute(
            """
            INSERT INTO activity_logs(user_id, username, action, target_type, target_id, detail)
            VALUES(%s,%s,%s,%s,%s,%s)
            """.strip(),
            (
                (int(user_id) if user_id else None),
                (username[:50] if username else None),
                action[:60],
                (target_type[:40] if target_type else None),
                (int(target_id) if target_id else None),
                (detail[:500] if detail else None),
            ),
        )

    def list_recent(self, limit: int = 200) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT id, user_id, username, action, target_type, target_id, detail, created_at
            FROM activity_logs
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """.strip(),
            (int(limit),),
        )

    def list_for_user(self, user_id: int, limit: int = 200) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT id, user_id, username, action, target_type, target_id, detail, created_at
            FROM activity_logs
            WHERE user_id=%s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """.strip(),
            (int(user_id), int(limit)),
        )

    def list_for_target(self, target_type: str, target_id: int, limit: int = 100) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT id, user_id, username, action, detail, created_at
            FROM activity_logs
            WHERE target_type=%s AND target_id=%s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """.strip(),
            (target_type, int(target_id), int(limit)),
        )
