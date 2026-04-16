from __future__ import annotations

from app.core.db import Database


class BookingRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT b.id, b.customer_name, b.phone, b.start_time, b.end_time, b.note,
                   b.table_id, t.name AS table_name
            FROM bookings b
            LEFT JOIN tables t ON t.id = b.table_id
            ORDER BY b.id DESC
            """.strip()
        )

    def create(
        self,
        table_id: int,
        customer_name: str,
        phone: str | None,
        start_time: str,
        end_time: str,
        note: str | None,
    ) -> int:
        return self._db.execute(
            """
            INSERT INTO bookings(table_id, customer_name, phone, start_time, end_time, note)
            VALUES(%s,%s,%s,%s,%s,%s)
            """.strip(),
            (table_id, customer_name, phone, start_time, end_time, note),
        )

    def update(
        self,
        booking_id: int,
        table_id: int,
        customer_name: str,
        phone: str | None,
        start_time: str,
        end_time: str,
        note: str | None,
    ) -> int:
        self._db.execute(
            """
            UPDATE bookings
            SET table_id=%s, customer_name=%s, phone=%s, start_time=%s, end_time=%s, note=%s
            WHERE id=%s
            """.strip(),
            (table_id, customer_name, phone, start_time, end_time, note, booking_id),
        )
        return booking_id

    def delete(self, booking_id: int) -> None:
        self._db.execute("DELETE FROM bookings WHERE id=%s", (booking_id,))

