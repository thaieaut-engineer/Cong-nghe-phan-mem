from __future__ import annotations

# Tên role trong DB (không phân biệt hoa thường)
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_STAFF = "staff"

# Trang chỉ admin (và trang quản lý user)
ADMIN_ONLY_PAGE_NAMES = frozenset(
    {
        "pageEmployees",
        "pageRoles",
        "pageShifts",
        "pageStats",
        "pageUsers",
    }
)

# Role `user` (đăng ký công khai): chỉ vận hành — KHÔNG cấu hình bàn/dịch vụ/loại…
USER_ALLOWED_PAGE_NAMES = frozenset(
    {
        "pageDashboard",
        "pageSessions",
        "pageBookings",
        "pageInvoices",
    }
)

# Thứ tự trang trong QStackedWidget (main.ui) — phải khớp file UI
# Mục đầu chuỗi label dùng làm icon (đứng trước 2 space) cho sidebar dark navy.
_MENU_ORDER: list[tuple[str, str]] = [
    ("pageSessions", "▦  Sơ đồ bàn"),
    ("pageDashboard", "▤  Tổng quan"),
    ("pageInvoices", "🧾  Thu ngân"),
    ("pageBookings", "📅  Đặt lịch"),
    ("pageServices", "🛎  Phiếu minibar/dịch vụ"),
    ("pageServiceTypes", "🗂  Loại dịch vụ"),
    ("pageShifts", "🔁  Giao ca"),
    ("pageStats", "📈  Thống kê tổng hợp"),
    ("pageEmployees", "👥  Nhân viên"),
    ("pageRoles", "🏷  Chức vụ"),
    ("pageTables", "🎱  Thiết đặt bàn"),
    ("pageTableTypes", "💲  Cấu hình giá bàn"),
    ("pageUsers", "🔐  Tài khoản"),
]


def normalize_role(role_name: str | None) -> str:
    """Không có role trong DB → coi như tài khoản user thường."""
    if not role_name:
        return ROLE_USER
    s = str(role_name).strip().lower()
    return s if s else ROLE_USER


def is_admin(role_name: str | None) -> bool:
    return normalize_role(role_name) == ROLE_ADMIN


def is_restricted_user(role_name: str | None) -> bool:
    """Tài khoản `user` — quyền hẹp (không như staff)."""
    return normalize_role(role_name) == ROLE_USER


def staff_can_register_public() -> bool:
    """Đăng ký từ màn login: không tạo admin (xem RegisterService)."""
    return True


def menu_entries_for_role(role_name: str | None) -> list[tuple[str, str]]:
    """
    Trả về danh sách (object_name, label) cho menu sidebar, theo role.
    - admin: toàn bộ.
    - user: chỉ Tổng quan + Phiên + Đặt lịch + Hoá đơn (không chỉnh bàn/dịch vụ/loại…).
    - staff (và role khác, trừ admin): vận hành đầy đủ trừ các trang admin.
    """
    r = normalize_role(role_name)
    if r == ROLE_ADMIN:
        return list(_MENU_ORDER)

    out: list[tuple[str, str]] = []
    for page_name, label in _MENU_ORDER:
        if page_name == "pageUsers":
            continue
        if page_name in ADMIN_ONLY_PAGE_NAMES:
            continue
        if r == ROLE_USER and page_name not in USER_ALLOWED_PAGE_NAMES:
            continue
        out.append((page_name, label))
    return out