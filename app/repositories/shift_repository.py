from __future__ import annotations

from app.core.db import Database


class ShiftRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            "SELECT id, name, start_time, end_time, salary_factor FROM shifts ORDER BY id DESC"
        )

    def create(self, name: str, start_time: str, end_time: str, salary_factor: float = 1) -> int:
        return self._db.execute(
            "INSERT INTO shifts(name, start_time, end_time, salary_factor) VALUES(%s,%s,%s,%s)",
            (name, start_time, end_time, float(salary_factor)),
        )

    def update(self, shift_id: int, name: str, start_time: str, end_time: str, salary_factor: float = 1) -> int:
        self._db.execute(
            "UPDATE shifts SET name=%s, start_time=%s, end_time=%s, salary_factor=%s WHERE id=%s",
            (name, start_time, end_time, float(salary_factor), shift_id),
        )
        return shift_id

    def delete(self, shift_id: int) -> None:
        self._db.execute("DELETE FROM shifts WHERE id=%s", (shift_id,))

