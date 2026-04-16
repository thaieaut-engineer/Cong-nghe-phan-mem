from __future__ import annotations

from app.core.db import Database


class InvoiceRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT i.id, i.session_id, i.total, i.created_at, t.name AS table_name
            FROM invoices i
            LEFT JOIN sessions s ON s.id = i.session_id
            LEFT JOIN tables t ON t.id = s.table_id
            ORDER BY i.id DESC
            """.strip()
        )

    def get_detail(self, invoice_id: int) -> dict | None:
        return self._db.fetch_one(
            """
            SELECT i.id, i.session_id, i.total, i.created_at, t.name AS table_name
            FROM invoices i
            LEFT JOIN sessions s ON s.id = i.session_id
            LEFT JOIN tables t ON t.id = s.table_id
            WHERE i.id=%s
            """.strip(),
            (invoice_id,),
        )

    def create_for_session(self, session_id: int, total: float) -> int:
        return self._db.execute(
            "INSERT INTO invoices(session_id, total) VALUES(%s,%s)",
            (session_id, total),
        )

