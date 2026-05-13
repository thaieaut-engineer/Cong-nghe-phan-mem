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


def _table_exists(db: Database, table: str) -> bool:
    row = db.fetch_one(
        """
        SELECT 1
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        LIMIT 1
        """.strip(),
        (table,),
    )
    return row is not None


def ensure_service_images_columns(db: Database) -> None:
    """Migration cho ảnh dịch vụ (giữ tương thích ngược)."""
    if not _column_exists(db, "service_types", "image_path"):
        db.execute("ALTER TABLE service_types ADD COLUMN image_path VARCHAR(255) NULL")
    if not _column_exists(db, "services", "image_path"):
        db.execute("ALTER TABLE services ADD COLUMN image_path VARCHAR(255) NULL")


# ----- DDL cho các bảng nghiệp vụ mở rộng -----
# Mỗi entry: (tên bảng, câu CREATE TABLE đầy đủ).
_EXTRA_TABLES: list[tuple[str, str]] = [
    (
        "members",
        """
        CREATE TABLE IF NOT EXISTS members (
          id INT AUTO_INCREMENT PRIMARY KEY,
          code VARCHAR(40) NOT NULL UNIQUE,
          name VARCHAR(120) NOT NULL,
          phone VARCHAR(20),
          email VARCHAR(120),
          discount_percent FLOAT NOT NULL DEFAULT 0,
          total_spent FLOAT NOT NULL DEFAULT 0,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ),
    (
        "session_members",
        """
        CREATE TABLE IF NOT EXISTS session_members (
          session_id INT NOT NULL PRIMARY KEY,
          member_id INT NOT NULL,
          applied_discount_percent FLOAT NOT NULL DEFAULT 0,
          CONSTRAINT fk_sm_session FOREIGN KEY (session_id) REFERENCES sessions(id)
            ON UPDATE CASCADE ON DELETE CASCADE,
          CONSTRAINT fk_sm_member FOREIGN KEY (member_id) REFERENCES members(id)
            ON UPDATE CASCADE ON DELETE RESTRICT
        )
        """,
    ),
    (
        "power_logs",
        """
        CREATE TABLE IF NOT EXISTS power_logs (
          id INT AUTO_INCREMENT PRIMARY KEY,
          table_id INT NOT NULL,
          action ENUM('on','off') NOT NULL,
          user_id INT NULL,
          action_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          note VARCHAR(255),
          CONSTRAINT fk_pl_table FOREIGN KEY (table_id) REFERENCES tables(id)
            ON UPDATE CASCADE ON DELETE CASCADE,
          CONSTRAINT fk_pl_user FOREIGN KEY (user_id) REFERENCES users(id)
            ON UPDATE CASCADE ON DELETE SET NULL,
          INDEX idx_pl_table_time (table_id, action_time)
        )
        """,
    ),
    (
        "activity_logs",
        """
        CREATE TABLE IF NOT EXISTS activity_logs (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NULL,
          username VARCHAR(50) NULL,
          action VARCHAR(60) NOT NULL,
          target_type VARCHAR(40),
          target_id INT,
          detail VARCHAR(500),
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_al_user FOREIGN KEY (user_id) REFERENCES users(id)
            ON UPDATE CASCADE ON DELETE SET NULL,
          INDEX idx_al_user_time (user_id, created_at),
          INDEX idx_al_action (action)
        )
        """,
    ),
    (
        "payment_groups",
        """
        CREATE TABLE IF NOT EXISTS payment_groups (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(120) NOT NULL,
          total FLOAT NOT NULL DEFAULT 0,
          created_by INT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_pg_user FOREIGN KEY (created_by) REFERENCES users(id)
            ON UPDATE CASCADE ON DELETE SET NULL
        )
        """,
    ),
    (
        "payment_group_invoices",
        """
        CREATE TABLE IF NOT EXISTS payment_group_invoices (
          payment_group_id INT NOT NULL,
          invoice_id INT NOT NULL,
          PRIMARY KEY (payment_group_id, invoice_id),
          CONSTRAINT fk_pgi_group FOREIGN KEY (payment_group_id) REFERENCES payment_groups(id)
            ON UPDATE CASCADE ON DELETE CASCADE,
          CONSTRAINT fk_pgi_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            ON UPDATE CASCADE ON DELETE CASCADE
        )
        """,
    ),
    (
        "expenses",
        """
        CREATE TABLE IF NOT EXISTS expenses (
          id INT AUTO_INCREMENT PRIMARY KEY,
          category VARCHAR(60) NOT NULL,
          amount FLOAT NOT NULL DEFAULT 0,
          expense_date DATE NOT NULL,
          note VARCHAR(255),
          created_by INT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_exp_user FOREIGN KEY (created_by) REFERENCES users(id)
            ON UPDATE CASCADE ON DELETE SET NULL,
          INDEX idx_exp_date (expense_date)
        )
        """,
    ),
    (
        "inventory_items",
        """
        CREATE TABLE IF NOT EXISTS inventory_items (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(120) NOT NULL,
          unit VARCHAR(20) NOT NULL DEFAULT 'cái',
          stock FLOAT NOT NULL DEFAULT 0,
          min_stock FLOAT NOT NULL DEFAULT 0,
          cost_price FLOAT NOT NULL DEFAULT 0,
          service_id INT NULL,
          CONSTRAINT fk_inv_service FOREIGN KEY (service_id) REFERENCES services(id)
            ON UPDATE CASCADE ON DELETE SET NULL
        )
        """,
    ),
    (
        "inventory_movements",
        """
        CREATE TABLE IF NOT EXISTS inventory_movements (
          id INT AUTO_INCREMENT PRIMARY KEY,
          item_id INT NOT NULL,
          movement_type ENUM('in','out','adjust') NOT NULL,
          quantity FLOAT NOT NULL DEFAULT 0,
          ref_type VARCHAR(40),
          ref_id INT,
          note VARCHAR(255),
          created_by INT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_im_item FOREIGN KEY (item_id) REFERENCES inventory_items(id)
            ON UPDATE CASCADE ON DELETE CASCADE,
          CONSTRAINT fk_im_user FOREIGN KEY (created_by) REFERENCES users(id)
            ON UPDATE CASCADE ON DELETE SET NULL,
          INDEX idx_im_item_time (item_id, created_at)
        )
        """,
    ),
    (
        "shift_handovers",
        """
        CREATE TABLE IF NOT EXISTS shift_handovers (
          id INT AUTO_INCREMENT PRIMARY KEY,
          from_user_id INT NULL,
          to_user_id INT NULL,
          handover_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          cash_amount FLOAT NOT NULL DEFAULT 0,
          note VARCHAR(255),
          CONSTRAINT fk_sh_from FOREIGN KEY (from_user_id) REFERENCES users(id)
            ON UPDATE CASCADE ON DELETE SET NULL,
          CONSTRAINT fk_sh_to FOREIGN KEY (to_user_id) REFERENCES users(id)
            ON UPDATE CASCADE ON DELETE SET NULL
        )
        """,
    ),
]


def ensure_extra_tables(db: Database) -> None:
    """Auto-tạo các bảng nghiệp vụ mở rộng cho DB đã có sẵn."""
    for name, ddl in _EXTRA_TABLES:
        if _table_exists(db, name):
            continue
        # MySQL connector không thích query nhiều dòng có trailing whitespace ở 1 số phiên bản.
        db.execute(" ".join(ddl.split()))


def run_all_migrations(db: Database) -> None:
    """Chạy toàn bộ migrations cần thiết khi app khởi động."""
    ensure_service_images_columns(db)
    ensure_extra_tables(db)
