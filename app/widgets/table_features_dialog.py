from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class BillService:
    name: str
    quantity: int
    unit_price: float

    @property
    def amount(self) -> float:
        return float(self.quantity) * float(self.unit_price)


@dataclass(frozen=True)
class BillSummary:
    table_amount: float = 0.0
    discount_percent: float = 0.0
    services: tuple[BillService, ...] = ()

    @property
    def discount_amount(self) -> float:
        if self.discount_percent <= 0:
            return 0.0
        return self.table_amount * float(self.discount_percent) / 100.0

    @property
    def services_total(self) -> float:
        return float(sum(s.amount for s in self.services))


# action_id phát ra khi user bấm 1 trong các nút tính năng.
# Các action_id:
ACTION_SERVICE = "service"
ACTION_PAYMENT = "payment"
ACTION_TRANSFER = "transfer"
ACTION_MEMBER = "member"
ACTION_GROUP_PAY = "group_pay"
ACTION_DETAIL = "detail"
ACTION_POWER_HISTORY = "power_history"
ACTION_USER_HISTORY = "user_history"


def _fmt_vnd(v: float) -> str:
    try:
        return f"{int(round(v)):,}".replace(",", ",")
    except Exception:
        return "0"


class TableFeaturesDialog(QDialog):
    """Modal "Tính năng" cho 1 bàn — theo ý tưởng từ ảnh.

    Phát signal `action_triggered(str)` với 1 trong các ACTION_* khi user chọn nút.
    """

    action_triggered = Signal(str)

    def __init__(
        self,
        table_name: str,
        bill: BillSummary,
        parent: QWidget | None = None,
        is_playing: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tableFeaturesDialog")
        self.setWindowTitle(f"Tính năng - {table_name}")
        self.setModal(True)
        self.setMinimumWidth(520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        # ---- Tiêu đề ----
        title = QLabel("Tính năng")
        title.setObjectName("featuresTitle")
        outer.addWidget(title)

        # ---- Lưới 8 nút tính năng (3 cột) ----
        grid_wrap = QFrame()
        grid_wrap.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        actions = [
            ("🛎",  "Dịch vụ",           ACTION_SERVICE,        is_playing),
            ("💳",  "Thanh toán",        ACTION_PAYMENT,        is_playing),
            ("⇄",   "Chuyển bàn",        ACTION_TRANSFER,       is_playing),
            ("🪪",  "Thẻ thành viên",    ACTION_MEMBER,         True),
            ("👥",  "Thanh toán nhóm",   ACTION_GROUP_PAY,      is_playing),
            ("🔍",  "Xem chi tiết",      ACTION_DETAIL,         is_playing),
            ("⏻",   "Lịch sử bật/tắt điện", ACTION_POWER_HISTORY, True),
            ("🕘",  "Lịch sử người dùng",ACTION_USER_HISTORY,   True),
        ]

        for idx, (icon, label, action_id, enabled) in enumerate(actions):
            btn = self._make_feature_button(icon, label, action_id)
            btn.setEnabled(enabled)
            r, c = divmod(idx, 3)
            grid.addWidget(btn, r, c)
        for i in range(3):
            grid.setColumnStretch(i, 1)

        outer.addWidget(grid_wrap)

        # ---- Đường kẻ ngăn ----
        sep = QFrame()
        sep.setObjectName("billSeparator")
        sep.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(sep)

        # ---- Tóm tắt hóa đơn ----
        outer.addLayout(self._build_bill_layout(bill))

        # ---- Nút đóng (góc dưới) ----
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_close = QPushButton("Đóng")
        btn_close.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.35);"
            "color:#fff;border-radius:8px;padding:6px 14px;font-weight:600;}"
            "QPushButton:hover{background:rgba(255,255,255,0.28);}"
        )
        btn_close.clicked.connect(self.reject)
        bottom.addWidget(btn_close)
        outer.addLayout(bottom)

    # ---------- builders ----------
    def _make_feature_button(self, icon: str, label: str, action_id: str) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("featureBtn", True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(86)
        # icon + 2 dòng chữ
        btn.setText(f"{icon}\n{label}")
        btn.setStyleSheet(btn.styleSheet())  # buộc re-polish nếu cần
        btn.clicked.connect(lambda _=False, a=action_id: self._on_action(a))
        return btn

    def _on_action(self, action_id: str) -> None:
        self.action_triggered.emit(action_id)
        # Đóng dialog sau khi chọn (để MainWindow xử lý tiếp).
        self.accept()

    def _build_bill_layout(self, bill: BillSummary) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        v.addLayout(_bill_line("Tiền bàn", _fmt_vnd(bill.table_amount)))
        if bill.discount_percent > 0:
            v.addLayout(
                _bill_line(
                    f"Giảm giá ({int(bill.discount_percent)}%)",
                    _fmt_vnd(bill.discount_amount),
                )
            )
        if bill.services:
            v.addLayout(_bill_line("Dịch vụ sử dụng", _fmt_vnd(bill.services_total)))
            for s in bill.services:
                detail = QLabel(
                    f"   {s.name}    {s.quantity} x {_fmt_vnd(s.unit_price)} = {_fmt_vnd(s.amount)}"
                )
                detail.setProperty("billLine", True)
                v.addWidget(detail)
        else:
            empty = QLabel("Chưa có dịch vụ sử dụng.")
            empty.setProperty("billLine", True)
            v.addWidget(empty)
        return v


def _bill_line(label: str, value: str) -> QHBoxLayout:
    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    lbl = QLabel(label)
    lbl.setProperty("billLine", True)
    val = QLabel(value)
    val.setProperty("billValue", True)
    val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    h.addWidget(lbl, 1)
    h.addWidget(val, 0)
    return h
