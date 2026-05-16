from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, Slot, QTime
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDateTimeEdit,
    QSpinBox,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QScrollArea,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QTableView,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.currency import format_vnd
from app.core.ui import get_child, load_ui
from app.core.db import Database
from app.core.image_store import resolve_image_path, store_image
from app.core.permissions import is_admin, menu_entries_for_role, normalize_role
from app.repositories.activity_log_repository import ActivityLogRepository
from app.repositories.booking_repository import BookingRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.payment_group_repository import PaymentGroupRepository
from app.repositories.power_log_repository import PowerLogRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.service_repository import ServiceRepository
from app.repositories.service_type_repository import ServiceTypeRepository
from app.repositories.shift_handover_repository import ShiftHandoverRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.stats_repository import StatsRepository
from app.repositories.table_repository import TableRepository
from app.repositories.table_type_repository import TableTypeRepository
from app.repositories.user_repository import UserRepository
from app.services.activity_log_service import ActivityLogService
from app.widgets.table_helpers import build_model, configure_table_view, selected_row_data
from app.widgets.sessions_board import SessionsBoard, TableState
from app.widgets.table_features_dialog import (
    ACTION_DETAIL,
    ACTION_GROUP_PAY,
    ACTION_MEMBER,
    ACTION_PAYMENT,
    ACTION_POWER_HISTORY,
    ACTION_SERVICE,
    ACTION_TRANSFER,
    ACTION_USER_HISTORY,
    BillService,
    BillSummary,
    TableFeaturesDialog,
)
from app.widgets.feature_dialogs import (
    GroupPaymentDialog,
    HistoryDialog,
    MemberChooserDialog,
)
from app.widgets.revenue_chart import RevenueChartPanel, RevenuePoint
from app.services.invoice_pdf_service import export_invoice_pdf
from app.services.register_service import RegisterService


