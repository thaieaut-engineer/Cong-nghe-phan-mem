from __future__ import annotations

from app.core.db import Database


class ExpenseRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT e.id, e.category, e.amount, e.expense_date, e.note,
                   e.created_at, u.username AS created_by_name
            FROM expenses e
            LEFT JOIN users u ON u.id = e.created_by
            ORDER BY e.expense_date DESC, e.id DESC
            """.strip()
        )

    def create(
        self,
        category: str,
        amount: float,
        expense_date: str,
        note: str | None,
        created_by: int | None,
    ) -> int:
        return self._db.execute(
            "INSERT INTO expenses(category, amount, expense_date, note, created_by) "
            "VALUES(%s,%s,%s,%s,%s)",
            (
                category.strip(),
                float(amount),
                expense_date,
                (note.strip() if note else None),
                (int(created_by) if created_by else None),
            ),
        )

    def update(
        self,
        expense_id: int,
        category: str,
        amount: float,
        expense_date: str,
        note: str | None,
    ) -> None:
        self._db.execute(
            "UPDATE expenses SET category=%s, amount=%s, expense_date=%s, note=%s WHERE id=%s",
            (
                category.strip(),
                float(amount),
                expense_date,
                (note.strip() if note else None),
                int(expense_id),
            ),
        )

    def delete(self, expense_id: int) -> None:
        self._db.execute("DELETE FROM expenses WHERE id=%s", (int(expense_id),))

    def total_by_range(self, date_from: str, date_to: str) -> float:
        row = self._db.fetch_one(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses "
            "WHERE expense_date BETWEEN %s AND %s",
            (date_from, date_to),
        )
        return float(row["total"]) if row else 0.0
