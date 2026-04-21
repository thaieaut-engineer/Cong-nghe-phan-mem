from __future__ import annotations

from app.core.db import Database


def _column_exists(db: Database, table: str, column: str) -> bool:
    row = db.fetch_one(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """.strip(),
        (table, column),
    )
    return row is not None


def ensure_service_images_columns(db: Database) -> None:
    """
    Best-effort migration for existing databases.
    """
    if not _column_exists(db, "service_types", "image_path"):
        db.execute("ALTER TABLE service_types ADD COLUMN image_path VARCHAR(255) NULL")
    if not _column_exists(db, "services", "image_path"):
        db.execute("ALTER TABLE services ADD COLUMN image_path VARCHAR(255) NULL")

