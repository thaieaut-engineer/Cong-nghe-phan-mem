from __future__ import annotations

from app.core.db import Database


class PaymentGroupRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, name: str, total: float, created_by: int | None) -> int:
        return self._db.execute(
            "INSERT INTO payment_groups(name, total, created_by) VALUES(%s,%s,%s)",
            (name.strip(), float(total), (int(created_by) if created_by else None)),
        )

    def add_invoice(self, payment_group_id: int, invoice_id: int) -> None:
        self._db.execute(
            "INSERT IGNORE INTO payment_group_invoices(payment_group_id, invoice_id) VALUES(%s,%s)",
            (int(payment_group_id), int(invoice_id)),
        )

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT pg.id, pg.name, pg.total, pg.created_at,
                   u.username AS created_by_name,
                   (SELECT COUNT(*) FROM payment_group_invoices pgi WHERE pgi.payment_group_id = pg.id) AS invoice_count
            FROM payment_groups pg
            LEFT JOIN users u ON u.id = pg.created_by
            ORDER BY pg.created_at DESC, pg.id DESC
            """.strip()
        )

    def list_invoices(self, payment_group_id: int) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT i.id, i.session_id, i.total, i.created_at, t.name AS table_name
            FROM payment_group_invoices pgi
            JOIN invoices i ON i.id = pgi.invoice_id
            LEFT JOIN sessions s ON s.id = i.session_id
            LEFT JOIN tables t ON t.id = s.table_id
            WHERE pgi.payment_group_id=%s
            ORDER BY i.id DESC
            """.strip(),
            (int(payment_group_id),),
        )
