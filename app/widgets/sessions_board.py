from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class TableState:
    table_id: int
    name: str
    status: str
    type_name: str
    price_per_hour: float
    active_session_id: int | None
    active_start_time: str | None
    active_total: float


class SessionsBoard(QWidget):
    refresh_requested = Signal()
    start_requested = Signal(int)  # table_id
    end_requested = Signal(int)  # session_id
    add_service_requested = Signal(int)  # session_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        title = QLabel("Bàn chơi")
        title.setStyleSheet("font-size:18px;font-weight:800;")
        hint = QLabel("Chọn bàn để bắt đầu/kết thúc phiên, hoặc thêm dịch vụ.")
        hint.setProperty("muted", True)
        hint.setWordWrap(True)

        header_left = QVBoxLayout()
        header_left.setSpacing(2)
        header_left.addWidget(title)
        header_left.addWidget(hint)

        self._btn_refresh = QPushButton("Làm mới")
        self._btn_refresh.clicked.connect(self.refresh_requested.emit)

        header.addLayout(header_left, 1)
        header.addWidget(self._btn_refresh, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

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

        self._empty = QLabel("Chưa có bàn nào. Hãy tạo bàn trong mục “Quản lý bàn”.")
        self._empty.setProperty("muted", True)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)
        root.addWidget(self._empty)

    def set_tables(self, tables: list[TableState]) -> None:
        self._clear_grid()
        if not tables:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)

        cols = 3
        # Group by table type name (UI requirement: phân loại theo loại bàn)
        def type_label(x: TableState) -> str:
            name = (x.type_name or "").strip()
            return name if name else "Chưa đặt loại"

        grouped: dict[str, list[TableState]] = {}
        for t in tables:
            grouped.setdefault(type_label(t), []).append(t)

        r = 0
        for group_name in sorted(grouped.keys(), key=lambda s: (s == "Chưa đặt loại", s.lower())):
            header = QLabel(group_name)
            header.setStyleSheet("font-size:14px;font-weight:800;")
            header.setProperty("muted", False)
            header.setContentsMargins(4, 8, 4, 0)
            self._grid.addWidget(header, r, 0, 1, cols)
            r += 1

            c = 0
            for t in sorted(grouped[group_name], key=lambda x: (x.status != "playing", x.name.lower(), x.table_id)):
                card = self._build_table_card(t)
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

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _badge(self, status: str) -> tuple[str, str]:
        s = (status or "empty").lower()
        if s == "playing":
            return "Đang chơi", "playing"
        if s == "maintenance":
            return "Bảo trì", "maintenance"
        return "Trống", "empty"

    def _build_table_card(self, t: TableState) -> QWidget:
        card = QFrame()
        card.setProperty("card", True)
        card.setProperty("tableStatus", (t.status or "empty").lower())
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setMinimumHeight(150)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)

        name = QLabel(t.name)
        name.setStyleSheet("font-size:16px;font-weight:800;")

        badge_text, badge_type = self._badge(t.status)
        badge = QLabel(badge_text)
        badge.setProperty("badge", True)
        badge.setProperty("badgeType", badge_type)

        top.addWidget(name, 1)
        top.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        meta = QLabel(f"{t.type_name or 'Chưa đặt loại'} • {t.price_per_hour:g}/h")
        meta.setProperty("muted", True)
        layout.addWidget(meta)

        if t.status == "playing" and t.active_session_id is not None:
            info = QLabel(f"Phiên #{t.active_session_id} • Bắt đầu: {t.active_start_time or ''} • Tạm tính: {t.active_total:,.0f}đ")
            info.setProperty("muted", True)
            info.setWordWrap(True)
            layout.addWidget(info)
        else:
            info = QLabel("Sẵn sàng phục vụ.")
            info.setProperty("muted", True)
            layout.addWidget(info)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)

        if (t.status or "empty").lower() == "empty":
            btn = QPushButton("Bắt đầu")
            btn.setProperty("variant", "primary")
            btn.clicked.connect(lambda _=False, table_id=t.table_id: self.start_requested.emit(table_id))
            actions.addWidget(btn)
        elif (t.status or "").lower() == "playing" and t.active_session_id is not None:
            btn_service = QPushButton("Thêm DV")
            btn_service.setProperty("variant", "primary")
            btn_service.clicked.connect(
                lambda _=False, sid=t.active_session_id: self.add_service_requested.emit(int(sid))
            )
            btn_end = QPushButton("Kết thúc")
            btn_end.setProperty("variant", "danger")
            btn_end.clicked.connect(lambda _=False, sid=t.active_session_id: self.end_requested.emit(int(sid)))
            actions.addWidget(btn_service)
            actions.addWidget(btn_end)
        else:
            btn = QPushButton("Đang bảo trì")
            btn.setEnabled(False)
            actions.addWidget(btn)

        layout.addLayout(actions)
        return card

