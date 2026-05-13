"""Dialog cho các tính năng mở rộng: Member, Group payment, Power history, Activity history."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


# =====================================================================
# Member chooser
# =====================================================================
class MemberChooserDialog(QDialog):
    """Cho phép tìm member theo code/tên/sđt; cho phép tạo mới nhanh.

    Trả về (member_id, applied_discount_percent) nếu Accepted.
    """

    def __init__(self, members_repo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Thẻ thành viên")
        self.setMinimumSize(520, 420)
        self._repo = members_repo
        self._selected_member: dict | None = None
        self._discount: float = 0.0

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QLabel("Chọn thẻ thành viên hoặc tạo mới")
        title.setStyleSheet("font-size:15px;font-weight:800;")
        v.addWidget(title)

        # --- Search row ---
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Tìm theo mã / tên / số điện thoại...")
        self._search.textChanged.connect(self._reload_list)
        btn_new = QPushButton("+ Thêm thành viên")
        btn_new.setProperty("variant", "primary")
        btn_new.clicked.connect(self._create_new)
        search_row.addWidget(self._search, 1)
        search_row.addWidget(btn_new)
        v.addLayout(search_row)

        # --- List ---
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(lambda _: self._on_pick())
        v.addWidget(self._list, 1)

        # --- Discount adjust ---
        form = QFormLayout()
        self._spin_disc = QDoubleSpinBox()
        self._spin_disc.setRange(0, 100)
        self._spin_disc.setSingleStep(1)
        self._spin_disc.setSuffix(" %")
        form.addRow("Áp dụng giảm giá:", self._spin_disc)
        v.addLayout(form)

        # --- Buttons ---
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._on_pick)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self._reload_list()

    def _reload_list(self) -> None:
        self._list.clear()
        q = self._search.text().strip()
        try:
            rows = self._repo.search(q) if q else self._repo.list_all()
        except Exception:
            rows = []
        for m in rows:
            text = (
                f"[{m.get('code')}]  {m.get('name')}"
                f"  •  SĐT: {m.get('phone') or '-'}"
                f"  •  Giảm giá: {int(m.get('discount_percent') or 0)}%"
            )
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, dict(m))
            self._list.addItem(it)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
            self._on_row_changed()
            self._list.currentRowChanged.connect(lambda _: self._on_row_changed())

    def _on_row_changed(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        m = item.data(Qt.ItemDataRole.UserRole) or {}
        self._spin_disc.setValue(float(m.get("discount_percent") or 0))

    def _create_new(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm thẻ thành viên")
        form = QFormLayout(dlg)
        e_code = QLineEdit()
        e_name = QLineEdit()
        e_phone = QLineEdit()
        e_email = QLineEdit()
        s_disc = QDoubleSpinBox()
        s_disc.setRange(0, 100)
        s_disc.setSuffix(" %")
        form.addRow("Mã thẻ *", e_code)
        form.addRow("Họ tên *", e_name)
        form.addRow("SĐT", e_phone)
        form.addRow("Email", e_email)
        form.addRow("Giảm giá mặc định", s_disc)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not e_code.text().strip() or not e_name.text().strip():
            return
        try:
            self._repo.create(
                e_code.text(),
                e_name.text(),
                e_phone.text(),
                e_email.text(),
                s_disc.value(),
            )
        except Exception:
            return
        self._search.setText(e_code.text().strip())
        self._reload_list()

    def _on_pick(self) -> None:
        item = self._list.currentItem()
        if item is None:
            self.reject()
            return
        self._selected_member = item.data(Qt.ItemDataRole.UserRole) or {}
        self._discount = float(self._spin_disc.value())
        self.accept()

    def selected(self) -> tuple[dict | None, float]:
        return self._selected_member, self._discount


# =====================================================================
# Group payment
# =====================================================================
class GroupPaymentDialog(QDialog):
    """Hiển thị các phiên đang chơi, cho phép tick chọn nhiều phiên để thanh toán nhóm.

    Trả về (group_name, list[session_id]) khi Accepted.
    """

    def __init__(
        self,
        active_sessions: list[dict],
        compute_total_fn,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Thanh toán nhóm")
        self.setMinimumSize(640, 460)
        self._active_sessions = active_sessions
        self._compute_total_fn = compute_total_fn
        self._result: tuple[str, list[int]] | None = None

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QLabel("Chọn các phiên đang chơi để thanh toán cùng lúc")
        title.setStyleSheet("font-size:15px;font-weight:800;")
        v.addWidget(title)

        # Group name
        form = QFormLayout()
        self._name = QLineEdit()
        self._name.setPlaceholderText("VD: Bàn A04 + B01 (khách đoàn)")
        form.addRow("Tên nhóm thanh toán:", self._name)
        v.addLayout(form)

        # Table of active sessions
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["", "Bàn", "Bắt đầu", "Tạm tính"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self._table.setRowCount(len(active_sessions))
        for i, s in enumerate(active_sessions):
            chk = QTableWidgetItem()
            chk.setFlags(chk.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, int(s["id"]))
            self._table.setItem(i, 0, chk)
            self._table.setItem(i, 1, QTableWidgetItem(str(s.get("table_name", ""))))
            self._table.setItem(i, 2, QTableWidgetItem(str(s.get("start_time", ""))))
            try:
                total = float(compute_total_fn(int(s["id"])) or 0)
            except Exception:
                total = float(s.get("total") or 0)
            cell = QTableWidgetItem(f"{int(round(total)):,}".replace(",", ".") + " đ")
            cell.setData(Qt.ItemDataRole.UserRole, float(total))
            self._table.setItem(i, 3, cell)

        self._table.itemChanged.connect(self._update_summary)
        v.addWidget(self._table, 1)

        # Summary
        self._lbl_summary = QLabel("Đã chọn 0 phiên — Tổng: 0 đ")
        self._lbl_summary.setStyleSheet("font-weight:700;")
        v.addWidget(self._lbl_summary)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = bb.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Thanh toán nhóm")
        ok_btn.setProperty("variant", "primary")
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _selected_ids_and_total(self) -> tuple[list[int], float]:
        ids: list[int] = []
        total = 0.0
        for i in range(self._table.rowCount()):
            chk = self._table.item(i, 0)
            if chk is None:
                continue
            if chk.checkState() == Qt.CheckState.Checked:
                sid = int(chk.data(Qt.ItemDataRole.UserRole))
                ids.append(sid)
                cell = self._table.item(i, 3)
                if cell is not None:
                    total += float(cell.data(Qt.ItemDataRole.UserRole) or 0)
        return ids, total

    def _update_summary(self, *_) -> None:
        ids, total = self._selected_ids_and_total()
        amount_text = f"{int(round(total)):,}".replace(",", ".") + " đ"
        self._lbl_summary.setText(f"Đã chọn {len(ids)} phiên — Tổng: {amount_text}")

    def _on_ok(self) -> None:
        ids, _ = self._selected_ids_and_total()
        if not ids:
            return
        name = self._name.text().strip() or f"Nhóm {len(ids)} phiên"
        self._result = (name, ids)
        self.accept()

    def result_value(self) -> tuple[str, list[int]] | None:
        return self._result


# =====================================================================
# History dialog (Power log / Activity log) — read-only generic
# =====================================================================
class HistoryDialog(QDialog):
    """Hiển thị 1 bảng read-only với rows + headers cho trước."""

    def __init__(
        self,
        title: str,
        headers: list[str],
        rows: list[list[str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 460)

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        lbl = QLabel(title)
        lbl.setStyleSheet("font-size:15px;font-weight:800;")
        v.addWidget(lbl)

        if not rows:
            empty = QLabel("Chưa có dữ liệu.")
            empty.setProperty("muted", True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(empty, 1)
        else:
            tbl = QTableWidget(len(rows), len(headers))
            tbl.setHorizontalHeaderLabels(headers)
            tbl.verticalHeader().setVisible(False)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    item = QTableWidgetItem(str(val) if val is not None else "")
                    tbl.setItem(r, c, item)
            tbl.resizeColumnsToContents()
            v.addWidget(tbl, 1)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        # Close button maps to "rejected" in Qt; but we accept both:
        for b in bb.buttons():
            b.clicked.connect(self.accept)
        v.addWidget(bb)