class MainWindow(QMainWindow):
    def __init__(self, user: dict, db: Database, close_result: list[str] | None = None) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        # main.py truyền ["relogin"] hoặc ["quit"] sau khi đóng — Đăng xuất vs nút X
        self._close_result = close_result if close_result is not None else ["relogin"]
        self._logout_via_button = False
        self._user = user
        self._db = db
        self._table_types_repo = TableTypeRepository(db)
        self._tables_repo = TableRepository(db)
        self._roles_repo = RoleRepository(db)
        self._service_types_repo = ServiceTypeRepository(db)
        self._services_repo = ServiceRepository(db)
        self._employees_repo = EmployeeRepository(db)
        self._shifts_repo = ShiftRepository(db)
        self._bookings_repo = BookingRepository(db)
        self._sessions_repo = SessionRepository(db)
        self._invoices_repo = InvoiceRepository(db)
        self._stats_repo = StatsRepository(db)
        self._users_repo = UserRepository(db)
        self._members_repo = MemberRepository(db)
        self._power_repo = PowerLogRepository(db)
        self._activity_repo = ActivityLogRepository(db)
        self._payment_groups_repo = PaymentGroupRepository(db)
        self._expenses_repo = ExpenseRepository(db)
        self._inventory_repo = InventoryRepository(db)
        self._handovers_repo = ShiftHandoverRepository(db)
        self._activity = ActivityLogService(self._activity_repo)
        self._register = RegisterService(self._users_repo)

        self._table_types_cache: list[dict] = []
        self._tables_cache: list[dict] = []
        self._roles_cache: list[dict] = []
        self._service_types_cache: list[dict] = []
        self._services_cache: list[dict] = []
        self._employees_cache: list[dict] = []
        self._shifts_cache: list[dict] = []
        self._bookings_cache: list[dict] = []
        self._sessions_cache: list[dict] = []
        self._invoices_cache: list[dict] = []
        self._users_cache: list[dict] = []

        self.setWindowTitle("Billiards Manager")
        self._ui: QWidget = load_ui("main.ui", self)
        self.setCentralWidget(self._ui)
        self._apply_main_window_layout_stretch()

        self._lbl_user = get_child(self._ui, QLabel, "lblUser")
        self._list_menu = get_child(self._ui, QListWidget, "listMenu")
        self._btn_logout = get_child(self._ui, QPushButton, "btnLogout")
        self._stacked = get_child(self._ui, QStackedWidget, "stackedPages")
        self._lbl_top_title = get_child(self._ui, QLabel, "lblTopTitle")

        rn = normalize_role(user.get("role_name"))
        self._lbl_user.setText(f"Xin chào, {user.get('username', '')}\n(Quyền: {rn})")
        self._btn_logout.clicked.connect(self._on_logout)

        self._activity.log(user, "login", detail=f"Đăng nhập với quyền {rn}")

        self._init_dashboard_page()
        self._init_table_types_page()
        self._init_tables_page()
        self._init_service_types_page()
        self._init_services_page()
        self._init_roles_page()
        self._init_employees_page()
        self._init_shifts_page()
        self._init_bookings_page()
        self._init_sessions_page()
        self._init_invoices_page()
        self._init_stats_page()
        if is_admin(user.get("role_name")):
            self._init_users_page()

        self._build_role_menu()
        self._list_menu.currentRowChanged.connect(self._on_menu_changed)
        if self._list_menu.count() > 0:
            self._list_menu.setCurrentRow(0)

    def _stacked_index_for_page(self, page_object_name: str) -> int:
        for i in range(self._stacked.count()):
            w = self._stacked.widget(i)
            if w is not None and w.objectName() == page_object_name:
                return i
        return -1

    def _build_role_menu(self) -> None:
        self._list_menu.clear()
        for page_name, label in menu_entries_for_role(self._user.get("role_name")):
            idx = self._stacked_index_for_page(page_name)
            if idx < 0:
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self._list_menu.addItem(item)
        if self._list_menu.count() > 0:
            first = self._list_menu.item(0)
            if first is not None:
                si = first.data(Qt.ItemDataRole.UserRole)
                if si is not None:
                    self._stacked.setCurrentIndex(int(si))

    @Slot(int)
    def _on_menu_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self._list_menu.item(row)
        if item is None:
            return
        si = item.data(Qt.ItemDataRole.UserRole)
        if si is None:
            return
        if hasattr(self, "_lbl_top_title") and self._lbl_top_title is not None:
            label = item.text()
            if "  " in label:
                label = label.split("  ", 1)[1].strip()
            self._lbl_top_title.setText(label)
        self._stacked.setCurrentIndex(int(si))

    def _on_logout(self) -> None:
        try:
            self._activity.log(self._user, "logout", detail="Đăng xuất bằng nút")
        except Exception:
            pass
        self._logout_via_button = True
        self.close()

    def closeEvent(self, event) -> None:
        if self._logout_via_button:
            self._logout_via_button = False
            self._close_result[0] = "relogin"
            event.accept()
            return super().closeEvent(event)
        self._close_result[0] = "quit"
        QApplication.quit()
        event.accept()
        super().closeEvent(event)

    def _apply_main_window_layout_stretch(self) -> None:
        root = self._ui.layout()
        if root is not None and root.count() >= 2:
            root.setStretch(0, 0)
            root.setStretch(1, 1)
        content = get_child(self._ui, QWidget, "content")
        cl = content.layout()
        if cl is not None and cl.count() >= 2:
            cl.setStretch(0, 0)
            cl.setStretch(1, 1)

    def _replace_page_with_crud(self, page_object_name: str, title: str) -> QWidget:
        page = get_child(self._ui, QWidget, page_object_name)
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        crud = load_ui("crud_page.ui", page)
        get_child(crud, QLabel, "lblTitle").setText(title)

        table_view = get_child(crud, QTableView, "tableView")
        configure_table_view(table_view)

        outer = crud.layout()
        if outer is not None and outer.count() >= 1:
            outer.setStretch(0, 1)
        card = get_child(crud, QFrame, "card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card_layout = card.layout()
        if card_layout is not None and card_layout.count() >= 3:
            card_layout.setStretch(0, 0)
            card_layout.setStretch(1, 0)
            card_layout.setStretch(2, 1)

        layout.addWidget(crud)
        if layout.count() >= 1:
            layout.setStretch(layout.count() - 1, 1)
        return crud

    def _replace_page_with_crud_grid(self, page_object_name: str, title: str) -> QWidget:
        page = get_child(self._ui, QWidget, page_object_name)
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        crud = load_ui("crud_grid_page.ui", page)
        get_child(crud, QLabel, "lblTitle").setText(title)

        grid_list = get_child(crud, QListWidget, "gridList")
        grid_list.setUniformItemSizes(True)

        outer = crud.layout()
        if outer is not None and outer.count() >= 1:
            outer.setStretch(0, 1)
        card = get_child(crud, QFrame, "card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card_layout = card.layout()
        if card_layout is not None and card_layout.count() >= 3:
            card_layout.setStretch(0, 0)
            card_layout.setStretch(1, 0)
            card_layout.setStretch(2, 1)

        layout.addWidget(crud)
        if layout.count() >= 1:
            layout.setStretch(layout.count() - 1, 1)
        return crud

    def _wire_grid_five_columns(self, grid: QListWidget, *, row_height: int, icon_size: QSize) -> None:
        grid._grid_row_height = row_height  # type: ignore[attr-defined]
        grid._grid_icon_size = icon_size  # type: ignore[attr-defined]
        grid._grid_columns = 5  # type: ignore[attr-defined]
        grid.setIconSize(icon_size)
        grid.setCursor(Qt.CursorShape.PointingHandCursor)
        grid.viewport().installEventFilter(self)
        self._update_grid_cell_size(grid)

    def _update_grid_cell_size(self, grid: QListWidget) -> None:
        cols = int(getattr(grid, "_grid_columns", 5))
        row_h = int(getattr(grid, "_grid_row_height", 130))
        icon_sz = getattr(grid, "_grid_icon_size", QSize(64, 64))
        grid.setIconSize(icon_sz)
        vw = grid.viewport().width()
        if vw < 80:
            return
        s = grid.spacing()
        cell_w = max(120, (vw - (cols - 1) * s) // cols)
        grid.setGridSize(QSize(cell_w, row_h))
        cell = grid.gridSize()
        if not cell.isValid():
            return
        for i in range(grid.count()):
            it = grid.item(i)
            if it is not None:
                it.setSizeHint(cell)

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Resize:
            for name in ("_tt_grid", "_tb_grid", "_st_grid", "_sv_grid"):
                g = getattr(self, name, None)
                if g is not None and g.viewport() is obj:
                    self._update_grid_cell_size(g)
                    break
        return super().eventFilter(obj, event)

    def _selected_grid_item(self, grid: QListWidget) -> dict | None:
        it = grid.currentItem()
        if it is None:
            return None
        data = it.data(Qt.ItemDataRole.UserRole)
        return dict(data) if isinstance(data, dict) else None

    def _set_grid_items(self, grid: QListWidget, items: list[dict], build_text) -> None:
        self._update_grid_cell_size(grid)
        grid.clear()
        cell = grid.gridSize()
        for d in items:
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, d)
            it.setText(build_text(d))
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            if cell.isValid():
                it.setSizeHint(cell)
            icon, tooltip = self._icon_for_grid_item(d)
            if icon is not None:
                it.setIcon(icon)
            if tooltip:
                it.setToolTip(tooltip)
            bg = self._background_for_grid_item(d)
            if bg is not None:
                it.setData(Qt.ItemDataRole.BackgroundRole, QBrush(bg))
            grid.addItem(it)
        self._update_grid_cell_size(grid)

    def _format_vnd(self, amount: float) -> str:
        return format_vnd(amount)

    # ---------- Dashboard ----------
    def _init_dashboard_page(self) -> None:
        from datetime import datetime

        page = get_child(self._ui, QWidget, "pageDashboard")
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)

        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(0)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(14)

        # ===== Header =====
        header_card = QFrame()
        header_card.setProperty("card", True)
        hcl = QHBoxLayout(header_card)
        hcl.setContentsMargins(18, 14, 18, 14)
        hcl.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(2)
        title = QLabel("Tổng quan hoạt động")
        title.setStyleSheet("font-size:20px;font-weight:800;")
        username = (self._user or {}).get("username") or "—"
        greet = QLabel(
            f"Xin chào, <b>{username}</b> · Hôm nay là {datetime.now().strftime('%A, %d/%m/%Y')}"
        )
        greet.setProperty("greeting", True)
        greet.setTextFormat(Qt.TextFormat.RichText)
        left.addWidget(title)
        left.addWidget(greet)

        self._dash_btn_refresh = QPushButton("⟳  Làm mới")
        self._dash_btn_refresh.setProperty("variant", "primary")
        self._dash_btn_refresh.clicked.connect(self._reload_dashboard)

        hcl.addLayout(left, 1)
        hcl.addWidget(self._dash_btn_refresh, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(header_card)

        # ===== Section 1: Trạng thái bàn =====
        sec1_title = QLabel("Trạng thái bàn")
        sec1_title.setProperty("sectionTitle", True)
        outer.addWidget(sec1_title)

        self._dash_kpi: dict[str, QLabel] = {}
        row1 = QGridLayout()
        row1.setHorizontalSpacing(12)
        row1.setVerticalSpacing(12)

        tables_kpis = [
            ("tables_total", "🎱", "Tổng số bàn", "blue"),
            ("tables_empty", "🟢", "Bàn trống", "green"),
            ("tables_playing", "🟠", "Đang chơi", "orange"),
            ("tables_maintenance", "🟡", "Bảo trì", "yellow"),
        ]
        for i, (key, icon, label, accent) in enumerate(tables_kpis):
            card_kpi, value_lbl = self._make_kpi_card(icon, label, accent)
            self._dash_kpi[key] = value_lbl
            row1.addWidget(card_kpi, 0, i)
        for c in range(len(tables_kpis)):
            row1.setColumnStretch(c, 1)
        outer.addLayout(row1)

        # ===== Section 2: Tài chính hôm nay =====
        sec2_title = QLabel("Tài chính hôm nay")
        sec2_title.setProperty("sectionTitle", True)
        outer.addWidget(sec2_title)

        row2 = QGridLayout()
        row2.setHorizontalSpacing(12)
        row2.setVerticalSpacing(12)
        money_kpis = [
            ("revenue_today", "💰", "Doanh thu hôm nay", "green"),
            ("expense_today", "📉", "Chi phí hôm nay", "red"),
            ("invoices_today", "🧾", "Hoá đơn hôm nay", "blue"),
            ("bookings_today", "📅", "Đặt lịch hôm nay", "purple"),
        ]
        for i, (key, icon, label, accent) in enumerate(money_kpis):
            card_kpi, value_lbl = self._make_kpi_card(icon, label, accent)
            self._dash_kpi[key] = value_lbl
            row2.addWidget(card_kpi, 0, i)
        for c in range(len(money_kpis)):
            row2.setColumnStretch(c, 1)
        outer.addLayout(row2)

        # ===== Section 3: Hoạt động & Cảnh báo =====
        sec3_title = QLabel("Hoạt động & Cảnh báo")
        sec3_title.setProperty("sectionTitle", True)
        outer.addWidget(sec3_title)

        row3 = QGridLayout()
        row3.setHorizontalSpacing(12)
        row3.setVerticalSpacing(12)
        ops_kpis = [
            ("active_sessions", "▶", "Phiên đang chạy", "orange"),
            ("members_total", "🪪", "Thành viên", "purple"),
            ("low_stock", "📦", "Kho cảnh báo", "red"),
            ("revenue_month", "📈", "Doanh thu tháng", "green"),
        ]
        for i, (key, icon, label, accent) in enumerate(ops_kpis):
            card_kpi, value_lbl = self._make_kpi_card(icon, label, accent)
            self._dash_kpi[key] = value_lbl
            row3.addWidget(card_kpi, 0, i)
        for c in range(len(ops_kpis)):
            row3.setColumnStretch(c, 1)
        outer.addLayout(row3)

        # ===== Chart + Activity panel side by side =====
        chart_row = QHBoxLayout()
        chart_row.setSpacing(12)

        chart_card = QFrame()
        chart_card.setProperty("card", True)
        chart_ly = QVBoxLayout(chart_card)
        chart_ly.setContentsMargins(14, 14, 14, 14)
        chart_ly.setSpacing(10)
        self._dash_rev_panel = RevenueChartPanel()
        self._dash_rev_panel.period_changed.connect(self._reload_dashboard_chart)
        chart_ly.addWidget(self._dash_rev_panel, 1)

        activity_card = QFrame()
        activity_card.setProperty("card", True)
        act_ly = QVBoxLayout(activity_card)
        act_ly.setContentsMargins(14, 14, 14, 14)
        act_ly.setSpacing(10)
        act_title = QLabel("Hoạt động gần đây")
        act_title.setProperty("sectionTitle", True)
        act_ly.addWidget(act_title)
        self._dash_activity_list = QListWidget()
        self._dash_activity_list.setMinimumHeight(220)
        self._dash_activity_list.setStyleSheet(
            "QListWidget{border:none;background:transparent;}"
            "QListWidget::item{padding:8px 4px;border-bottom:1px solid #eef2f7;}"
        )
        act_ly.addWidget(self._dash_activity_list, 1)

        chart_row.addWidget(chart_card, 2)
        chart_row.addWidget(activity_card, 1)
        outer.addLayout(chart_row)

        # ===== Bottom: Hoá đơn gần đây + Đặt lịch sắp tới =====
        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)

        self._dash_recent_invoices = QTableView()
        configure_table_view(self._dash_recent_invoices)
        self._dash_recent_invoices.setMinimumHeight(200)

        self._dash_upcoming_bookings = QTableView()
        configure_table_view(self._dash_upcoming_bookings)
        self._dash_upcoming_bookings.setMinimumHeight(200)

        left_card = QFrame()
        left_card.setProperty("card", True)
        left_ly = QVBoxLayout(left_card)
        left_ly.setContentsMargins(14, 14, 14, 14)
        left_ly.setSpacing(10)
        left_title = QLabel("🧾  Hoá đơn gần đây")
        left_title.setProperty("sectionTitle", True)
        left_ly.addWidget(left_title)
        left_ly.addWidget(self._dash_recent_invoices, 1)

        right_card = QFrame()
        right_card.setProperty("card", True)
        right_ly = QVBoxLayout(right_card)
        right_ly.setContentsMargins(14, 14, 14, 14)
        right_ly.setSpacing(10)
        right_title = QLabel("📅  Đặt lịch sắp tới")
        right_title.setProperty("sectionTitle", True)
        right_ly.addWidget(right_title)
        right_ly.addWidget(self._dash_upcoming_bookings, 1)

        tables_row.addWidget(left_card, 1)
        tables_row.addWidget(right_card, 1)
        outer.addLayout(tables_row)

        scroll_host = QWidget()
        scroll_host.setLayout(outer)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(scroll_host)
        layout.addWidget(scroll, 1)

        self._reload_dashboard()

    def _make_kpi_card(self, icon: str, label_text: str, accent: str) -> tuple[QFrame, QLabel]:
        w = QFrame()
        w.setProperty("kpi", True)
        w.setProperty("accent", accent)
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        w.setMinimumHeight(94)
        ly = QHBoxLayout(w)
        ly.setContentsMargins(14, 10, 14, 10)
        ly.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setProperty("kpiIcon", True)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        t = QLabel(label_text)
        t.setProperty("kpiLabel", True)
        t.setWordWrap(True)
        v = QLabel("—")
        v.setProperty("kpiValue", True)
        text_col.addWidget(t)
        text_col.addWidget(v)

        ly.addWidget(icon_lbl, 0)
        ly.addLayout(text_col, 1)
        return w, v

    def _reload_dashboard(self) -> None:
        from datetime import date

        try:
            kpi = self._stats_repo.dashboard_kpis()
            invoices = self._stats_repo.recent_invoices(8)
            bookings = self._stats_repo.upcoming_bookings(8)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return

        def set_kpi(key: str, value: object, *, money: bool = False) -> None:
            lbl = self._dash_kpi.get(key)
            if lbl is None:
                return
            if money:
                lbl.setText(self._format_vnd(float(value or 0)))
            else:
                lbl.setText(
                    str(int(value)) if isinstance(value, (int, float)) else (str(value) if value is not None else "0")
                )

        set_kpi("tables_total", kpi.get("tables_total", 0))
        set_kpi("tables_playing", kpi.get("tables_playing", 0))
        set_kpi("tables_empty", kpi.get("tables_empty", 0))
        set_kpi("tables_maintenance", kpi.get("tables_maintenance", 0))
        set_kpi("active_sessions", kpi.get("active_sessions", 0))
        set_kpi("revenue_today", kpi.get("revenue_today", 0), money=True)
        set_kpi("invoices_today", kpi.get("invoices_today", 0))
        set_kpi("bookings_today", kpi.get("bookings_today", 0))

        # KPI mở rộng: chi phí hôm nay, thành viên, kho cảnh báo, doanh thu tháng
        today = date.today()
        try:
            expense_today = self._expenses_repo.total_by_range(today.isoformat(), today.isoformat())
        except Exception:
            expense_today = 0.0
        set_kpi("expense_today", expense_today, money=True)

        try:
            members_total = len(self._members_repo.list_all())
        except Exception:
            members_total = 0
        set_kpi("members_total", members_total)

        try:
            low_stock_n = len(self._inventory_repo.low_stock())
        except Exception:
            low_stock_n = 0
        set_kpi("low_stock", low_stock_n)

        try:
            month_start = today.replace(day=1).isoformat()
            row = self._db.fetch_one(
                "SELECT COALESCE(SUM(total), 0) AS s FROM invoices WHERE DATE(created_at) >= %s",
                (month_start,),
            )
            revenue_month = float((row or {}).get("s") or 0)
        except Exception:
            revenue_month = 0.0
        set_kpi("revenue_month", revenue_month, money=True)

        # ----- Bảng hoá đơn gần đây -----
        inv_rows: list[list[object]] = []
        for r in invoices:
            inv_rows.append(
                [
                    r.get("id"),
                    r.get("table_name") or "—",
                    self._format_vnd(float(r.get("total") or 0)),
                    str(r.get("created_at") or ""),
                ]
            )
        self._dash_recent_invoices.setModel(build_model(["Mã HĐ", "Bàn", "Tổng", "Tạo lúc"], inv_rows))
        self._dash_recent_invoices.resizeColumnsToContents()

        # ----- Bảng đặt lịch sắp tới -----
        bk_rows: list[list[object]] = []
        for r in bookings:
            phone = str(r.get("phone") or "").strip()
            bk_rows.append(
                [
                    r.get("id"),
                    r.get("table_name") or "—",
                    r.get("customer_name") or "",
                    phone if phone else "—",
                    str(r.get("start_time") or ""),
                ]
            )
        self._dash_upcoming_bookings.setModel(build_model(["Mã", "Bàn", "Khách", "SĐT", "Bắt đầu"], bk_rows))
        self._dash_upcoming_bookings.resizeColumnsToContents()

        # ----- Activity feed -----
        if hasattr(self, "_dash_activity_list") and self._dash_activity_list is not None:
            self._dash_activity_list.clear()
            try:
                acts = self._activity_repo.list_recent(limit=20)
            except Exception:
                acts = []
            if not acts:
                it = QListWidgetItem("Chưa có hoạt động nào.")
                it.setForeground(QBrush(QColor("#94a3b8")))
                self._dash_activity_list.addItem(it)
            else:
                for r in acts:
                    when = str(r.get("created_at") or "")
                    who = str(r.get("username") or "—")
                    action = self._activity_action_label(str(r.get("action") or ""))
                    detail = str(r.get("detail") or "")
                    text = f"[{when}]  {who}  ·  {action}"
                    if detail:
                        text += f"  —  {detail}"
                    self._dash_activity_list.addItem(QListWidgetItem(text))

        self._reload_dashboard_chart()

    def _reload_dashboard_chart(self) -> None:
        if not hasattr(self, "_dash_rev_panel"):
            return
        start, end = self._dash_rev_panel.selected_range()
        try:
            rev = self._stats_repo.revenue_by_date_range(start, end)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi biểu đồ", str(e))
            return
        pts = [RevenuePoint(day=str(r.get("day") or ""), revenue=float(r.get("revenue") or 0)) for r in rev]
        self._dash_rev_panel.chart().set_points(pts, start=start, end=end)
        self._dash_rev_panel.refresh_title()

    def _table_status_label(self, status: str) -> str:
        status_map = {"empty": "Trống", "playing": "Đang chơi", "maintenance": "Bảo trì"}
        return status_map.get(status, status)

    def _table_status_color(self, status: str) -> QColor:
        # soft background tints for cards
        if status == "playing":
            return QColor("#fff7d6")  # yellow
        if status == "maintenance":
            return QColor("#ffe4e6")  # red
        return QColor("#e9f9ee")  # green (empty default)

    def _render_table_icon(self, status: str) -> QIcon:
        # Draw a simple billiards-table icon programmatically.
        w, h = 64, 64
        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Outer frame
        frame = QColor("#1f2937")
        felt = QColor("#16a34a") if status == "empty" else QColor("#eab308") if status == "playing" else QColor("#ef4444")
        p.setPen(QPen(frame, 3))
        p.setBrush(felt)
        p.drawRoundedRect(10, 16, 44, 32, 10, 10)

        # Pockets
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0b1220"))
        for x, y in [(12, 18), (32, 18), (52, 18), (12, 46), (32, 46), (52, 46)]:
            p.drawEllipse(x - 3, y - 3, 6, 6)

        # Cue ball
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(26, 30, 10, 10)
        p.end()
        return QIcon(pm)

    def _icon_for_grid_item(self, d: dict) -> tuple[QIcon | None, str]:
        # Services / service types: show stored image if exists
        img = str(d.get("image_path") or "").strip()
        if img:
            pm = QPixmap(resolve_image_path(img))
            if not pm.isNull():
                return QIcon(pm), img

        # Tables: fallback to generated billiards-table icon by status
        if "status" in d and "type_name" in d:
            status = str(d.get("status") or "empty")
            return self._render_table_icon(status), ""

        return None, ""

    def _background_for_grid_item(self, d: dict) -> QColor | None:
        if "status" in d and "type_name" in d:
            status = str(d.get("status") or "empty")
            return self._table_status_color(status)
        return None

    def _init_table_types_page(self) -> None:
        self._crud_table_types = self._replace_page_with_crud_grid("pageTableTypes", "Loại bàn")
        self._tt_search = get_child(self._crud_table_types, QLineEdit, "lineSearch")
        self._tt_filter = get_child(self._crud_table_types, QComboBox, "comboFilter")
        self._tt_refresh = get_child(self._crud_table_types, QPushButton, "btnRefresh")
        self._tt_add = get_child(self._crud_table_types, QPushButton, "btnAdd")
        self._tt_edit = get_child(self._crud_table_types, QPushButton, "btnEdit")
        self._tt_delete = get_child(self._crud_table_types, QPushButton, "btnDelete")
        self._tt_grid = get_child(self._crud_table_types, QListWidget, "gridList")

        self._tt_filter.setVisible(False)
        self._tt_refresh.clicked.connect(self._reload_table_types)
        self._tt_add.clicked.connect(self._add_table_type)
        self._tt_edit.clicked.connect(self._edit_table_type)
        self._tt_delete.clicked.connect(self._delete_table_type)
        self._tt_search.textChanged.connect(self._apply_table_types_filter)
        self._tt_grid.itemDoubleClicked.connect(lambda _: self._edit_table_type())
        self._wire_grid_five_columns(self._tt_grid, row_height=130, icon_size=QSize(64, 64))

        self._reload_table_types()

    def _reload_table_types(self) -> None:
        try:
            self._table_types_cache = self._table_types_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_table_types_filter()

    def _apply_table_types_filter(self) -> None:
        q = self._tt_search.text().strip().lower() if hasattr(self, "_tt_search") else ""
        items: list[dict] = []
        for r in self._table_types_cache:
            if q and q not in str(r.get("name", "")).lower():
                continue
            items.append(r)

        def build_text(d: dict) -> str:
            name = str(d.get("name", ""))
            price = float(d.get("price_per_hour") or 0)
            return f"{name}\n{self._format_vnd(price)}/giờ"

        self._set_grid_items(self._tt_grid, items, build_text)
        if hasattr(self, "_sessions_board"):
            self._reload_sessions_board()

    def _add_table_type(self) -> None:
        dlg = load_ui("dialog_table_type.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        spin_price = get_child(dlg, QDoubleSpinBox, "spinPricePerHour")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            price = float(spin_price.value())
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên loại bàn.")
                return
            try:
                self._table_types_repo.create(name, price)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_table_types()

    def _edit_table_type(self) -> None:
        current = self._selected_grid_item(self._tt_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại bàn để sửa.")
            return
        type_id = int(current["id"])

        dlg = load_ui("dialog_table_type.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        spin_price = get_child(dlg, QDoubleSpinBox, "spinPricePerHour")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        line_name.setText(str(current.get("name", "")))
        spin_price.setValue(float(current.get("price_per_hour") or 0))

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            price = float(spin_price.value())
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên loại bàn.")
                return
            try:
                self._table_types_repo.update(type_id, name, price)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_table_types()

    def _delete_table_type(self) -> None:
        current = self._selected_grid_item(self._tt_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại bàn để xoá.")
            return
        type_id = int(current["id"])
        if QMessageBox.question(self, "Xác nhận", "Xoá loại bàn này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._table_types_repo.delete(type_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_table_types()

    def _init_tables_page(self) -> None:
        self._crud_tables = self._replace_page_with_crud_grid("pageTables", "Quản lý bàn")
        self._tb_search = get_child(self._crud_tables, QLineEdit, "lineSearch")
        self._tb_filter = get_child(self._crud_tables, QComboBox, "comboFilter")
        self._tb_refresh = get_child(self._crud_tables, QPushButton, "btnRefresh")
        self._tb_add = get_child(self._crud_tables, QPushButton, "btnAdd")
        self._tb_edit = get_child(self._crud_tables, QPushButton, "btnEdit")
        self._tb_delete = get_child(self._crud_tables, QPushButton, "btnDelete")
        self._tb_grid = get_child(self._crud_tables, QListWidget, "gridList")

        self._tb_filter.setVisible(True)
        self._tb_refresh.clicked.connect(self._reload_tables)
        self._tb_add.clicked.connect(self._add_table)
        self._tb_edit.clicked.connect(self._edit_table)
        self._tb_delete.clicked.connect(self._delete_table)
        self._tb_search.textChanged.connect(self._apply_tables_filter)
        self._tb_filter.currentIndexChanged.connect(self._apply_tables_filter)
        self._tb_grid.itemDoubleClicked.connect(lambda _: self._edit_table())
        self._wire_grid_five_columns(self._tb_grid, row_height=130, icon_size=QSize(64, 64))

        self._reload_tables()

    def _reload_tables(self) -> None:
        try:
            self._tables_cache = self._tables_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        # build filter: table types
        try:
            types = self._table_types_repo.list_all()
        except Exception:
            types = []
        self._tb_filter.blockSignals(True)
        self._tb_filter.clear()
        self._tb_filter.addItem("Tất cả loại bàn", None)
        for t in types:
            self._tb_filter.addItem(str(t.get("name", "")), int(t["id"]))
        self._tb_filter.blockSignals(False)
        self._apply_tables_filter()

    def _apply_tables_filter(self) -> None:
        q = self._tb_search.text().strip().lower() if hasattr(self, "_tb_search") else ""
        type_id = self._tb_filter.currentData() if hasattr(self, "_tb_filter") else None
        items: list[dict] = []
        for r in self._tables_cache:
            name = str(r.get("name", ""))
            type_name = str(r.get("type_name", "") or "")
            if type_id is not None and int(r.get("type_id") or 0) != int(type_id):
                continue
            if q and q not in name.lower() and q not in type_name.lower():
                continue
            items.append(r)

        def build_text(d: dict) -> str:
            name = str(d.get("name", ""))
            type_name = str(d.get("type_name", "") or "—")
            status = str(d.get("status", "") or "empty")
            st = self._table_status_label(status)
            return f"{name}\n{type_name} • {st}"

        self._set_grid_items(self._tb_grid, items, build_text)
        if hasattr(self, "_sessions_board"):
            self._reload_sessions_board()

    def _open_table_dialog(self, current: dict | None = None) -> tuple[str, int | None, str] | None:
        dlg = load_ui("dialog_table.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        combo_type = get_child(dlg, QComboBox, "comboType")
        combo_status = get_child(dlg, QComboBox, "comboStatus")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        combo_type.clear()
        combo_type.addItem("-- Chọn loại bàn --", None)
        for t in self._table_types_repo.list_all():
            combo_type.addItem(f"{t['name']} ({format_vnd(float(t['price_per_hour'] or 0))}/giờ)", int(t["id"]))

        statuses = [("empty", "Trống"), ("playing", "Đang chơi"), ("maintenance", "Bảo trì")]
        combo_status.clear()
        for code, label in statuses:
            combo_status.addItem(label, code)

        if current:
            line_name.setText(str(current.get("name", "")))
            type_id = current.get("type_id")
            if type_id is not None:
                idx = combo_type.findData(int(type_id))
                if idx >= 0:
                    combo_type.setCurrentIndex(idx)
            s = str(current.get("status") or "empty")
            idx_s = combo_status.findData(s)
            if idx_s >= 0:
                combo_status.setCurrentIndex(idx_s)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            type_id = combo_type.currentData()
            status = str(combo_status.currentData())
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên bàn.")
                return None
            return name, (int(type_id) if type_id is not None else None), status
        return None

    def _add_table(self) -> None:
        try:
            result = self._open_table_dialog()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, type_id, status = result
        try:
            self._tables_repo.create(name, type_id, status)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_tables()

    def _edit_table(self) -> None:
        current = self._selected_grid_item(self._tb_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 bàn để sửa.")
            return
        table_id = int(current["id"])
        try:
            result = self._open_table_dialog(current=current)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, type_id, status = result
        try:
            self._tables_repo.update(table_id, name, type_id, status)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_tables()

    def _delete_table(self) -> None:
        current = self._selected_grid_item(self._tb_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 bàn để xoá.")
            return
        table_id = int(current["id"])
        if QMessageBox.question(self, "Xác nhận", "Xoá bàn này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._tables_repo.delete(table_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_tables()

    # ---------- Service types ----------
    def _init_service_types_page(self) -> None:
        self._crud_service_types = self._replace_page_with_crud_grid("pageServiceTypes", "Loại dịch vụ")
        self._st_search = get_child(self._crud_service_types, QLineEdit, "lineSearch")
        self._st_filter = get_child(self._crud_service_types, QComboBox, "comboFilter")
        self._st_refresh = get_child(self._crud_service_types, QPushButton, "btnRefresh")
        self._st_add = get_child(self._crud_service_types, QPushButton, "btnAdd")
        self._st_edit = get_child(self._crud_service_types, QPushButton, "btnEdit")
        self._st_delete = get_child(self._crud_service_types, QPushButton, "btnDelete")
        self._st_grid = get_child(self._crud_service_types, QListWidget, "gridList")

        self._st_filter.setVisible(False)
        self._st_refresh.clicked.connect(self._reload_service_types)
        self._st_add.clicked.connect(self._add_service_type)
        self._st_edit.clicked.connect(self._edit_service_type)
        self._st_delete.clicked.connect(self._delete_service_type)
        self._st_search.textChanged.connect(self._apply_service_types_filter)
        self._st_grid.itemDoubleClicked.connect(lambda _: self._edit_service_type())
        self._wire_grid_five_columns(self._st_grid, row_height=160, icon_size=QSize(96, 96))

        self._reload_service_types()

    def _reload_service_types(self) -> None:
        try:
            self._service_types_cache = self._service_types_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_service_types_filter()

    def _apply_service_types_filter(self) -> None:
        q = self._st_search.text().strip().lower() if hasattr(self, "_st_search") else ""
        items: list[dict] = []
        for r in self._service_types_cache:
            if q and q not in str(r.get("name", "")).lower():
                continue
            items.append(r)

        def build_text(d: dict) -> str:
            return str(d.get("name", ""))

        self._set_grid_items(self._st_grid, items, build_text)

    def _add_service_type(self) -> None:
        dlg = load_ui("dialog_service_type.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        line_image = get_child(dlg, QLineEdit, "lineImage")
        btn_browse = get_child(dlg, QPushButton, "btnBrowseImage")
        lbl_preview = get_child(dlg, QLabel, "lblPreview")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        def pick_image() -> None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Chọn ảnh loại dịch vụ",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)",
            )
            if not path:
                return
            rel = store_image(path, "service_types")
            line_image.setText(rel)
            abs_path = resolve_image_path(rel)
            pm = QPixmap(abs_path)
            if not pm.isNull():
                lbl_preview.setPixmap(pm.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                lbl_preview.setText("")

        btn_browse.clicked.connect(pick_image)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            image_path = line_image.text().strip() or None
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên loại dịch vụ.")
                return
            try:
                self._service_types_repo.create(name, image_path=image_path)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_service_types()

    def _edit_service_type(self) -> None:
        current = self._selected_grid_item(self._st_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại dịch vụ để sửa.")
            return
        type_id = int(current["id"])

        dlg = load_ui("dialog_service_type.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        line_image = get_child(dlg, QLineEdit, "lineImage")
        btn_browse = get_child(dlg, QPushButton, "btnBrowseImage")
        lbl_preview = get_child(dlg, QLabel, "lblPreview")
        line_name.setText(str(current.get("name", "")))
        line_image.setText(str(current.get("image_path", "") or ""))
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        def sync_preview() -> None:
            rel = line_image.text().strip()
            if not rel:
                lbl_preview.setPixmap(QPixmap())
                lbl_preview.setText("(xem trước)")
                return
            pm = QPixmap(resolve_image_path(rel))
            if pm.isNull():
                lbl_preview.setPixmap(QPixmap())
                lbl_preview.setText("(xem trước)")
                return
            lbl_preview.setPixmap(pm.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_preview.setText("")

        def pick_image() -> None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Chọn ảnh loại dịch vụ",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)",
            )
            if not path:
                return
            rel = store_image(path, "service_types")
            line_image.setText(rel)
            sync_preview()

        btn_browse.clicked.connect(pick_image)
        sync_preview()

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            image_path = line_image.text().strip() or None
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên loại dịch vụ.")
                return
            try:
                self._service_types_repo.update(type_id, name, image_path=image_path)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_service_types()

    def _delete_service_type(self) -> None:
        current = self._selected_grid_item(self._st_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại dịch vụ để xoá.")
            return
        type_id = int(current["id"])
        if QMessageBox.question(self, "Xác nhận", "Xoá loại dịch vụ này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._service_types_repo.delete(type_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_service_types()

    # ---------- Services ----------
    def _init_services_page(self) -> None:
        self._crud_services = self._replace_page_with_crud_grid("pageServices", "Dịch vụ")
        self._sv_search = get_child(self._crud_services, QLineEdit, "lineSearch")
        self._sv_filter = get_child(self._crud_services, QComboBox, "comboFilter")
        self._sv_refresh = get_child(self._crud_services, QPushButton, "btnRefresh")
        self._sv_add = get_child(self._crud_services, QPushButton, "btnAdd")
        self._sv_edit = get_child(self._crud_services, QPushButton, "btnEdit")
        self._sv_delete = get_child(self._crud_services, QPushButton, "btnDelete")
        self._sv_grid = get_child(self._crud_services, QListWidget, "gridList")

        self._sv_refresh.clicked.connect(self._reload_services)
        self._sv_add.clicked.connect(self._add_service)
        self._sv_edit.clicked.connect(self._edit_service)
        self._sv_delete.clicked.connect(self._delete_service)
        self._sv_search.textChanged.connect(self._apply_services_filter)
        self._sv_filter.currentIndexChanged.connect(self._apply_services_filter)
        self._sv_grid.itemDoubleClicked.connect(lambda _: self._edit_service())
        self._wire_grid_five_columns(self._sv_grid, row_height=170, icon_size=QSize(96, 96))

        self._reload_services()

    def _reload_services(self) -> None:
        try:
            self._services_cache = self._services_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        # build filter: service types
        try:
            types = self._service_types_repo.list_all()
        except Exception:
            types = []
        self._sv_filter.blockSignals(True)
        self._sv_filter.clear()
        self._sv_filter.addItem("Tất cả loại", None)
        for t in types:
            self._sv_filter.addItem(str(t.get("name", "")), int(t["id"]))
        self._sv_filter.blockSignals(False)
        self._apply_services_filter()

    def _apply_services_filter(self) -> None:
        q = self._sv_search.text().strip().lower() if hasattr(self, "_sv_search") else ""
        type_id = self._sv_filter.currentData() if hasattr(self, "_sv_filter") else None
        items: list[dict] = []
        for r in self._services_cache:
            name = str(r.get("name", ""))
            type_name = str(r.get("type_name", "") or "")
            if type_id is not None and int(r.get("type_id") or 0) != int(type_id):
                continue
            if q and q not in name.lower() and q not in type_name.lower():
                continue
            items.append(r)

        def build_text(d: dict) -> str:
            name = str(d.get("name", ""))
            type_name = str(d.get("type_name", "") or "—")
            price = float(d.get("price") or 0)
            return f"{name}\n{type_name} • {self._format_vnd(price)}"

        self._set_grid_items(self._sv_grid, items, build_text)

    def _apply_image_thumbs(self, view: QTableView, model, image_col: int) -> None:
        view.setIconSize(QSize(40, 40))
        view.verticalHeader().setDefaultSectionSize(48)
        for r in range(model.rowCount()):
            idx = model.index(r, image_col)
            rel = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "").strip()
            if not rel:
                continue
            pm = QPixmap(resolve_image_path(rel))
            if pm.isNull():
                continue
            model.setData(idx, "", Qt.ItemDataRole.DisplayRole)
            model.setData(idx, rel, Qt.ItemDataRole.ToolTipRole)
            model.setData(idx, QIcon(pm), Qt.ItemDataRole.DecorationRole)

    def _open_service_dialog(self, current: dict | None = None) -> tuple[str, float, int | None, str | None] | None:
        dlg = load_ui("dialog_service.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        spin_price = get_child(dlg, QDoubleSpinBox, "spinPrice")
        combo_type = get_child(dlg, QComboBox, "comboType")
        line_image = get_child(dlg, QLineEdit, "lineImage")
        btn_browse = get_child(dlg, QPushButton, "btnBrowseImage")
        lbl_preview = get_child(dlg, QLabel, "lblPreview")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        combo_type.clear()
        combo_type.addItem("-- Chọn loại --", None)
        for t in self._service_types_repo.list_all():
            combo_type.addItem(str(t["name"]), int(t["id"]))

        if current:
            line_name.setText(str(current.get("name", "")))
            spin_price.setValue(float(current.get("price") or 0))
            type_id = current.get("type_id")
            if type_id is not None:
                idx = combo_type.findData(int(type_id))
                if idx >= 0:
                    combo_type.setCurrentIndex(idx)
            line_image.setText(str(current.get("image_path", "") or ""))

        def sync_preview() -> None:
            rel = line_image.text().strip()
            if not rel:
                lbl_preview.setPixmap(QPixmap())
                lbl_preview.setText("(xem trước)")
                return
            pm = QPixmap(resolve_image_path(rel))
            if pm.isNull():
                lbl_preview.setPixmap(QPixmap())
                lbl_preview.setText("(xem trước)")
                return
            lbl_preview.setPixmap(pm.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_preview.setText("")

        def pick_image() -> None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Chọn ảnh dịch vụ",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)",
            )
            if not path:
                return
            rel = store_image(path, "services")
            line_image.setText(rel)
            sync_preview()

        btn_browse.clicked.connect(pick_image)
        sync_preview()

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            price = float(spin_price.value())
            type_id = combo_type.currentData()
            image_path = line_image.text().strip() or None
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên dịch vụ.")
                return None
            return name, price, (int(type_id) if type_id is not None else None), image_path
        return None

    def _add_service(self) -> None:
        try:
            result = self._open_service_dialog()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, price, type_id, image_path = result
        try:
            self._services_repo.create(name, price, type_id, image_path=image_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_services()

    def _edit_service(self) -> None:
        current = self._selected_grid_item(self._sv_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 dịch vụ để sửa.")
            return
        service_id = int(current["id"])
        try:
            result = self._open_service_dialog(current=current)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, price, type_id, image_path = result
        try:
            self._services_repo.update(service_id, name, price, type_id, image_path=image_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_services()

    def _delete_service(self) -> None:
        current = self._selected_grid_item(self._sv_grid)
        if not current:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 dịch vụ để xoá.")
            return
        service_id = int(current["id"])
        if QMessageBox.question(self, "Xác nhận", "Xoá dịch vụ này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._services_repo.delete(service_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_services()

    # ---------- Roles ----------
    def _init_roles_page(self) -> None:
        self._crud_roles = self._replace_page_with_crud("pageRoles", "Chức vụ")
        self._rl_search = get_child(self._crud_roles, QLineEdit, "lineSearch")
        self._rl_refresh = get_child(self._crud_roles, QPushButton, "btnRefresh")
        self._rl_add = get_child(self._crud_roles, QPushButton, "btnAdd")
        self._rl_edit = get_child(self._crud_roles, QPushButton, "btnEdit")
        self._rl_delete = get_child(self._crud_roles, QPushButton, "btnDelete")
        self._rl_table = get_child(self._crud_roles, QTableView, "tableView")

        self._rl_search.setPlaceholderText("Tìm theo tên chức vụ...")
        self._rl_edit.setEnabled(False)
        self._rl_delete.setEnabled(False)

        self._rl_refresh.clicked.connect(self._reload_roles)
        self._rl_add.clicked.connect(self._add_role)
        self._rl_edit.clicked.connect(self._edit_role)
        self._rl_delete.clicked.connect(self._delete_role)
        self._rl_search.textChanged.connect(self._apply_roles_filter)
        self._rl_table.doubleClicked.connect(lambda _: self._edit_role())

        self._reload_roles()

    def _reload_roles(self) -> None:
        try:
            self._roles_cache = self._roles_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_roles_filter()

    def _apply_roles_filter(self) -> None:
        q = self._rl_search.text().strip().lower() if hasattr(self, "_rl_search") else ""
        rows = []
        hidden_system_roles = {"admin", "user"}
        for r in self._roles_cache:
            if str(r.get("name", "")).strip().lower() in hidden_system_roles:
                continue
            if q and q not in str(r.get("name", "")).lower():
                continue
            base_salary = float(r.get("base_salary") or 0)
            rows.append([r["id"], r["name"], self._format_vnd(base_salary)])
        self._rl_table.setModel(build_model(["ID", "Tên", "Lương cơ bản"], rows))
        self._rl_table.resizeColumnsToContents()

        sel = self._rl_table.selectionModel()
        if sel is not None:
            sel.selectionChanged.connect(lambda *_: self._rl_edit.setEnabled(sel.hasSelection()))
            sel.selectionChanged.connect(lambda *_: self._rl_delete.setEnabled(sel.hasSelection()))
        self._rl_edit.setEnabled(sel.hasSelection() if sel is not None else False)
        self._rl_delete.setEnabled(sel.hasSelection() if sel is not None else False)

    def _add_role(self) -> None:
        dlg = load_ui("dialog_role.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        spin_base = get_child(dlg, QDoubleSpinBox, "spinBaseSalary")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            base_salary = float(spin_base.value())
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên chức vụ.")
                return
            try:
                self._roles_repo.create(name, base_salary)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_roles()

    def _edit_role(self) -> None:
        row = selected_row_data(self._rl_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 chức vụ để sửa.")
            return
        role_id = int(row[0])
        current = next((x for x in self._roles_cache if int(x["id"]) == role_id), None)
        if current is None:
            return

        dlg = load_ui("dialog_role.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        spin_base = get_child(dlg, QDoubleSpinBox, "spinBaseSalary")
        line_name.setText(str(current.get("name", "")))
        spin_base.setValue(float(current.get("base_salary") or 0))
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            base_salary = float(spin_base.value())
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên chức vụ.")
                return
            try:
                self._roles_repo.update(role_id, name, base_salary)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_roles()

    def _delete_role(self) -> None:
        row = selected_row_data(self._rl_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 chức vụ để xoá.")
            return
        role_id = int(row[0])
        if QMessageBox.question(self, "Xác nhận", "Xoá chức vụ này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._roles_repo.delete(role_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_roles()

    # ---------- Employees ----------
    def _init_employees_page(self) -> None:
        self._crud_employees = self._replace_page_with_crud("pageEmployees", "Nhân viên")
        self._ep_search = get_child(self._crud_employees, QLineEdit, "lineSearch")
        self._ep_refresh = get_child(self._crud_employees, QPushButton, "btnRefresh")
        self._ep_add = get_child(self._crud_employees, QPushButton, "btnAdd")
        self._ep_edit = get_child(self._crud_employees, QPushButton, "btnEdit")
        self._ep_delete = get_child(self._crud_employees, QPushButton, "btnDelete")
        self._ep_table = get_child(self._crud_employees, QTableView, "tableView")

        self._ep_search.setPlaceholderText("Tìm theo tên, SĐT, chức vụ...")
        self._ep_edit.setEnabled(False)
        self._ep_delete.setEnabled(False)

        self._ep_refresh.clicked.connect(self._reload_employees)
        self._ep_add.clicked.connect(self._add_employee)
        self._ep_edit.clicked.connect(self._edit_employee)
        self._ep_delete.clicked.connect(self._delete_employee)
        self._ep_search.textChanged.connect(self._apply_employees_filter)
        self._ep_table.doubleClicked.connect(lambda _: self._edit_employee())

        self._reload_employees()

    def _reload_employees(self) -> None:
        try:
            self._employees_cache = self._employees_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_employees_filter()

    def _apply_employees_filter(self) -> None:
        q = self._ep_search.text().strip().lower() if hasattr(self, "_ep_search") else ""
        rows = []
        for r in self._employees_cache:
            name = str(r.get("name", ""))
            phone = str(r.get("phone", "") or "")
            role_name = str(r.get("role_name", "") or "")
            if q and q not in name.lower() and q not in phone.lower() and q not in role_name.lower():
                continue
            salary = float(r.get("salary") or 0)
            rows.append([r["id"], name, phone, self._format_vnd(salary), role_name])
        self._ep_table.setModel(build_model(["ID", "Họ tên", "SĐT", "Lương", "Chức vụ"], rows))
        self._ep_table.resizeColumnsToContents()

        sel = self._ep_table.selectionModel()
        if sel is not None:
            sel.selectionChanged.connect(lambda *_: self._ep_edit.setEnabled(sel.hasSelection()))
            sel.selectionChanged.connect(lambda *_: self._ep_delete.setEnabled(sel.hasSelection()))
        self._ep_edit.setEnabled(sel.hasSelection() if sel is not None else False)
        self._ep_delete.setEnabled(sel.hasSelection() if sel is not None else False)

    def _open_employee_dialog(self, current: dict | None = None) -> tuple[str, str | None, float, int | None] | None:
        dlg = load_ui("dialog_employee.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        line_phone = get_child(dlg, QLineEdit, "linePhone")
        spin_salary = get_child(dlg, QDoubleSpinBox, "spinSalary")
        combo_role = get_child(dlg, QComboBox, "comboRole")
        combo_shift = get_child(dlg, QComboBox, "comboShift")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        combo_role.clear()
        combo_role.addItem("-- Chọn chức vụ --", None)
        roles = self._roles_repo.list_all()
        for r in roles:
            base = float(r.get("base_salary") or 0)
            combo_role.addItem(f"{r['name']} ({self._format_vnd(base)})", int(r["id"]))

        combo_shift.clear()
        combo_shift.addItem("-- Chọn ca làm --", None)
        shifts = self._shifts_repo.list_all()
        for s in shifts:
            factor = float(s.get("salary_factor") or 1)
            combo_shift.addItem(f"{s['name']} (hệ số {factor:g})", int(s["id"]))

        spin_salary.setReadOnly(True)

        def compute_salary() -> None:
            rid = combo_role.currentData()
            sid = combo_shift.currentData()
            if rid is None or sid is None:
                spin_salary.setValue(0.0)
                return
            role = next((x for x in roles if int(x["id"]) == int(rid)), None)
            shift = next((x for x in shifts if int(x["id"]) == int(sid)), None)
            base = float(role.get("base_salary") or 0) if role else 0.0
            factor = float(shift.get("salary_factor") or 1) if shift else 1.0
            spin_salary.setValue(float(base) * float(factor))

        if current:
            line_name.setText(str(current.get("name", "")))
            line_phone.setText(str(current.get("phone", "") or ""))
            spin_salary.setValue(float(current.get("salary") or 0))
            role_id = current.get("role_id")
            if role_id is not None:
                idx = combo_role.findData(int(role_id))
                if idx >= 0:
                    combo_role.setCurrentIndex(idx)
            if combo_shift.count() > 0:
                combo_shift.setCurrentIndex(0)
        else:
            if combo_role.count() > 0:
                combo_role.setCurrentIndex(0)
            if combo_shift.count() > 0:
                combo_shift.setCurrentIndex(0)

        combo_role.currentIndexChanged.connect(compute_salary)
        combo_shift.currentIndexChanged.connect(compute_salary)
        compute_salary()

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            phone = line_phone.text().strip() or None
            salary = float(spin_salary.value())
            role_id = combo_role.currentData()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập họ tên nhân viên.")
                return None
            return name, phone, salary, (int(role_id) if role_id is not None else None)
        return None

    def _add_employee(self) -> None:
        try:
            result = self._open_employee_dialog()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, phone, salary, role_id = result
        try:
            self._employees_repo.create(name, phone, salary, role_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_employees()

    def _edit_employee(self) -> None:
        row = selected_row_data(self._ep_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 nhân viên để sửa.")
            return
        employee_id = int(row[0])
        current = next((x for x in self._employees_cache if int(x["id"]) == employee_id), None)
        if current is None:
            return
        try:
            result = self._open_employee_dialog(current=current)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, phone, salary, role_id = result
        try:
            self._employees_repo.update(employee_id, name, phone, salary, role_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_employees()

    def _delete_employee(self) -> None:
        row = selected_row_data(self._ep_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 nhân viên để xoá.")
            return
        employee_id = int(row[0])
        if QMessageBox.question(self, "Xác nhận", "Xoá nhân viên này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._employees_repo.delete(employee_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_employees()

    # ---------- Shifts ----------
    def _init_shifts_page(self) -> None:
        self._crud_shifts = self._replace_page_with_crud("pageShifts", "Ca làm")
        self._sf_search = get_child(self._crud_shifts, QLineEdit, "lineSearch")
        self._sf_refresh = get_child(self._crud_shifts, QPushButton, "btnRefresh")
        self._sf_add = get_child(self._crud_shifts, QPushButton, "btnAdd")
        self._sf_edit = get_child(self._crud_shifts, QPushButton, "btnEdit")
        self._sf_delete = get_child(self._crud_shifts, QPushButton, "btnDelete")
        self._sf_table = get_child(self._crud_shifts, QTableView, "tableView")

        self._sf_search.setPlaceholderText("Tìm theo tên ca...")
        self._sf_edit.setEnabled(False)
        self._sf_delete.setEnabled(False)

        self._sf_refresh.clicked.connect(self._reload_shifts)
        self._sf_add.clicked.connect(self._add_shift)
        self._sf_edit.clicked.connect(self._edit_shift)
        self._sf_delete.clicked.connect(self._delete_shift)
        self._sf_search.textChanged.connect(self._apply_shifts_filter)
        self._sf_table.doubleClicked.connect(lambda _: self._edit_shift())

        self._reload_shifts()

    def _reload_shifts(self) -> None:
        try:
            self._shifts_cache = self._shifts_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_shifts_filter()

    def _apply_shifts_filter(self) -> None:
        q = self._sf_search.text().strip().lower() if hasattr(self, "_sf_search") else ""
        rows = []
        for r in self._shifts_cache:
            name = str(r.get("name", ""))
            if q and q not in name.lower():
                continue
            rows.append(
                [
                    r["id"],
                    name,
                    str(r.get("start_time", "")),
                    str(r.get("end_time", "")),
                    float(r.get("salary_factor") or 1),
                ]
            )
        self._sf_table.setModel(build_model(["ID", "Tên ca", "Bắt đầu", "Kết thúc", "Hệ số"], rows))
        self._sf_table.resizeColumnsToContents()

        sel = self._sf_table.selectionModel()
        if sel is not None:
            sel.selectionChanged.connect(lambda *_: self._sf_edit.setEnabled(sel.hasSelection()))
            sel.selectionChanged.connect(lambda *_: self._sf_delete.setEnabled(sel.hasSelection()))
        self._sf_edit.setEnabled(sel.hasSelection() if sel is not None else False)
        self._sf_delete.setEnabled(sel.hasSelection() if sel is not None else False)

    def _open_shift_dialog(self, current: dict | None = None) -> tuple[str, str, str, float] | None:
        dlg = load_ui("dialog_shift.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        time_start = get_child(dlg, QTimeEdit, "timeStart")
        time_end = get_child(dlg, QTimeEdit, "timeEnd")
        spin_factor = get_child(dlg, QDoubleSpinBox, "spinSalaryFactor")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        def parse_time(value: object) -> QTime:
            s = str(value or "").strip()
            if not s:
                return QTime()
            for fmt in ("HH:mm:ss", "H:mm:ss", "HH:mm", "H:mm"):
                t = QTime.fromString(s, fmt)
                if t.isValid():
                    return t
            return QTime()

        if current:
            line_name.setText(str(current.get("name", "")))
            t1 = parse_time(current.get("start_time"))
            t2 = parse_time(current.get("end_time"))
            if t1.isValid():
                time_start.setTime(t1)
            if t2.isValid():
                time_end.setTime(t2)
            spin_factor.setValue(float(current.get("salary_factor") or 1))
        else:
            spin_factor.setValue(1.0)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên ca làm.")
                return None
            start = time_start.time().toString("HH:mm:ss")
            end = time_end.time().toString("HH:mm:ss")
            factor = float(spin_factor.value())
            return name, start, end, factor
        return None

    def _add_shift(self) -> None:
        result = self._open_shift_dialog()
        if not result:
            return
        name, start, end, factor = result
        try:
            self._shifts_repo.create(name, start, end, factor)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_shifts()

    def _edit_shift(self) -> None:
        row = selected_row_data(self._sf_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 ca để sửa.")
            return
        shift_id = int(row[0])
        current = next((x for x in self._shifts_cache if int(x["id"]) == shift_id), None)
        if current is None:
            return
        result = self._open_shift_dialog(current=current)
        if not result:
            return
        name, start, end, factor = result
        try:
            self._shifts_repo.update(shift_id, name, start, end, factor)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_shifts()

    def _delete_shift(self) -> None:
        row = selected_row_data(self._sf_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 ca để xoá.")
            return
        shift_id = int(row[0])
        if QMessageBox.question(self, "Xác nhận", "Xoá ca này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._shifts_repo.delete(shift_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_shifts()

    # ---------- Bookings ----------
    def _init_bookings_page(self) -> None:
        self._crud_bookings = self._replace_page_with_crud("pageBookings", "Đặt lịch")
        self._bk_search = get_child(self._crud_bookings, QLineEdit, "lineSearch")
        self._bk_refresh = get_child(self._crud_bookings, QPushButton, "btnRefresh")
        self._bk_add = get_child(self._crud_bookings, QPushButton, "btnAdd")
        self._bk_edit = get_child(self._crud_bookings, QPushButton, "btnEdit")
        self._bk_delete = get_child(self._crud_bookings, QPushButton, "btnDelete")
        self._bk_table = get_child(self._crud_bookings, QTableView, "tableView")

        self._bk_search.setPlaceholderText("Tìm theo bàn, tên khách, SĐT...")
        self._bk_edit.setEnabled(False)
        self._bk_delete.setEnabled(False)

        self._bk_refresh.clicked.connect(self._reload_bookings)
        self._bk_add.clicked.connect(self._add_booking)
        self._bk_edit.clicked.connect(self._edit_booking)
        self._bk_delete.clicked.connect(self._delete_booking)
        self._bk_search.textChanged.connect(self._apply_bookings_filter)
        self._bk_table.doubleClicked.connect(lambda _: self._edit_booking())

        self._reload_bookings()

    def _reload_bookings(self) -> None:
        try:
            self._bookings_cache = self._bookings_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_bookings_filter()

    def _apply_bookings_filter(self) -> None:
        q = self._bk_search.text().strip().lower() if hasattr(self, "_bk_search") else ""
        rows = []
        for r in self._bookings_cache:
            customer = str(r.get("customer_name", ""))
            table_name = str(r.get("table_name", "") or "")
            phone = str(r.get("phone", "") or "")
            if q and q not in customer.lower() and q not in table_name.lower() and q not in phone.lower():
                continue
            rows.append(
                [
                    r["id"],
                    table_name,
                    customer,
                    phone,
                    str(r.get("start_time", "")),
                    str(r.get("end_time", "")),
                ]
            )
        self._bk_table.setModel(build_model(["ID", "Bàn", "Khách", "SĐT", "Bắt đầu", "Kết thúc"], rows))
        self._bk_table.resizeColumnsToContents()

        sel = self._bk_table.selectionModel()
        if sel is not None:
            sel.selectionChanged.connect(lambda *_: self._bk_edit.setEnabled(sel.hasSelection()))
            sel.selectionChanged.connect(lambda *_: self._bk_delete.setEnabled(sel.hasSelection()))
        self._bk_edit.setEnabled(sel.hasSelection() if sel is not None else False)
        self._bk_delete.setEnabled(sel.hasSelection() if sel is not None else False)

    def _open_booking_dialog(self, current: dict | None = None) -> tuple[int, str, str | None, str, str, str | None] | None:
        dlg = load_ui("dialog_booking.ui", self)
        combo_table = get_child(dlg, QComboBox, "comboTable")
        line_customer = get_child(dlg, QLineEdit, "lineCustomer")
        line_phone = get_child(dlg, QLineEdit, "linePhone")
        dt_start = get_child(dlg, QDateTimeEdit, "dtStart")
        dt_end = get_child(dlg, QDateTimeEdit, "dtEnd")
        text_note = get_child(dlg, QTextEdit, "textNote")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        combo_table.clear()
        for t in self._tables_repo.list_all():
            combo_table.addItem(str(t["name"]), int(t["id"]))

        if current:
            table_id = current.get("table_id")
            if table_id is not None:
                idx = combo_table.findData(int(table_id))
                if idx >= 0:
                    combo_table.setCurrentIndex(idx)
            line_customer.setText(str(current.get("customer_name", "")))
            line_phone.setText(str(current.get("phone", "") or ""))
            text_note.setText(str(current.get("note", "") or ""))

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            table_id = int(combo_table.currentData())
            customer = line_customer.text().strip()
            phone = line_phone.text().strip() or None
            start = dt_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            end = dt_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            note = text_note.toPlainText().strip() or None
            if not customer:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên khách hàng.")
                return None
            return table_id, customer, phone, start, end, note
        return None

    def _add_booking(self) -> None:
        try:
            result = self._open_booking_dialog()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        table_id, customer, phone, start, end, note = result
        try:
            self._bookings_repo.create(table_id, customer, phone, start, end, note)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_bookings()

    def _edit_booking(self) -> None:
        row = selected_row_data(self._bk_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 đặt lịch để sửa.")
            return
        booking_id = int(row[0])
        current = next((x for x in self._bookings_cache if int(x["id"]) == booking_id), None)
        if current is None:
            return
        try:
            result = self._open_booking_dialog(current=current)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        table_id, customer, phone, start, end, note = result
        try:
            self._bookings_repo.update(booking_id, table_id, customer, phone, start, end, note)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_bookings()

    def _delete_booking(self) -> None:
        row = selected_row_data(self._bk_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 đặt lịch để xoá.")
            return
        booking_id = int(row[0])
        if QMessageBox.question(self, "Xác nhận", "Xoá đặt lịch này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._bookings_repo.delete(booking_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_bookings()

    # ---------- Sessions (start/end + add service) ----------
    def _init_sessions_page(self) -> None:
        page = get_child(self._ui, QWidget, "pageSessions")
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)

        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        container = QFrame(page)
        container.setProperty("card", True)
        outer = QVBoxLayout(container)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        title = QLabel("Phiên chơi")
        title.setProperty("muted", False)
        title.setStyleSheet("font-size:18px;font-weight:800;")
        outer.addWidget(title)

        self._sessions_board = SessionsBoard(container)
        self._sessions_board.refresh_requested.connect(self._reload_sessions_board)
        self._sessions_board.table_clicked.connect(self._on_table_card_clicked)
        outer.addWidget(self._sessions_board, 1)

        layout.addWidget(container)
        layout.setStretch(layout.count() - 1, 1)

        self._reload_sessions_board()

    def _reload_sessions(self) -> None:
        # Trang "Phiên chơi" (cũ) đã được thay bằng "Sơ đồ bàn" — chuyển hướng reload sang board mới.
        try:
            self._sessions_cache = self._sessions_repo.list_all()
        except Exception:
            self._sessions_cache = []
        if hasattr(self, "_sessions_board"):
            self._reload_sessions_board()

    def _apply_sessions_filter(self) -> None:
        # No-op: filter giờ được xử lý trong SessionsBoard widget.
        return

    def _reload_sessions_board(self) -> None:
        from datetime import datetime, timedelta

        try:
            tables = self._tables_repo.list_all()
            sessions = self._sessions_repo.list_all()
            bookings = self._bookings_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return

        active_by_table: dict[int, dict] = {}
        for s in sessions:
            if s.get("end_time"):
                continue
            tid = s.get("table_id")
            if tid is None:
                continue
            if int(tid) not in active_by_table:
                active_by_table[int(tid)] = s

        # Bàn có booking sắp diễn ra trong 24h tới → coi là "Đặt trước".
        now = datetime.now()
        soon = now + timedelta(hours=24)
        booked_table_ids: set[int] = set()
        for b in bookings:
            try:
                start = b.get("start_time")
                if isinstance(start, str):
                    start = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                if not isinstance(start, datetime):
                    continue
                if start >= now and start <= soon:
                    booked_table_ids.add(int(b["table_id"]))
            except Exception:
                continue

        # tạm tính cập nhật thời gian thực cho phiên đang chơi
        items: list[TableState] = []
        for t in sorted(tables, key=lambda x: int(x.get("id", 0))):
            tid = int(t["id"])
            active = active_by_table.get(tid)
            total_now = 0.0
            if active is not None:
                try:
                    total_now = float(self._sessions_repo.compute_total(int(active["id"])) or 0)
                except Exception:
                    total_now = float(active.get("total") or 0)
            items.append(
                TableState(
                    table_id=tid,
                    name=str(t.get("name", "")),
                    status=str(t.get("status") or "empty"),
                    type_name=str(t.get("type_name") or ""),
                    price_per_hour=float(t.get("price_per_hour") or 0),
                    active_session_id=(int(active["id"]) if active else None),
                    active_start_time=(str(active.get("start_time", "")) if active else None),
                    active_total=total_now,
                    has_booking=(tid in booked_table_ids),
                )
            )

        self._sessions_board.set_tables(items)

    # ---------- Click vào thẻ bàn (Sơ đồ bàn) ----------
    def _on_table_card_clicked(self, table_id: int) -> None:
        try:
            tbl = next((x for x in self._tables_repo.list_all() if int(x.get("id", 0)) == int(table_id)), None)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        if tbl is None:
            return
        status = str(tbl.get("status") or "empty").lower()
        if status == "empty":
            if QMessageBox.question(
                self,
                "Bắt đầu phiên",
                f"Bắt đầu phiên cho bàn “{tbl.get('name','')}”?",
            ) == QMessageBox.StandardButton.Yes:
                self._start_session_from_table(int(table_id))
            return
        if status == "maintenance":
            QMessageBox.information(
                self,
                "Bàn đang bảo trì",
                f"Bàn “{tbl.get('name','')}” đang bảo trì.",
            )
            return

        # Đang chơi → mở dialog Tính năng
        active = next(
            (
                s
                for s in self._sessions_repo.list_all()
                if int(s.get("table_id") or 0) == int(table_id) and not s.get("end_time")
            ),
            None,
        )
        if active is None:
            QMessageBox.warning(self, "Không tìm thấy phiên", "Bàn đang đánh dấu 'đang chơi' nhưng không có phiên mở.")
            return
        session_id = int(active["id"])
        self._open_table_features_dialog(int(table_id), session_id, str(tbl.get("name", "")))

    def _build_bill_summary_for_session(self, session_id: int) -> BillSummary:
        # Tiền bàn: compute_total trừ tổng dịch vụ.
        try:
            services_rows = self._sessions_repo.list_services(int(session_id))
        except Exception:
            services_rows = []
        services = tuple(
            BillService(
                name=str(r.get("service_name") or "Dịch vụ"),
                quantity=int(r.get("quantity") or 0),
                unit_price=float(r.get("unit_price") or 0),
            )
            for r in services_rows
        )
        services_total = sum(s.amount for s in services)
        try:
            grand_total = float(self._sessions_repo.compute_total(int(session_id)) or 0)
        except Exception:
            grand_total = 0.0
        table_amount = max(0.0, grand_total - services_total)
        # Áp dụng giảm giá theo thẻ thành viên nếu có.
        discount = 0.0
        try:
            sm = self._members_repo.get_session_member(int(session_id))
            if sm is not None:
                discount = float(sm.get("applied_discount_percent") or 0)
        except Exception:
            discount = 0.0
        return BillSummary(
            table_amount=table_amount,
            discount_percent=discount,
            services=services,
        )

    def _open_table_features_dialog(self, table_id: int, session_id: int, table_name: str) -> None:
        bill = self._build_bill_summary_for_session(session_id)
        dlg = TableFeaturesDialog(table_name=table_name, bill=bill, parent=self, is_playing=True)

        def on_action(action_id: str) -> None:
            if action_id == ACTION_SERVICE:
                self._add_service_to_session_with_id(int(session_id))
                self._reload_sessions_board()
            elif action_id == ACTION_PAYMENT:
                self._end_session_by_id(int(session_id))
            elif action_id == ACTION_DETAIL:
                self._show_session_detail(int(session_id))
            elif action_id == ACTION_TRANSFER:
                self._transfer_session_dialog(int(session_id), int(table_id))
            elif action_id == ACTION_MEMBER:
                self._assign_member_to_session(int(session_id))
            elif action_id == ACTION_GROUP_PAY:
                self._group_payment_flow()
            elif action_id == ACTION_POWER_HISTORY:
                self._show_power_history(int(table_id), table_name)
            elif action_id == ACTION_USER_HISTORY:
                self._show_user_activity_history()

        dlg.action_triggered.connect(on_action)
        dlg.exec()

    # ---------- Tính năng mở rộng: Thẻ thành viên ----------
    def _assign_member_to_session(self, session_id: int) -> None:
        dlg = MemberChooserDialog(self._members_repo, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        member, discount = dlg.selected()
        if not member:
            return
        try:
            self._members_repo.assign_to_session(
                int(session_id), int(member["id"]), float(discount)
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._activity.log(
            self._user,
            "assign_member",
            target_type="session",
            target_id=int(session_id),
            detail=f"Gắn thẻ thành viên #{member.get('code')} ({member.get('name')}) vào phiên #{session_id}, giảm giá {discount:g}%",
        )
        QMessageBox.information(
            self,
            "Đã gắn thẻ thành viên",
            f"{member.get('name')} ({member.get('code')})\nGiảm giá áp dụng: {discount:g}%",
        )
        self._reload_sessions_board()

    # ---------- Tính năng mở rộng: Thanh toán nhóm ----------
    def _group_payment_flow(self) -> None:
        try:
            sessions = self._sessions_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        active = [s for s in sessions if not s.get("end_time")]
        if not active:
            QMessageBox.information(self, "Không có phiên đang chạy", "Hiện không có phiên nào để thanh toán nhóm.")
            return

        dlg = GroupPaymentDialog(
            active_sessions=active,
            compute_total_fn=self._sessions_repo.compute_total,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        result = dlg.result_value()
        if not result:
            return
        name, session_ids = result
        if not session_ids:
            return
        if QMessageBox.question(
            self,
            "Xác nhận thanh toán nhóm",
            f"Sẽ kết thúc {len(session_ids)} phiên và tạo nhóm hóa đơn “{name}”. Tiếp tục?",
        ) != QMessageBox.StandardButton.Yes:
            return

        # End từng phiên, tạo invoice, gộp vào payment_group.
        try:
            grand_total = 0.0
            invoice_ids: list[int] = []
            for sid in session_ids:
                info = self._sessions_repo.get_detail(int(sid))
                total = self._sessions_repo.end_session(int(sid))
                grand_total += float(total or 0)
                try:
                    inv_id = self._invoices_repo.create_for_session(int(sid), float(total))
                    if inv_id:
                        invoice_ids.append(int(inv_id))
                except Exception:
                    # invoice unique per session — bỏ qua nếu đã có
                    row = self._db.fetch_one(
                        "SELECT id FROM invoices WHERE session_id=%s",
                        (int(sid),),
                    )
                    if row:
                        invoice_ids.append(int(row["id"]))
                # Power off
                if info is not None:
                    try:
                        self._power_repo.log(
                            int(info.get("table_id") or 0),
                            "off",
                            user_id=self._user.get("id"),
                            note="Thanh toán nhóm",
                        )
                    except Exception:
                        pass

            group_id = self._payment_groups_repo.create(name, grand_total, self._user.get("id"))
            for inv_id in invoice_ids:
                self._payment_groups_repo.add_invoice(group_id, int(inv_id))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return

        self._activity.log(
            self._user,
            "group_payment",
            target_type="payment_group",
            target_id=int(group_id),
            detail=f"Thanh toán nhóm “{name}” gồm {len(session_ids)} phiên, tổng: {format_vnd(grand_total)}",
        )
        QMessageBox.information(
            self,
            "Thanh toán nhóm thành công",
            f"Đã tạo nhóm thanh toán “{name}”\nSố phiên: {len(session_ids)}\nTổng: {self._format_vnd(grand_total)}",
        )
        self._reload_sessions_board()
        self._reload_invoices()
        self._reload_tables()

    # ---------- Tính năng mở rộng: Lịch sử bật/tắt điện ----------
    def _show_power_history(self, table_id: int, table_name: str) -> None:
        try:
            rows = self._power_repo.list_for_table(int(table_id), limit=200)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        data = [
            [
                str(r.get("action_time", "")),
                "Bật" if str(r.get("action")) == "on" else "Tắt",
                str(r.get("user_name") or "-"),
                str(r.get("note") or ""),
            ]
            for r in rows
        ]
        dlg = HistoryDialog(
            title=f"Lịch sử bật/tắt điện - {table_name}",
            headers=["Thời điểm", "Hành động", "Người dùng", "Ghi chú"],
            rows=data,
            parent=self,
        )
        dlg.exec()

    # ---------- Tính năng mở rộng: Lịch sử người dùng ----------
    def _show_user_activity_history(self) -> None:
        try:
            rows = self._activity_repo.list_recent(limit=300)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        data = [
            [
                str(r.get("created_at", "")),
                str(r.get("username") or "-"),
                self._activity_action_label(str(r.get("action"))),
                str(r.get("target_type") or "-"),
                str(r.get("target_id") or "-"),
                str(r.get("detail") or ""),
            ]
            for r in rows
        ]
        dlg = HistoryDialog(
            title="Lịch sử người dùng",
            headers=["Thời điểm", "Người dùng", "Hành động", "Đối tượng", "Mã", "Chi tiết"],
            rows=data,
            parent=self,
        )
        dlg.exec()

    @staticmethod
    def _activity_action_label(action: str) -> str:
        mapping = {
            "login": "Đăng nhập",
            "logout": "Đăng xuất",
            "start_session": "Bắt đầu phiên",
            "payment": "Thanh toán",
            "transfer_table": "Chuyển bàn",
            "add_service": "Thêm dịch vụ",
            "assign_member": "Gắn thẻ thành viên",
            "group_payment": "Thanh toán nhóm",
        }
        return mapping.get(action, action)

    def _show_session_detail(self, session_id: int) -> None:
        session = self._sessions_repo.get_detail(int(session_id))
        items = self._sessions_repo.list_services(int(session_id))
        if not session:
            QMessageBox.warning(self, "Không tìm thấy", "Phiên không tồn tại.")
            return
        lines = [
            f"Phiên #{session.get('id')}  |  Bàn: {session.get('table_name','')}",
            f"Bắt đầu: {session.get('start_time','')}",
            f"Kết thúc: {session.get('end_time') or '(đang chơi)'}",
            "",
            "Dịch vụ đã dùng:",
        ]
        if not items:
            lines.append("  (chưa có)")
        else:
            for r in items:
                lines.append(
                    f"  - {r.get('service_name','')}: {int(r.get('quantity') or 0)} x "
                    f"{self._format_vnd(float(r.get('unit_price') or 0))}"
                )
        try:
            total = float(self._sessions_repo.compute_total(int(session_id)) or 0)
        except Exception:
            total = float(session.get("total") or 0)
        lines.append("")
        lines.append(f"Tạm tính: {self._format_vnd(total)}")
        QMessageBox.information(self, f"Chi tiết phiên #{session_id}", "\n".join(lines))

    def _transfer_session_dialog(self, session_id: int, current_table_id: int) -> None:
        try:
            tables = self._tables_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        targets = [t for t in tables if int(t.get("id", 0)) != int(current_table_id) and str(t.get("status")) == "empty"]
        if not targets:
            QMessageBox.information(self, "Không có bàn trống", "Hiện không có bàn trống để chuyển sang.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Chuyển bàn")
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Chọn bàn đích:"))
        combo = QComboBox()
        for t in targets:
            combo.addItem(str(t.get("name", "")), int(t["id"]))
        v.addWidget(combo)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        target_id = int(combo.currentData())
        try:
            self._db.execute("UPDATE sessions SET table_id=%s WHERE id=%s", (target_id, int(session_id)))
            self._db.execute("UPDATE tables SET status='playing' WHERE id=%s", (target_id,))
            self._db.execute("UPDATE tables SET status='empty' WHERE id=%s", (int(current_table_id),))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        try:
            self._power_repo.log(int(current_table_id), "off", user_id=self._user.get("id"), note="Chuyển bàn")
            self._power_repo.log(int(target_id), "on", user_id=self._user.get("id"), note="Chuyển bàn")
        except Exception:
            pass
        self._activity.log(
            self._user,
            "transfer_table",
            target_type="session",
            target_id=int(session_id),
            detail=f"Chuyển phiên #{session_id} từ bàn #{current_table_id} sang bàn #{target_id}",
        )
        self._reload_sessions_board()
        self._reload_tables()

    def _start_session(self) -> None:
        dlg = load_ui("dialog_session_start.ui", self)
        combo_table = get_child(dlg, QComboBox, "comboTable")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        combo_table.clear()
        # only empty tables are selectable
        for t in self._tables_repo.list_all():
            if str(t.get("status")) != "empty":
                continue
            combo_table.addItem(str(t["name"]), int(t["id"]))

        if combo_table.count() == 0:
            QMessageBox.information(self, "Không có bàn trống", "Hiện không có bàn trống để bắt đầu phiên.")
            return

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            table_id = int(combo_table.currentData())
            try:
                self._sessions_repo.start_session(table_id)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_sessions()
            self._reload_tables()

    def _start_session_from_table(self, table_id: int) -> None:
        try:
            sid = self._sessions_repo.start_session(int(table_id))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        try:
            self._power_repo.log(int(table_id), "on", user_id=self._user.get("id"))
        except Exception:
            pass
        self._activity.log(
            self._user,
            "start_session",
            target_type="session",
            target_id=int(sid) if sid else None,
            detail=f"Bắt đầu phiên cho bàn #{table_id}",
        )
        self._reload_sessions_board()
        self._reload_tables()

    def _end_session(self) -> None:
        row = selected_row_data(self._ss_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 phiên để kết thúc.")
            return
        session_id = int(row[0])
        current = next((x for x in self._sessions_cache if int(x["id"]) == session_id), None)
        if current and current.get("end_time"):
            QMessageBox.information(self, "Đã kết thúc", "Phiên này đã kết thúc rồi.")
            return
        if QMessageBox.question(self, "Xác nhận", "Kết thúc phiên và tạo hoá đơn?") != QMessageBox.StandardButton.Yes:
            return
        try:
            total = self._sessions_repo.end_session(session_id)
            try:
                self._invoices_repo.create_for_session(session_id, float(total))
            except Exception:
                # invoice unique per session: ignore if already created
                pass
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_sessions()
        self._reload_invoices()
        self._reload_tables()

    def _end_session_by_id(self, session_id: int) -> None:
        if QMessageBox.question(self, "Xác nhận", "Kết thúc phiên và tạo hoá đơn?") != QMessageBox.StandardButton.Yes:
            return
        session_info = None
        try:
            session_info = self._sessions_repo.get_detail(int(session_id))
        except Exception:
            pass
        try:
            total = self._sessions_repo.end_session(int(session_id))
            try:
                self._invoices_repo.create_for_session(int(session_id), float(total))
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        # Log: power off + payment, đồng thời cộng total_spent cho thẻ thành viên (nếu có)
        if session_info is not None:
            try:
                self._power_repo.log(int(session_info.get("table_id") or 0), "off", user_id=self._user.get("id"))
            except Exception:
                pass
            try:
                sm = self._members_repo.get_session_member(int(session_id))
                if sm is not None:
                    self._members_repo.add_spent(int(sm["member_id"]), float(total or 0))
            except Exception:
                pass
        self._activity.log(
            self._user,
            "payment",
            target_type="session",
            target_id=int(session_id),
            detail=f"Thanh toán phiên #{session_id}, tổng: {format_vnd(float(total or 0))}",
        )
        self._reload_sessions_board()
        self._reload_invoices()
        self._reload_tables()

    def _add_service_to_session(self) -> None:
        row = selected_row_data(self._ss_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 phiên để thêm dịch vụ.")
            return
        session_id = int(row[0])
        current = next((x for x in self._sessions_cache if int(x["id"]) == session_id), None)
        if current and current.get("end_time"):
            QMessageBox.information(self, "Phiên đã kết thúc", "Không thể thêm dịch vụ cho phiên đã kết thúc.")
            return

        dlg = load_ui("dialog_session_service.ui", self)
        combo_type = get_child(dlg, QComboBox, "comboServiceType")
        combo_sv = get_child(dlg, QComboBox, "comboService")
        lbl_preview = get_child(dlg, QLabel, "lblServicePreview")
        spin_qty = get_child(dlg, QSpinBox, "spinQty")
        spin_unit = get_child(dlg, QDoubleSpinBox, "spinUnitPrice")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        services = self._services_repo.list_all()
        if not services:
            QMessageBox.information(self, "Chưa có dịch vụ", "Bạn cần tạo dịch vụ trước.")
            return
        types = self._service_types_repo.list_all()
        combo_type.clear()
        combo_type.addItem("Tất cả loại", None)
        for t in types:
            combo_type.addItem(str(t.get("name", "")), int(t["id"]))

        def fill_services() -> None:
            tid = combo_type.currentData()
            combo_sv.blockSignals(True)
            combo_sv.clear()
            combo_sv.setIconSize(QSize(32, 32))
            for s in services:
                if tid is not None and int(s.get("type_id") or 0) != int(tid):
                    continue
                rel = str(s.get("image_path") or "").strip()
                combo_sv.addItem(
                    f"{s['name']} ({self._format_vnd(float(s.get('price', 0) or 0))})",
                    (int(s["id"]), float(s.get("price", 0) or 0), rel),
                )
                idx = combo_sv.count() - 1
                if rel:
                    pm = QPixmap(resolve_image_path(rel))
                    if not pm.isNull():
                        combo_sv.setItemIcon(idx, QIcon(pm))
            combo_sv.blockSignals(False)
            sync_price()

        def sync_price() -> None:
            _, price, rel = combo_sv.currentData()
            spin_unit.setValue(float(price))
            if rel:
                pm = QPixmap(resolve_image_path(rel))
                if not pm.isNull():
                    lbl_preview.setPixmap(pm.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    lbl_preview.setText("")
                    return
            lbl_preview.setPixmap(QPixmap())
            lbl_preview.setText("(ảnh)")

        combo_type.currentIndexChanged.connect(lambda _: fill_services())
        combo_sv.currentIndexChanged.connect(sync_price)
        fill_services()

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            service_id, _, _ = combo_sv.currentData()
            qty = int(spin_qty.value())
            unit = float(spin_unit.value())
            try:
                self._sessions_repo.add_service(session_id, int(service_id), qty, unit)
                # update session total preview (without ending session)
                total = self._sessions_repo.compute_total(session_id)
                self._db.execute("UPDATE sessions SET total=%s WHERE id=%s", (float(total), session_id))
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_sessions()

    def _add_service_to_session_by_id(self, session_id: int) -> None:
        current = self._sessions_repo.get_detail(int(session_id))
        if current and current.get("end_time"):
            QMessageBox.information(self, "Phiên đã kết thúc", "Không thể thêm dịch vụ cho phiên đã kết thúc.")
            return
        # Reuse existing dialog flow
        self._add_service_to_session_with_id(int(session_id))

    def _add_service_to_session_with_id(self, session_id: int) -> None:
        dlg = load_ui("dialog_session_service.ui", self)
        combo_type = get_child(dlg, QComboBox, "comboServiceType")
        combo_sv = get_child(dlg, QComboBox, "comboService")
        lbl_preview = get_child(dlg, QLabel, "lblServicePreview")
        spin_qty = get_child(dlg, QSpinBox, "spinQty")
        spin_unit = get_child(dlg, QDoubleSpinBox, "spinUnitPrice")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        services = self._services_repo.list_all()
        if not services:
            QMessageBox.information(self, "Chưa có dịch vụ", "Bạn cần tạo dịch vụ trước.")
            return
        types = self._service_types_repo.list_all()
        combo_type.clear()
        combo_type.addItem("Tất cả loại", None)
        for t in types:
            combo_type.addItem(str(t.get("name", "")), int(t["id"]))

        def fill_services() -> None:
            tid = combo_type.currentData()
            combo_sv.blockSignals(True)
            combo_sv.clear()
            combo_sv.setIconSize(QSize(32, 32))
            for s in services:
                if tid is not None and int(s.get("type_id") or 0) != int(tid):
                    continue
                rel = str(s.get("image_path") or "").strip()
                combo_sv.addItem(
                    f"{s['name']} ({self._format_vnd(float(s.get('price', 0) or 0))})",
                    (int(s["id"]), float(s.get("price", 0) or 0), rel),
                )
                idx = combo_sv.count() - 1
                if rel:
                    pm = QPixmap(resolve_image_path(rel))
                    if not pm.isNull():
                        combo_sv.setItemIcon(idx, QIcon(pm))
            combo_sv.blockSignals(False)
            sync_price()

        def sync_price() -> None:
            _, price, rel = combo_sv.currentData()
            spin_unit.setValue(float(price))
            if rel:
                pm = QPixmap(resolve_image_path(rel))
                if not pm.isNull():
                    lbl_preview.setPixmap(pm.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    lbl_preview.setText("")
                    return
            lbl_preview.setPixmap(QPixmap())
            lbl_preview.setText("(ảnh)")

        combo_type.currentIndexChanged.connect(lambda _: fill_services())
        combo_sv.currentIndexChanged.connect(sync_price)
        fill_services()

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            service_id, _, _ = combo_sv.currentData()
            qty = int(spin_qty.value())
            unit = float(spin_unit.value())
            try:
                self._sessions_repo.add_service(int(session_id), int(service_id), qty, unit)
                total = self._sessions_repo.compute_total(int(session_id))
                self._db.execute("UPDATE sessions SET total=%s WHERE id=%s", (float(total), int(session_id)))
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            try:
                self._inventory_consume_service(int(service_id), int(qty), int(session_id))
            except Exception:
                pass
            self._activity.log(
                self._user,
                "add_service",
                target_type="session",
                target_id=int(session_id),
                detail=f"Thêm {qty} x dịch vụ #{service_id} ({self._format_vnd(unit)}) vào phiên #{session_id}",
            )
            self._reload_sessions_board()

    def _inventory_consume_service(self, service_id: int, quantity: int, session_id: int) -> None:
        """Trừ kho tự động nếu service được gắn với item kho."""
        rows = self._db.fetch_all(
            "SELECT id FROM inventory_items WHERE service_id=%s",
            (int(service_id),),
        )
        for r in rows:
            self._inventory_repo.add_movement(
                item_id=int(r["id"]),
                movement_type="out",
                quantity=float(quantity),
                ref_type="session_service",
                ref_id=int(session_id),
                note="Tự động xuất kho theo dịch vụ",
                created_by=self._user.get("id"),
            )

    # ---------- Invoices (export PDF) ----------
    def _init_invoices_page(self) -> None:
        self._crud_invoices = self._replace_page_with_crud("pageInvoices", "Hoá đơn")
        self._iv_search = get_child(self._crud_invoices, QLineEdit, "lineSearch")
        self._iv_refresh = get_child(self._crud_invoices, QPushButton, "btnRefresh")
        get_child(self._crud_invoices, QPushButton, "btnAdd").hide()
        self._iv_export = get_child(self._crud_invoices, QPushButton, "btnEdit")
        self._iv_delete = get_child(self._crud_invoices, QPushButton, "btnDelete")
        self._iv_table = get_child(self._crud_invoices, QTableView, "tableView")

        self._iv_delete.setEnabled(False)
        self._iv_export.setText("Xuất PDF")
        self._iv_export.setEnabled(False)
        self._iv_search.setPlaceholderText("Tìm theo mã hoá đơn / tên bàn...")

        self._iv_refresh.clicked.connect(self._reload_invoices)
        self._iv_export.clicked.connect(self._export_invoice_pdf)
        self._iv_search.textChanged.connect(self._apply_invoices_filter)
        self._iv_table.doubleClicked.connect(lambda _: self._export_invoice_pdf())

        self._reload_invoices()

    def _reload_invoices(self) -> None:
        try:
            self._invoices_cache = self._invoices_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_invoices_filter()

    def _apply_invoices_filter(self) -> None:
        q = self._iv_search.text().strip().lower() if hasattr(self, "_iv_search") else ""
        rows = []
        for r in self._invoices_cache:
            table_name = str(r.get("table_name", "") or "")
            if q and q not in table_name.lower() and q not in str(r.get("id", "")).lower():
                continue
            total = float(r.get("total") or 0)
            rows.append([r["id"], r.get("session_id", ""), table_name, self._format_vnd(total), str(r.get("created_at", ""))])
        self._iv_table.setModel(build_model(["ID", "Phiên", "Bàn", "Tổng", "Tạo lúc"], rows))
        self._iv_table.resizeColumnsToContents()

        sel = self._iv_table.selectionModel()
        if sel is not None:
            sel.selectionChanged.connect(lambda *_: self._iv_export.setEnabled(sel.hasSelection()))
        self._iv_export.setEnabled(sel.hasSelection() if sel is not None else False)

    def _export_invoice_pdf(self) -> None:
        row = selected_row_data(self._iv_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 hoá đơn để xuất PDF.")
            return
        invoice_id = int(row[0])
        invoice = self._invoices_repo.get_detail(invoice_id)
        if not invoice:
            QMessageBox.warning(self, "Không tìm thấy", "Hoá đơn không tồn tại.")
            return

        session = self._sessions_repo.get_detail(int(invoice["session_id"]))
        items = self._sessions_repo.list_services(int(invoice["session_id"]))

        default_name = f"invoice_{invoice_id}.pdf"
        out_path, _ = QFileDialog.getSaveFileName(self, "Lưu hoá đơn PDF", default_name, "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            export_invoice_pdf(out_path=out_path, invoice=invoice, session=session, items=items)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất PDF", str(e))
            return
        QMessageBox.information(self, "Thành công", f"Đã xuất PDF:\n{out_path}")

    # ---------- Stats (read-only) ----------
    def _init_stats_page(self) -> None:
        self._crud_stats = self._replace_page_with_crud("pageStats", "Thống kê (doanh thu)")
        self._stt_search = get_child(self._crud_stats, QLineEdit, "lineSearch")
        self._stt_refresh = get_child(self._crud_stats, QPushButton, "btnRefresh")
        self._stt_add = get_child(self._crud_stats, QPushButton, "btnAdd")
        self._stt_edit = get_child(self._crud_stats, QPushButton, "btnEdit")
        self._stt_delete = get_child(self._crud_stats, QPushButton, "btnDelete")
        self._stt_table = get_child(self._crud_stats, QTableView, "tableView")

        self._stt_add.setEnabled(False)
        self._stt_delete.setEnabled(False)
        self._stt_edit.setText("Top dịch vụ")
        self._stt_table.doubleClicked.connect(lambda _: self._show_top_services())

        self._stt_refresh.clicked.connect(self._reload_stats_revenue)
        self._stt_edit.clicked.connect(self._show_top_services)
        self._stt_search.setPlaceholderText("Lọc theo ngày (YYYY-MM-DD)...")
        self._stt_search.textChanged.connect(self._apply_stats_filter)

        self._stats_cache: list[dict] = []
        self._reload_stats_revenue()

    def _reload_stats_revenue(self) -> None:
        try:
            self._stats_cache = self._stats_repo.revenue_by_day(30)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_stats_filter()

    def _apply_stats_filter(self) -> None:
        q = self._stt_search.text().strip().lower() if hasattr(self, "_stt_search") else ""
        rows = []
        for r in self._stats_cache:
            day = str(r.get("day", ""))
            if q and q not in day.lower():
                continue
            revenue = float(r.get("revenue") or 0)
            rows.append([day, self._format_vnd(revenue), r.get("invoices", 0)])
        self._stt_table.setModel(build_model(["Ngày", "Doanh thu", "Số HĐ"], rows))
        self._stt_table.resizeColumnsToContents()

    def _show_top_services(self) -> None:
        try:
            rows = self._stats_repo.top_services(10)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        data = []
        for r in rows:
            amount = float(r.get("amount") or 0)
            data.append([r.get("service_name", ""), r.get("qty", 0), self._format_vnd(amount)])
        self._stt_table.setModel(build_model(["Dịch vụ", "SL", "Doanh thu"], data))
        self._stt_table.resizeColumnsToContents()

    # ---------- Users (admin only — menu đã ẩn với staff) ----------
    def _init_users_page(self) -> None:
        self._crud_users = self._replace_page_with_crud("pageUsers", "Tài khoản & phân quyền")
        self._us_search = get_child(self._crud_users, QLineEdit, "lineSearch")
        self._us_refresh = get_child(self._crud_users, QPushButton, "btnRefresh")
        self._us_add = get_child(self._crud_users, QPushButton, "btnAdd")
        self._us_edit = get_child(self._crud_users, QPushButton, "btnEdit")
        self._us_delete = get_child(self._crud_users, QPushButton, "btnDelete")
        self._us_table = get_child(self._crud_users, QTableView, "tableView")

        self._us_add.setText("Thêm TK")
        self._us_edit.setText("Đổi quyền")
        self._us_search.setPlaceholderText("Tìm theo username / chức vụ...")
        self._us_edit.setEnabled(False)
        self._us_delete.setEnabled(False)

        self._us_refresh.clicked.connect(self._reload_users)
        self._us_add.clicked.connect(self._add_user_admin)
        self._us_edit.clicked.connect(self._edit_user_role)
        self._us_delete.clicked.connect(self._delete_user_admin)
        self._us_search.textChanged.connect(self._apply_users_filter)
        self._us_table.doubleClicked.connect(lambda _: self._edit_user_role())
        self._reload_users()

    def _reload_users(self) -> None:
        try:
            self._users_cache = self._users_repo.list_users_with_roles()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_users_filter()

    def _apply_users_filter(self) -> None:
        q = self._us_search.text().strip().lower() if hasattr(self, "_us_search") else ""
        rows = []
        for r in self._users_cache:
            un = str(r.get("username", ""))
            rn = str(r.get("role_name", "") or "")
            if q and q not in un.lower() and q not in rn.lower():
                continue
            rows.append([r["id"], un, rn])
        self._us_table.setModel(build_model(["ID", "Username", "Chức vụ"], rows))
        self._us_table.resizeColumnsToContents()

        sel = self._us_table.selectionModel()
        if sel is not None:
            sel.selectionChanged.connect(lambda *_: self._us_edit.setEnabled(sel.hasSelection()))
            sel.selectionChanged.connect(lambda *_: self._us_delete.setEnabled(sel.hasSelection()))
        self._us_edit.setEnabled(sel.hasSelection() if sel is not None else False)
        self._us_delete.setEnabled(sel.hasSelection() if sel is not None else False)

    def _add_user_admin(self) -> None:
        dlg = load_ui("dialog_register.ui", self)
        line_user = get_child(dlg, QLineEdit, "lineUsername")
        line_p1 = get_child(dlg, QLineEdit, "linePassword")
        line_p2 = get_child(dlg, QLineEdit, "linePassword2")
        combo_role = get_child(dlg, QComboBox, "comboRole")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        line_p1.setEchoMode(QLineEdit.EchoMode.Password)
        line_p2.setEchoMode(QLineEdit.EchoMode.Password)
        combo_role.clear()
        for r in self._register.list_roles():
            combo_role.addItem(str(r["name"]))
            idx = combo_role.count() - 1
            combo_role.setItemData(idx, int(r["id"]), Qt.ItemDataRole.UserRole)
        if combo_role.count() > 0:
            combo_role.setCurrentIndex(0)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            username = line_user.text().strip()
            p1 = line_p1.text()
            p2 = line_p2.text()
            role_data = combo_role.currentData(Qt.ItemDataRole.UserRole)
            if role_data is None and combo_role.currentIndex() >= 0:
                role_data = combo_role.itemData(combo_role.currentIndex(), Qt.ItemDataRole.UserRole)
            if combo_role.count() == 0 or role_data is None:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn chức vụ.")
                return
            role_id = int(role_data)
            if p1 != p2:
                QMessageBox.warning(self, "Sai", "Mật khẩu nhập lại không khớp.")
                return
            try:
                self._register.register(username, p1, role_id, allow_admin_role=True)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_users()

    def _edit_user_role(self) -> None:
        row = selected_row_data(self._us_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Chọn một tài khoản để đổi quyền.")
            return
        uid = int(row[0])
        current = next((x for x in self._users_cache if int(x["id"]) == uid), None)
        if current is None:
            return

        dlg = load_ui("dialog_user_role.ui", self)
        line_u = get_child(dlg, QLineEdit, "lineUsername")
        combo_role = get_child(dlg, QComboBox, "comboRole")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        line_u.setText(str(current.get("username", "")))
        combo_role.clear()
        for r in self._register.list_roles():
            combo_role.addItem(str(r["name"]))
            idx = combo_role.count() - 1
            combo_role.setItemData(idx, int(r["id"]), Qt.ItemDataRole.UserRole)
        rid = current.get("role_id")
        if rid is not None:
            ix = combo_role.findData(int(rid), Qt.ItemDataRole.UserRole)
            if ix >= 0:
                combo_role.setCurrentIndex(ix)
        elif combo_role.count() > 0:
            combo_role.setCurrentIndex(0)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            new_rid = combo_role.currentData(Qt.ItemDataRole.UserRole)
            if new_rid is None and combo_role.currentIndex() >= 0:
                new_rid = combo_role.itemData(combo_role.currentIndex(), Qt.ItemDataRole.UserRole)
            try:
                self._users_repo.update_user_role(uid, int(new_rid) if new_rid is not None else None)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_users()

    def _delete_user_admin(self) -> None:
        row = selected_row_data(self._us_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Chọn một tài khoản để xoá.")
            return
        uid = int(row[0])
        if uid == int(self._user["id"]):
            QMessageBox.warning(self, "Không được", "Không thể xoá chính tài khoản đang đăng nhập.")
            return
        if QMessageBox.question(self, "Xác nhận", "Xoá tài khoản này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._users_repo.delete_user(uid)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_users()

