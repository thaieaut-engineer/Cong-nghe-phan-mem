from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from PySide6.QtCore import QDate, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.currency import format_vnd


@dataclass(frozen=True)
class RevenuePoint:
    day: str
    revenue: float


def fill_revenue_range(points: list[RevenuePoint], start: date, end: date) -> list[RevenuePoint]:
    """Bổ sung các ngày trong [start, end] không có doanh thu = 0."""
    by_day: dict[str, float] = {}
    for pt in points:
        key = str(pt.day or "")[:10]
        if key:
            by_day[key] = float(pt.revenue or 0)

    if start > end:
        start, end = end, start

    filled: list[RevenuePoint] = []
    d = start
    while d <= end:
        filled.append(RevenuePoint(day=d.isoformat(), revenue=by_day.get(d.isoformat(), 0.0)))
        d += timedelta(days=1)
    return filled


def fill_revenue_days(points: list[RevenuePoint], *, days: int = 30) -> list[RevenuePoint]:
    end = date.today()
    start = end - timedelta(days=max(0, days - 1))
    return fill_revenue_range(points, start, end)


class RevenueLineChart(QWidget):
    """Biểu đồ đường doanh thu theo ngày."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: list[RevenuePoint] = []
        self.setMinimumHeight(260)

    def set_points(self, points: list[RevenuePoint], *, start: date | None = None, end: date | None = None) -> None:
        pts = list(points)
        if start is not None and end is not None:
            pts = fill_revenue_range(pts, start, end)
        self._points = pts
        self.update()

    def sizeHint(self) -> QSize:  # noqa: D102
        return QSize(520, 260)

    @staticmethod
    def _axis_amount_label(value: float) -> str:
        return format_vnd(value, compact=True)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = self.rect()
        p.fillRect(rect, QColor("#ffffff"))

        if not self._points:
            p.setPen(QColor("#64748b"))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Chưa có dữ liệu doanh thu.")
            p.end()
            return

        values = [max(0.0, float(x.revenue or 0)) for x in self._points]
        vmax = max(values) if values else 0.0
        if vmax <= 0:
            vmax = 1.0

        steps = 4
        axis_labels = [self._axis_amount_label(vmax * i / steps) for i in range(steps + 1)]
        fm = QFontMetrics(p.font())
        pad_l = max(56, max(fm.horizontalAdvance(lbl) for lbl in axis_labels) + 14)
        pad_r, pad_b = 16, 42
        pad_t = max(18, fm.height() + 8)

        plot = rect.adjusted(pad_l, pad_t, -pad_r, -pad_b)
        if plot.width() <= 40 or plot.height() <= 40:
            p.end()
            return

        grid = QColor("#eef2f7")
        axis_c = QColor("#e2e8f0")
        text = QColor("#475569")
        line_c = QColor("#3b82f6")
        fill_top = QColor("#3b82f6")
        fill_top.setAlpha(70)
        fill_bottom = QColor("#3b82f6")
        fill_bottom.setAlpha(8)
        dot_c = QColor("#2563eb")
        dot_border = QColor("#ffffff")

        for i in range(steps + 1):
            y = plot.bottom() - int(plot.height() * i / steps)
            p.setPen(QPen(grid, 1))
            p.drawLine(plot.left(), y, plot.right(), y)
            p.setPen(text)
            p.drawText(
                8,
                y - fm.height() // 2,
                pad_l - 12,
                fm.height() + 2,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                axis_labels[i],
            )

        p.setPen(QPen(axis_c, 1))
        p.drawLine(plot.left(), plot.top(), plot.left(), plot.bottom())
        p.drawLine(plot.left(), plot.bottom(), plot.right(), plot.bottom())

        n = len(self._points)
        if n == 0:
            p.end()
            return

        def xy(i: int, val: float) -> tuple[float, float]:
            if n == 1:
                x = plot.left() + plot.width() / 2
            else:
                x = plot.left() + (plot.width() * i / (n - 1))
            y = plot.bottom() - (val / vmax) * plot.height()
            return x, y

        coords = [xy(i, v) for i, v in enumerate(values)]

        # Vùng tô dưới đường
        if n >= 2:
            area = QPainterPath()
            area.moveTo(coords[0][0], plot.bottom())
            area.lineTo(coords[0][0], coords[0][1])
            for x, y in coords[1:]:
                area.lineTo(x, y)
            area.lineTo(coords[-1][0], plot.bottom())
            area.closeSubpath()
            grad = QLinearGradient(0, plot.top(), 0, plot.bottom())
            grad.setColorAt(0.0, fill_top)
            grad.setColorAt(1.0, fill_bottom)
            p.fillPath(area, grad)

        # Đường nối
        path = QPainterPath()
        path.moveTo(coords[0][0], coords[0][1])
        for x, y in coords[1:]:
            path.lineTo(x, y)
        p.setPen(QPen(line_c, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Điểm + nhãn (thưa khi nhiều ngày)
        label_step = 1 if n <= 12 else (3 if n <= 31 else max(1, n // 10))
        p.setClipping(False)
        peak_i = max(range(n), key=lambda i: values[i])

        for i, (x, y) in enumerate(coords):
            p.setPen(QPen(dot_border, 2))
            p.setBrush(dot_c)
            r = 4 if values[i] > 0 else 3
            p.drawEllipse(int(x - r), int(y - r), r * 2, r * 2)

            show_lbl = i == 0 or i == n - 1 or i == peak_i or (i % label_step == 0)
            if show_lbl and values[i] > 0:
                val_lbl = format_vnd(values[i], compact=True)
                tw = fm.horizontalAdvance(val_lbl)
                tx = max(2, min(int(x - tw / 2), plot.right() - tw - 2))
                ty = int(y) - fm.height() - 8
                if ty < plot.top():
                    ty = int(y) + 8
                p.setPen(QColor("#1e3a8a"))
                p.drawText(tx, ty, tw, fm.height() + 2, Qt.AlignmentFlag.AlignCenter, val_lbl)

            show_x = i == 0 or i == n - 1 or (i % label_step == 0)
            if show_x:
                day = str(self._points[i].day or "")
                short = day[5:10] if len(day) >= 10 else day
                p.setPen(QColor("#64748b"))
                p.drawText(
                    int(x) - 22,
                    plot.bottom() + 8,
                    44,
                    fm.height() + 2,
                    Qt.AlignmentFlag.AlignHCenter,
                    short,
                )

        if max(values) <= 0:
            p.setPen(QColor("#94a3b8"))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "Chưa có doanh thu trong khoảng thời gian này")

        p.end()


class RevenueChartPanel(QWidget):
    """Biểu đồ doanh thu + chọn khoảng thời gian."""

    period_changed = Signal()

    _PRESETS: tuple[tuple[str, int], ...] = (
        ("7 ngày", 7),
        ("14 ngày", 14),
        ("30 ngày", 30),
        ("90 ngày", 90),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._chart = RevenueLineChart()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._title = QLabel("Doanh thu theo ngày")
        self._title.setProperty("sectionTitle", True)
        header.addWidget(self._title, 1)

        self._combo = QComboBox()
        self._combo.setMinimumWidth(120)
        for label, days in self._PRESETS:
            self._combo.addItem(label, days)
        self._combo.addItem("Tùy chọn", "custom")
        self._combo.setCurrentIndex(2)  # mặc định 30 ngày
        header.addWidget(QLabel("Khoảng thời gian:"))
        header.addWidget(self._combo)
        root.addLayout(header)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        self._date_from.setDate(QDate.currentDate().addDays(-29))
        self._date_to.setDate(QDate.currentDate())

        self._btn_apply = QPushButton("Xem")
        self._btn_apply.setProperty("variant", "primary")

        custom_row.addWidget(QLabel("Từ"))
        custom_row.addWidget(self._date_from)
        custom_row.addWidget(QLabel("đến"))
        custom_row.addWidget(self._date_to)
        custom_row.addWidget(self._btn_apply)
        custom_row.addStretch(1)

        self._custom_wrap = QFrame()
        self._custom_wrap.setLayout(custom_row)
        self._custom_wrap.setVisible(False)
        root.addWidget(self._custom_wrap)

        root.addWidget(self._chart, 1)

        self._combo.currentIndexChanged.connect(self._on_preset_changed)
        self._btn_apply.clicked.connect(self.period_changed.emit)

    def chart(self) -> RevenueLineChart:
        return self._chart

    def _on_preset_changed(self) -> None:
        custom = self._combo.currentData() == "custom"
        self._custom_wrap.setVisible(custom)
        if not custom:
            self.period_changed.emit()

    def selected_range(self) -> tuple[date, date]:
        data = self._combo.currentData()
        if data == "custom":
            d0 = self._date_from.date().toPython()
            d1 = self._date_to.date().toPython()
            return (d0, d1) if d0 <= d1 else (d1, d0)
        days = int(data)
        end = date.today()
        start = end - timedelta(days=max(0, days - 1))
        return start, end

    def range_label(self) -> str:
        start, end = self.selected_range()
        if start == end:
            return start.strftime("%d/%m/%Y")
        return f"{start.strftime('%d/%m/%Y')} – {end.strftime('%d/%m/%Y')}"

    def refresh_title(self) -> None:
        self._title.setText(f"Doanh thu theo ngày ({self.range_label()})")


# Giữ tên cũ để tương thích import
RevenueBarChart = RevenueLineChart
