from __future__ import annotations

from app.core.db import Database


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def revenue_by_day(self, days: int = 14) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT DATE(created_at) AS day, SUM(total) AS revenue, COUNT(*) AS invoices
            FROM invoices
            WHERE created_at >= (NOW() - INTERVAL %s DAY)
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            """.strip(),
            (days,),
        )

    def top_services(self, limit: int = 10) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT sv.name AS service_name, SUM(ss.quantity) AS qty, SUM(ss.quantity * ss.unit_price) AS amount
            FROM session_services ss
            LEFT JOIN services sv ON sv.id = ss.service_id
            GROUP BY sv.name
            ORDER BY amount DESC
            LIMIT %s
            """.strip(),
            (limit,),
        )

