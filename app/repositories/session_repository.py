from __future__ import annotations

from app.core.db import Database


class SessionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT s.id, s.table_id, t.name AS table_name, s.start_time, s.end_time, s.total
            FROM sessions s
            LEFT JOIN tables t ON t.id = s.table_id
            ORDER BY s.id DESC
            """.strip()
        )

    def get_detail(self, session_id: int) -> dict | None:
        return self._db.fetch_one(
            """
            SELECT s.id, s.table_id, t.name AS table_name, s.start_time, s.end_time, s.total
            FROM sessions s
            LEFT JOIN tables t ON t.id = s.table_id
            WHERE s.id=%s
            """.strip(),
            (session_id,),
        )

    def list_services(self, session_id: int) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT ss.id, ss.quantity, ss.unit_price, sv.name AS service_name
            FROM session_services ss
            LEFT JOIN services sv ON sv.id = ss.service_id
            WHERE ss.session_id=%s
            ORDER BY ss.id DESC
            """.strip(),
            (session_id,),
        )

    def start_session(self, table_id: int) -> int:
        # status constraint is handled at UI level; DB still enforces FK.
        self._db.execute("UPDATE tables SET status='playing' WHERE id=%s", (table_id,))
        return self._db.execute(
            "INSERT INTO sessions(table_id, start_time, end_time, total) VALUES(%s, NOW(), NULL, 0)",
            (table_id,),
        )

    def add_service(self, session_id: int, service_id: int, quantity: int, unit_price: float) -> int:
        return self._db.execute(
            """
            INSERT INTO session_services(session_id, service_id, quantity, unit_price)
            VALUES(%s,%s,%s,%s)
            """.strip(),
            (session_id, service_id, quantity, unit_price),
        )

    def compute_total(self, session_id: int) -> float:
        row = self._db.fetch_one(
            """
            SELECT
              (TIMESTAMPDIFF(SECOND, s.start_time, COALESCE(s.end_time, NOW())) / 3600.0) * COALESCE(tt.price_per_hour, 0) AS table_amount,
              COALESCE((
                SELECT SUM(ss.quantity * ss.unit_price)
                FROM session_services ss
                WHERE ss.session_id = s.id
              ), 0) AS service_amount
            FROM sessions s
            LEFT JOIN tables t ON t.id = s.table_id
            LEFT JOIN table_types tt ON tt.id = t.type_id
            WHERE s.id=%s
            """.strip(),
            (session_id,),
        )
        if not row:
            return 0.0
        return float(row.get("table_amount", 0) or 0) + float(row.get("service_amount", 0) or 0)

    def end_session(self, session_id: int) -> float:
        # set end_time first, then compute total based on end_time
        sess = self._db.fetch_one("SELECT table_id FROM sessions WHERE id=%s", (session_id,))
        if not sess:
            raise ValueError("Session không tồn tại.")
        self._db.execute("UPDATE sessions SET end_time=NOW() WHERE id=%s", (session_id,))
        total = self.compute_total(session_id)
        self._db.execute("UPDATE sessions SET total=%s WHERE id=%s", (total, session_id))
        self._db.execute("UPDATE tables SET status='empty' WHERE id=%s", (int(sess["table_id"]),))
        return float(total)

