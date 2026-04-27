from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class RevenuePoint:
    day: str
    revenue: float


class RevenueBarChart(QWidget):
    """
    Lightweight revenue chart (no QtCharts dependency).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: list[RevenuePoint] = []
        self.setMinimumHeight(220)

    def set_points(self, points: list[RevenuePoint]) -> None:
        self._points = list(points)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        bg = QColor("#ffffff")
        p.fillRect(rect, bg)

        if not self._points:
            p.setPen(QColor("#64748b"))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Chưa có dữ liệu doanh thu.")
            p.end()
            return

        pad_l, pad_r, pad_t, pad_b = 48, 14, 14, 34
        plot = rect.adjusted(pad_l, pad_t, -pad_r, -pad_b)
        if plot.width() <= 20 or plot.height() <= 20:
            p.end()
            return

        values = [max(0.0, float(x.revenue or 0)) for x in self._points]
        vmax = max(values) if values else 0.0
        if vmax <= 0:
            vmax = 1.0

        axis = QColor("#e5e7eb")
        grid = QColor("#eef2f7")
        text = QColor("#334155")
        bar = QColor("#4293e6")

        # Grid + Y labels (3 lines)
        p.setPen(QPen(grid, 1))
        steps = 3
        fm = QFontMetrics(p.font())
        for i in range(steps + 1):
            y = plot.bottom() - int(plot.height() * i / steps)
            p.drawLine(plot.left(), y, plot.right(), y)
            val = vmax * i / steps
            label = f"{val:,.0f}đ".replace(",", ".")
            p.setPen(text)
            p.drawText(0, y - fm.height() // 2, pad_l - 8, fm.height(), Qt.AlignmentFlag.AlignRight, label)
            p.setPen(QPen(grid, 1))

        # Axis
        p.setPen(QPen(axis, 1))
        p.drawRect(plot)

        n = len(self._points)
        gap = 6
        bar_w = max(6, int((plot.width() - gap * (n - 1)) / max(1, n)))
        total_w = bar_w * n + gap * (n - 1)
        x0 = plot.left() + max(0, int((plot.width() - total_w) / 2))

        # Bars + X labels (sparse)
        for i, pt in enumerate(self._points):
            v = max(0.0, float(pt.revenue or 0))
            h = int((v / vmax) * plot.height())
            x = x0 + i * (bar_w + gap)
            y = plot.bottom() - h

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bar)
            p.drawRoundedRect(x, y, bar_w, h, 4, 4)

            # show label every ~5 bars + last bar
            show = (i == 0) or (i == n - 1) or (n <= 10) or (i % 5 == 0)
            if show:
                day = str(pt.day or "")
                # Accept both DATE (YYYY-MM-DD) and datetime; keep short form
                short = day[:10] if len(day) >= 10 else day
                p.setPen(text)
                p.drawText(x - 18, plot.bottom() + 6, bar_w + 36, fm.height(), Qt.AlignmentFlag.AlignHCenter, short)

        p.end()

