from __future__ import annotations

from app.core.db import Database


class InventoryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    # ----- items -----
    def list_items(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT i.id, i.name, i.unit, i.stock, i.min_stock, i.cost_price,
                   i.service_id, s.name AS service_name
            FROM inventory_items i
            LEFT JOIN services s ON s.id = i.service_id
            ORDER BY i.name ASC
            """.strip()
        )

    def get_item(self, item_id: int) -> dict | None:
        return self._db.fetch_one(
            "SELECT id, name, unit, stock, min_stock, cost_price, service_id "
            "FROM inventory_items WHERE id=%s",
            (int(item_id),),
        )

    def create_item(
        self,
        name: str,
        unit: str,
        stock: float,
        min_stock: float,
        cost_price: float,
        service_id: int | None,
    ) -> int:
        return self._db.execute(
            "INSERT INTO inventory_items(name, unit, stock, min_stock, cost_price, service_id) "
            "VALUES(%s,%s,%s,%s,%s,%s)",
            (
                name.strip(),
                (unit or "cái").strip(),
                float(stock),
                float(min_stock),
                float(cost_price),
                (int(service_id) if service_id else None),
            ),
        )

    def update_item(
        self,
        item_id: int,
        name: str,
        unit: str,
        min_stock: float,
        cost_price: float,
        service_id: int | None,
    ) -> None:
        self._db.execute(
            "UPDATE inventory_items SET name=%s, unit=%s, min_stock=%s, cost_price=%s, service_id=%s "
            "WHERE id=%s",
            (
                name.strip(),
                (unit or "cái").strip(),
                float(min_stock),
                float(cost_price),
                (int(service_id) if service_id else None),
                int(item_id),
            ),
        )

    def delete_item(self, item_id: int) -> None:
        self._db.execute("DELETE FROM inventory_items WHERE id=%s", (int(item_id),))

    # ----- movements -----
    def add_movement(
        self,
        item_id: int,
        movement_type: str,
        quantity: float,
        ref_type: str | None = None,
        ref_id: int | None = None,
        note: str | None = None,
        created_by: int | None = None,
    ) -> int:
        if movement_type not in ("in", "out", "adjust"):
            raise ValueError("movement_type phải là in|out|adjust")
        mid = self._db.execute(
            "INSERT INTO inventory_movements(item_id, movement_type, quantity, ref_type, ref_id, note, created_by) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (
                int(item_id),
                movement_type,
                float(quantity),
                ref_type,
                (int(ref_id) if ref_id else None),
                note,
                (int(created_by) if created_by else None),
            ),
        )
        delta = float(quantity)
        if movement_type == "in":
            self._db.execute(
                "UPDATE inventory_items SET stock = stock + %s WHERE id=%s",
                (delta, int(item_id)),
            )
        elif movement_type == "out":
            self._db.execute(
                "UPDATE inventory_items SET stock = stock - %s WHERE id=%s",
                (delta, int(item_id)),
            )
        else:  # adjust → set stock = quantity (số tuyệt đối)
            self._db.execute(
                "UPDATE inventory_items SET stock = %s WHERE id=%s",
                (delta, int(item_id)),
            )
        return mid

    def list_movements(self, item_id: int | None = None, limit: int = 200) -> list[dict]:
        if item_id is None:
            return self._db.fetch_all(
                """
                SELECT m.id, m.item_id, i.name AS item_name, m.movement_type, m.quantity,
                       m.ref_type, m.ref_id, m.note, m.created_at,
                       u.username AS created_by_name
                FROM inventory_movements m
                LEFT JOIN inventory_items i ON i.id = m.item_id
                LEFT JOIN users u ON u.id = m.created_by
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT %s
                """.strip(),
                (int(limit),),
            )
        return self._db.fetch_all(
            """
            SELECT m.id, m.movement_type, m.quantity, m.ref_type, m.ref_id, m.note,
                   m.created_at, u.username AS created_by_name
            FROM inventory_movements m
            LEFT JOIN users u ON u.id = m.created_by
            WHERE m.item_id=%s
            ORDER BY m.created_at DESC, m.id DESC
            LIMIT %s
            """.strip(),
            (int(item_id), int(limit)),
        )

    def low_stock(self) -> list[dict]:
        return self._db.fetch_all(
            "SELECT id, name, unit, stock, min_stock FROM inventory_items "
            "WHERE stock <= min_stock ORDER BY stock ASC"
        )
