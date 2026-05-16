from __future__ import annotations

VND_SUFFIX = "VNĐ"


def format_vnd(amount: float, *, compact: bool = False) -> str:
    """Định dạng số tiền Việt Nam (đồng), ví dụ: 50.000 VNĐ."""
    n = int(round(float(amount or 0)))
    if compact and abs(n) >= 1000:
        k = n / 1000.0
        if n % 1000 == 0:
            text = f"{int(k)}K"
        else:
            text = f"{k:.1f}K".replace(".", ",")
        return f"{text} {VND_SUFFIX}"
    s = f"{n:,}".replace(",", ".")
    return f"{s} {VND_SUFFIX}"
