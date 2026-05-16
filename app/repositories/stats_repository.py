from __future__ import annotations

from datetime import date

from app.core.db import Database


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def dashboard_kpis(self) -> dict:
        row = self._db.fetch_one(
            """
            SELECT
              (SELECT COUNT(*) FROM tables) AS tables_total,
              (SELECT COUNT(*) FROM tables WHERE status='empty') AS tables_empty,
              (SELECT COUNT(*) FROM tables WHERE status='playing') AS tables_playing,
              (SELECT COUNT(*) FROM tables WHERE status='maintenance') AS tables_maintenance,
              (SELECT COUNT(*) FROM sessions WHERE end_time IS NULL) AS active_sessions,
              (SELECT COUNT(*) FROM bookings WHERE DATE(start_time) = CURDATE()) AS bookings_today,
              (SELECT COUNT(*) FROM invoices WHERE DATE(created_at) = CURDATE()) AS invoices_today,
              (SELECT COALESCE(SUM(total), 0) FROM invoices WHERE DATE(created_at) = CURDATE()) AS revenue_today
            """.strip()
        )
        return dict(row) if row else {}

    def recent_invoices(self, limit: int = 8) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT i.id, i.session_id, i.total, i.created_at, t.name AS table_name
            FROM invoices i
            LEFT JOIN sessions s ON s.id = i.session_id
            LEFT JOIN tables t ON t.id = s.table_id
            ORDER BY i.id DESC
            LIMIT %s
            """.strip(),
            (int(limit),),
        )

    def upcoming_bookings(self, limit: int = 8) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT b.id, b.customer_name, b.phone, b.start_time, b.end_time, t.name AS table_name
            FROM bookings b
            LEFT JOIN tables t ON t.id = b.table_id
            WHERE b.start_time >= NOW()
            ORDER BY b.start_time ASC
            LIMIT %s
            """.strip(),
            (int(limit),),
        )

    def revenue_by_day(self, days: int = 14) -> list[dict]:
        end = date.today()
        start = end.fromordinal(end.toordinal() - max(0, int(days) - 1))
        return self.revenue_by_date_range(start, end)

    def revenue_by_date_range(self, start: date, end: date) -> list[dict]:
        if start > end:
            start, end = end, start
        return self._db.fetch_all(
            """
            SELECT DATE(created_at) AS day, SUM(total) AS revenue, COUNT(*) AS invoices
            FROM invoices
            WHERE DATE(created_at) BETWEEN %s AND %s
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """.strip(),
            (start.isoformat(), end.isoformat()),
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
