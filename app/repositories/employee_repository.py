from __future__ import annotations

from app.core.db import Database


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT e.id, e.name, e.phone, e.salary, e.role_id, r.name AS role_name
            FROM employees e
            LEFT JOIN roles r ON r.id = e.role_id
            ORDER BY e.id DESC
            """.strip()
        )

    def create(self, name: str, phone: str | None, salary: float, role_id: int | None) -> int:
        return self._db.execute(
            "INSERT INTO employees(name, phone, salary, role_id) VALUES(%s,%s,%s,%s)",
            (name, phone, salary, role_id),
        )

    def update(self, employee_id: int, name: str, phone: str | None, salary: float, role_id: int | None) -> int:
        self._db.execute(
            "UPDATE employees SET name=%s, phone=%s, salary=%s, role_id=%s WHERE id=%s",
            (name, phone, salary, role_id, employee_id),
        )
        return employee_id

    def delete(self, employee_id: int) -> None:
        self._db.execute("DELETE FROM employees WHERE id=%s", (employee_id,))

