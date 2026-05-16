from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.currency import format_vnd


@dataclass(frozen=True)
class TableState:
    table_id: int
    name: str
    status: str  # 'empty' | 'playing' | 'maintenance' (DB)
    type_name: str
    price_per_hour: float
    active_session_id: int | None
    active_start_time: str | None  # 'YYYY-MM-DD HH:MM:SS' (str)
    active_total: float
    has_booking: bool = False  # bàn đang được đặt trước (sắp tới)
    discount_percent: float = 0.0  # % giảm giá hiển thị (tuỳ ý)


class _TableCard(QFrame):
    """Thẻ một bàn trong sơ đồ bàn — clickable."""

    clicked = Signal(int)  # table_id

    def __init__(self, t: TableState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = t
        self.setProperty("tableCard", True)
        # Bắt buộc với QFrame để stylesheet background được vẽ.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(118)

        # ----- Phân loại visual -----
        # Mapping DB status → màu thẻ.
        # - playing → cam (đang chơi)
        # - maintenance → vàng (có điện / bảo trì)
        # - empty + has_booking → xanh dương (đặt trước)
        # - empty + VIP → đỏ (Bàn VIP)
        # - empty + bình thường → xám đậm (Bàn thường, rảnh chưa active)
        # - empty đặc biệt (mặc định trống xanh lá) → dùng khi muốn "Bàn trống" rõ ràng
        is_vip = "vip" in (t.type_name or "").lower()
        if t.status == "playing":
            visual = "playing"
        elif t.status == "maintenance":
            visual = "maintenance"
        elif t.has_booking:
            visual = "booked"
        elif is_vip:
            visual = "vip"
        else:
            visual = "empty"
        self.setProperty("tableStatus", visual)
        self._visual = visual

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(6)

        # ----- Header: tên + tag trạng thái -----
        head = QHBoxLayout()
        head.setSpacing(8)

        name = QLabel(t.name)
        name.setProperty("tableName", True)

        tag = QLabel(self._status_label(visual))
        tag.setProperty("statusTag", True)
        tag.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        head.addWidget(name, 1)
        head.addWidget(tag, 0)
        root.addLayout(head)

        # ----- Loại bàn -----
        type_lbl = QLabel(t.type_name or "Bàn thường")
        type_lbl.setProperty("tableType", True)
        root.addWidget(type_lbl)

        # ----- Body: theo trạng thái -----
        if visual == "playing":
            self._build_playing_body(root)
        else:
            self._build_idle_body(root, visual)

    # ---------- helpers ----------
    @staticmethod
    def _status_label(visual: str) -> str:
        return {
            "playing": "Đang chơi",
            "maintenance": "Có điện",
            "booked": "Đặt trước",
            "vip": "Bàn VIP",
            "empty": "Bàn trống",
        }.get(visual, "Bàn trống")

    def _build_playing_body(self, root: QVBoxLayout) -> None:
        t = self._t
        # Đồng hồ phút/giây + thời điểm bắt đầu
        clock_row = QHBoxLayout()
        clock_row.setSpacing(4)

        self._lbl_min = QLabel("0")
        self._lbl_min.setProperty("clockBig", True)
        unit_min = QLabel("phút")
        unit_min.setProperty("clockUnit", True)

        self._lbl_sec = QLabel("0")
        self._lbl_sec.setProperty("clockBig", True)
        unit_sec = QLabel("giây")
        unit_sec.setProperty("clockUnit", True)

        clock_row.addWidget(self._lbl_min)
        clock_row.addWidget(unit_min)
        clock_row.addSpacing(6)
        clock_row.addWidget(self._lbl_sec)
        clock_row.addWidget(unit_sec)
        clock_row.addStretch(1)

        root.addLayout(clock_row)

        # Bắt đầu + giảm giá + giá tạm tính
        meta = QHBoxLayout()
        meta.setSpacing(8)

        start_text = (t.active_start_time or "").split(" ")[-1] if t.active_start_time else "--:--:--"
        lbl_start = QLabel(f"⏱ {start_text}")
        lbl_start.setProperty("startTime", True)
        meta.addWidget(lbl_start)

        if t.discount_percent and t.discount_percent > 0:
            lbl_disc = QLabel(f"% {int(t.discount_percent)}%")
            lbl_disc.setProperty("discountTag", True)
            meta.addWidget(lbl_disc)

        meta.addStretch(1)

        lbl_amount = QLabel(format_vnd(float(t.active_total or 0), compact=True))
        lbl_amount.setProperty("priceBig", True)
        meta.addWidget(lbl_amount)

        root.addLayout(meta)

        self._tick_now()

    def _build_idle_body(self, root: QVBoxLayout, visual: str) -> None:
        # Khoảng đẩy nội dung & nút play giả
        spacer = QLabel(" ")
        root.addWidget(spacer)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        play = QLabel("▶")
        play.setStyleSheet(
            "color: rgba(255,255,255,0.75); font-size: 30px; font-weight: 800;"
            " background: transparent;"
        )
        play.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        bottom.addWidget(play)
        root.addLayout(bottom)

    # ---------- public ----------
    def tick(self) -> None:
        """Cập nhật đồng hồ phút/giây nếu đang chơi."""
        if self._visual != "playing":
            return
        self._tick_now()

    def _tick_now(self) -> None:
        t = self._t
        if not t.active_start_time:
            return
        try:
            start = datetime.strptime(t.active_start_time, "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                start = datetime.fromisoformat(t.active_start_time)
            except Exception:
                return
        delta = datetime.now() - start
        total_sec = int(max(0, delta.total_seconds()))
        mins, secs = divmod(total_sec, 60)
        if hasattr(self, "_lbl_min"):
            self._lbl_min.setText(str(mins))
        if hasattr(self, "_lbl_sec"):
            self._lbl_sec.setText(str(secs))

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(int(self._t.table_id))
        super().mousePressEvent(event)


class SessionsBoard(QWidget):
    """Sơ đồ bàn — theo ý tưởng UI từ ảnh.

    Phát các signal điều khiển ra ngoài để MainWindow xử lý nghiệp vụ.
    """

    refresh_requested = Signal()
    table_clicked = Signal(int)    # table_id (mọi click)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tables: list[TableState] = []
        self._cards: list[_TableCard] = []
        self._active_filter: str = "all"  # all|empty|playing|maintenance|booked

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        root.addWidget(self._build_filter_bar())
        root.addWidget(self._build_counter_row())

        # ----- Grid -----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        self._scroll.setWidget(self._grid_host)
        root.addWidget(self._scroll, 1)

        self._empty = QLabel("Chưa có bàn nào. Hãy tạo bàn trong mục “Thiết đặt bàn”.")
        self._empty.setProperty("muted", True)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)
        root.addWidget(self._empty)

        # ----- Tick timer cho đồng hồ phút/giây -----
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_all)
        self._timer.start()

    # ---------- UI builders ----------
    def _build_filter_bar(self) -> QWidget:
        bar = QFrame()
        bar.setProperty("card", True)
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)

        # Ngày
        lbl_date = QLabel("Ngày")
        lbl_date.setStyleSheet("font-weight:600;")
        self._date = QDateEdit(QDate.currentDate())
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("dd/MM/yyyy")
        self._date.setFixedWidth(130)

        # Tầng
        lbl_floor = QLabel("Tầng")
        lbl_floor.setStyleSheet("font-weight:600;")
        self._floor = QComboBox()
        self._floor.addItem("Tất cả", None)
        self._floor.setFixedWidth(120)

        # Tìm kiếm
        self._search = QLineEdit()
        self._search.setPlaceholderText("Tìm bàn theo tên...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(lambda _=None: self._render())

        # Status pills (Đang chơi / Bàn trống / Có điện / Đặt trước)
        self._pill_all = self._make_pill("Tất cả", "all")
        self._pill_playing = self._make_pill("Đang chơi", "playing")
        self._pill_empty = self._make_pill("Bàn trống", "empty")
        self._pill_maint = self._make_pill("Có điện", "maintenance")
        self._pill_booked = self._make_pill("Đặt trước", "booked")
        self._set_active_pill("all")

        h.addWidget(lbl_date)
        h.addWidget(self._date)
        h.addSpacing(6)
        h.addWidget(lbl_floor)
        h.addWidget(self._floor)
        h.addSpacing(6)
        h.addWidget(self._search, 1)
        h.addSpacing(6)
        h.addWidget(self._pill_playing)
        h.addWidget(self._pill_empty)
        h.addWidget(self._pill_maint)
        h.addWidget(self._pill_booked)
        h.addWidget(self._pill_all)

        return bar

    def _make_pill(self, text: str, key: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("filterPill", key)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _=False, k=key: self._on_pill_clicked(k))
        return btn

    def _build_counter_row(self) -> QWidget:
        wrap = QWidget()
        h = QHBoxLayout(wrap)
        h.setContentsMargins(2, 0, 2, 0)
        h.setSpacing(10)

        self._cnt_booked = QLabel("(0) Đặt bàn")
        self._cnt_booked.setProperty("counterChip", "booked")
        self._cnt_playing = QLabel("(0) Đang chơi")
        self._cnt_playing.setProperty("counterChip", "playing")
        self._cnt_done = QLabel("(0) Trả bàn")
        self._cnt_done.setProperty("counterChip", "maintenance")
        self._cnt_empty = QLabel("(0) Bàn trống")
        self._cnt_empty.setProperty("counterChip", "empty")

        h.addWidget(self._cnt_booked)
        h.addWidget(self._cnt_playing)
        h.addWidget(self._cnt_done)
        h.addWidget(self._cnt_empty)
        h.addStretch(1)
        return wrap

    # ---------- Public ----------
    def set_tables(self, tables: list[TableState]) -> None:
        self._tables = list(tables)
        self._refresh_floors()
        self._update_counters()
        self._render()

    # ---------- Internal ----------
    def _refresh_floors(self) -> None:
        # (Tuỳ chọn) Hiện chỉ có "Tất cả" — sau này nếu có thuộc tính floor có thể nạp thêm.
        # Tránh reset nếu list không đổi.
        if self._floor.count() <= 1:
            return

    def _on_pill_clicked(self, key: str) -> None:
        # toggle off → all
        if self._active_filter == key:
            self._active_filter = "all"
        else:
            self._active_filter = key
        self._set_active_pill(self._active_filter)
        self._render()

    def _set_active_pill(self, key: str) -> None:
        for k, btn in (
            ("all", self._pill_all),
            ("empty", self._pill_empty),
            ("playing", self._pill_playing),
            ("maintenance", self._pill_maint),
            ("booked", self._pill_booked),
        ):
            btn.setProperty("active", "true" if k == key else "false")
            btn.setChecked(k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_counters(self) -> None:
        c_play = sum(1 for x in self._tables if x.status == "playing")
        c_empty = sum(1 for x in self._tables if x.status == "empty" and not x.has_booking)
        c_book = sum(1 for x in self._tables if x.status == "empty" and x.has_booking)
        c_maint = sum(1 for x in self._tables if x.status == "maintenance")

        self._cnt_booked.setText(f"({c_book}) Đặt bàn")
        self._cnt_playing.setText(f"({c_play}) Đang chơi")
        self._cnt_done.setText(f"({c_maint}) Trả bàn")
        self._cnt_empty.setText(f"({c_empty}) Bàn trống")

    def _passes_filter(self, t: TableState) -> bool:
        f = self._active_filter
        q = (self._search.text() or "").strip().lower()
        if q and q not in (t.name or "").lower():
            return False
        if f == "all":
            return True
        if f == "playing":
            return t.status == "playing"
        if f == "maintenance":
            return t.status == "maintenance"
        if f == "empty":
            return t.status == "empty" and not t.has_booking
        if f == "booked":
            return t.status == "empty" and t.has_booking
        return True

    def _clear_grid(self) -> None:
        self._cards.clear()
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render(self) -> None:
        self._clear_grid()
        items = [t for t in self._tables if self._passes_filter(t)]
        if not items:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)

        cols = 4

        def sort_key(x: TableState) -> tuple:
            order = {"playing": 0, "empty": 1, "maintenance": 2}.get(x.status, 3)
            return (order, x.name.lower(), x.table_id)

        items.sort(key=sort_key)
        r = 0
        c = 0
        for t in items:
            card = _TableCard(t)
            card.clicked.connect(self.table_clicked.emit)
            self._cards.append(card)
            self._grid.addWidget(card, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1
        if c != 0:
            r += 1
        self._grid.setRowStretch(r + 1, 1)
        for i in range(cols):
            self._grid.setColumnStretch(i, 1)

    def _tick_all(self) -> None:
        for card in self._cards:
            card.tick()
