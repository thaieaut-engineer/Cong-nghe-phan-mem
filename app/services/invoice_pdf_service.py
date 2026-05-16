from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from app.core.currency import format_vnd


def export_invoice_pdf(
    *,
    out_path: str,
    invoice: dict,
    session: dict | None,
    items: list[dict],
    shop_name: str = "Billiards Manager",
) -> str:
    path = Path(out_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    c = Canvas(str(path), pagesize=A4)
    w, h = A4
    x = 18 * mm
    y = h - 18 * mm

    def line(text: str, dy: float = 6 * mm, font: str = "Helvetica", size: int = 11) -> None:
        nonlocal y
        c.setFont(font, size)
        c.drawString(x, y, text)
        y -= dy

    line(shop_name, dy=8 * mm, font="Helvetica-Bold", size=16)
    line(f"HÓA ĐƠN #{invoice.get('id')}", dy=8 * mm, font="Helvetica-Bold", size=13)

    created_at = invoice.get("created_at")
    if isinstance(created_at, datetime):
        created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
    else:
        created_at_str = str(created_at or "")

    line(f"Thời gian: {created_at_str}")
    line(f"Bàn: {invoice.get('table_name') or (session.get('table_name') if session else '')}")
    line(f"Phiên: {invoice.get('session_id')}")
    y -= 4 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Dịch vụ")
    c.drawRightString(w - x, y, "Thành tiền")
    y -= 6 * mm
    c.setLineWidth(0.5)
    c.line(x, y, w - x, y)
    y -= 6 * mm

    c.setFont("Helvetica", 11)
    total_items = 0.0
    for it in items:
        name = str(it.get("service_name") or "")
        qty = int(it.get("quantity") or 0)
        unit = float(it.get("unit_price") or 0)
        amount = qty * unit
        total_items += amount
        c.drawString(x, y, f"{name} x{qty} @ {format_vnd(unit)}")
        c.drawRightString(w - x, y, format_vnd(amount))
        y -= 6 * mm
        if y < 30 * mm:
            c.showPage()
            y = h - 18 * mm
            c.setFont("Helvetica", 11)

    y -= 3 * mm
    c.setFont("Helvetica-Bold", 12)
    total = float(invoice.get("total") or total_items or 0)
    c.drawRightString(w - x, y, f"Tổng: {format_vnd(total)}")

    c.showPage()
    c.save()
    return str(path)

