from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDateTimeEdit,
    QSpinBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QFileDialog,
    QStackedWidget,
    QTableView,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.ui import get_child, load_ui
from app.core.db import Database
from app.core.permissions import is_admin, menu_entries_for_role, normalize_role
from app.repositories.booking_repository import BookingRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.service_repository import ServiceRepository
from app.repositories.service_type_repository import ServiceTypeRepository
from app.repositories.stats_repository import StatsRepository
from app.repositories.table_repository import TableRepository
from app.repositories.table_type_repository import TableTypeRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.user_repository import UserRepository
from app.widgets.table_helpers import build_model, configure_table_view, selected_row_data
from app.services.invoice_pdf_service import export_invoice_pdf
from app.services.register_service import RegisterService


class MainWindow(QMainWindow):
    def __init__(self, user: dict, db: Database) -> None:
        super().__init__()
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

        self._lbl_user = get_child(self._ui, QLabel, "lblUser")
        self._list_menu = get_child(self._ui, QListWidget, "listMenu")
        self._btn_logout = get_child(self._ui, QPushButton, "btnLogout")
        self._stacked = get_child(self._ui, QStackedWidget, "stackedPages")

        rn = normalize_role(user.get("role_name"))
        self._lbl_user.setText(f"Xin chào, {user.get('username', '')}\n(Quyền: {rn})")
        self._btn_logout.clicked.connect(self._on_logout)

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
        self._stacked.setCurrentIndex(int(si))

    def _on_logout(self) -> None:
        self.close()

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

        layout.addWidget(crud)
        return crud

    def _init_table_types_page(self) -> None:
        self._crud_table_types = self._replace_page_with_crud("pageTableTypes", "Loại bàn")
        self._tt_search = get_child(self._crud_table_types, QLineEdit, "lineSearch")
        self._tt_refresh = get_child(self._crud_table_types, QPushButton, "btnRefresh")
        self._tt_add = get_child(self._crud_table_types, QPushButton, "btnAdd")
        self._tt_edit = get_child(self._crud_table_types, QPushButton, "btnEdit")
        self._tt_delete = get_child(self._crud_table_types, QPushButton, "btnDelete")
        self._tt_table = get_child(self._crud_table_types, QTableView, "tableView")

        self._tt_refresh.clicked.connect(self._reload_table_types)
        self._tt_add.clicked.connect(self._add_table_type)
        self._tt_edit.clicked.connect(self._edit_table_type)
        self._tt_delete.clicked.connect(self._delete_table_type)
        self._tt_search.textChanged.connect(self._apply_table_types_filter)

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
        rows = []
        for r in self._table_types_cache:
            if q and q not in str(r.get("name", "")).lower():
                continue
            rows.append([r["id"], r["name"], r["price_per_hour"]])
        self._tt_table.setModel(build_model(["ID", "Tên", "Giá/giờ"], rows))
        self._tt_table.resizeColumnsToContents()

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
        row = selected_row_data(self._tt_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại bàn để sửa.")
            return
        type_id = int(row[0])

        current = next((x for x in self._table_types_cache if int(x["id"]) == type_id), None)
        if current is None:
            return

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
        row = selected_row_data(self._tt_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại bàn để xoá.")
            return
        type_id = int(row[0])
        if QMessageBox.question(self, "Xác nhận", "Xoá loại bàn này?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._table_types_repo.delete(type_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_table_types()

    def _init_tables_page(self) -> None:
        self._crud_tables = self._replace_page_with_crud("pageTables", "Quản lý bàn")
        self._tb_search = get_child(self._crud_tables, QLineEdit, "lineSearch")
        self._tb_refresh = get_child(self._crud_tables, QPushButton, "btnRefresh")
        self._tb_add = get_child(self._crud_tables, QPushButton, "btnAdd")
        self._tb_edit = get_child(self._crud_tables, QPushButton, "btnEdit")
        self._tb_delete = get_child(self._crud_tables, QPushButton, "btnDelete")
        self._tb_table = get_child(self._crud_tables, QTableView, "tableView")

        self._tb_refresh.clicked.connect(self._reload_tables)
        self._tb_add.clicked.connect(self._add_table)
        self._tb_edit.clicked.connect(self._edit_table)
        self._tb_delete.clicked.connect(self._delete_table)
        self._tb_search.textChanged.connect(self._apply_tables_filter)

        self._reload_tables()

    def _reload_tables(self) -> None:
        try:
            self._tables_cache = self._tables_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_tables_filter()

    def _apply_tables_filter(self) -> None:
        q = self._tb_search.text().strip().lower() if hasattr(self, "_tb_search") else ""
        rows = []
        for r in self._tables_cache:
            name = str(r.get("name", ""))
            type_name = str(r.get("type_name", "") or "")
            if q and q not in name.lower() and q not in type_name.lower():
                continue
            rows.append([r["id"], name, type_name, r.get("status", "")])
        self._tb_table.setModel(build_model(["ID", "Tên bàn", "Loại bàn", "Trạng thái"], rows))
        self._tb_table.resizeColumnsToContents()

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
            combo_type.addItem(f"{t['name']} ({t['price_per_hour']}/h)", int(t["id"]))

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
        row = selected_row_data(self._tb_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 bàn để sửa.")
            return
        table_id = int(row[0])
        current = next((x for x in self._tables_cache if int(x["id"]) == table_id), None)
        if current is None:
            return
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
        row = selected_row_data(self._tb_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 bàn để xoá.")
            return
        table_id = int(row[0])
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
        self._crud_service_types = self._replace_page_with_crud("pageServiceTypes", "Loại dịch vụ")
        self._st_search = get_child(self._crud_service_types, QLineEdit, "lineSearch")
        self._st_refresh = get_child(self._crud_service_types, QPushButton, "btnRefresh")
        self._st_add = get_child(self._crud_service_types, QPushButton, "btnAdd")
        self._st_edit = get_child(self._crud_service_types, QPushButton, "btnEdit")
        self._st_delete = get_child(self._crud_service_types, QPushButton, "btnDelete")
        self._st_table = get_child(self._crud_service_types, QTableView, "tableView")

        self._st_refresh.clicked.connect(self._reload_service_types)
        self._st_add.clicked.connect(self._add_service_type)
        self._st_edit.clicked.connect(self._edit_service_type)
        self._st_delete.clicked.connect(self._delete_service_type)
        self._st_search.textChanged.connect(self._apply_service_types_filter)

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
        rows = []
        for r in self._service_types_cache:
            if q and q not in str(r.get("name", "")).lower():
                continue
            rows.append([r["id"], r["name"]])
        self._st_table.setModel(build_model(["ID", "Tên"], rows))
        self._st_table.resizeColumnsToContents()

    def _add_service_type(self) -> None:
        dlg = load_ui("dialog_service_type.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên loại dịch vụ.")
                return
            try:
                self._service_types_repo.create(name)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_service_types()

    def _edit_service_type(self) -> None:
        row = selected_row_data(self._st_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại dịch vụ để sửa.")
            return
        type_id = int(row[0])
        current = next((x for x in self._service_types_cache if int(x["id"]) == type_id), None)
        if current is None:
            return

        dlg = load_ui("dialog_service_type.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        line_name.setText(str(current.get("name", "")))
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên loại dịch vụ.")
                return
            try:
                self._service_types_repo.update(type_id, name)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))
                return
            self._reload_service_types()

    def _delete_service_type(self) -> None:
        row = selected_row_data(self._st_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 loại dịch vụ để xoá.")
            return
        type_id = int(row[0])
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
        self._crud_services = self._replace_page_with_crud("pageServices", "Dịch vụ")
        self._sv_search = get_child(self._crud_services, QLineEdit, "lineSearch")
        self._sv_refresh = get_child(self._crud_services, QPushButton, "btnRefresh")
        self._sv_add = get_child(self._crud_services, QPushButton, "btnAdd")
        self._sv_edit = get_child(self._crud_services, QPushButton, "btnEdit")
        self._sv_delete = get_child(self._crud_services, QPushButton, "btnDelete")
        self._sv_table = get_child(self._crud_services, QTableView, "tableView")

        self._sv_refresh.clicked.connect(self._reload_services)
        self._sv_add.clicked.connect(self._add_service)
        self._sv_edit.clicked.connect(self._edit_service)
        self._sv_delete.clicked.connect(self._delete_service)
        self._sv_search.textChanged.connect(self._apply_services_filter)

        self._reload_services()

    def _reload_services(self) -> None:
        try:
            self._services_cache = self._services_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_services_filter()

    def _apply_services_filter(self) -> None:
        q = self._sv_search.text().strip().lower() if hasattr(self, "_sv_search") else ""
        rows = []
        for r in self._services_cache:
            name = str(r.get("name", ""))
            type_name = str(r.get("type_name", "") or "")
            if q and q not in name.lower() and q not in type_name.lower():
                continue
            rows.append([r["id"], name, r.get("price", 0), type_name])
        self._sv_table.setModel(build_model(["ID", "Tên", "Giá", "Loại"], rows))
        self._sv_table.resizeColumnsToContents()

    def _open_service_dialog(self, current: dict | None = None) -> tuple[str, float, int | None] | None:
        dlg = load_ui("dialog_service.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        spin_price = get_child(dlg, QDoubleSpinBox, "spinPrice")
        combo_type = get_child(dlg, QComboBox, "comboType")
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

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            price = float(spin_price.value())
            type_id = combo_type.currentData()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên dịch vụ.")
                return None
            return name, price, (int(type_id) if type_id is not None else None)
        return None

    def _add_service(self) -> None:
        try:
            result = self._open_service_dialog()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, price, type_id = result
        try:
            self._services_repo.create(name, price, type_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_services()

    def _edit_service(self) -> None:
        row = selected_row_data(self._sv_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 dịch vụ để sửa.")
            return
        service_id = int(row[0])
        current = next((x for x in self._services_cache if int(x["id"]) == service_id), None)
        if current is None:
            return
        try:
            result = self._open_service_dialog(current=current)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        if not result:
            return
        name, price, type_id = result
        try:
            self._services_repo.update(service_id, name, price, type_id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        self._reload_services()

    def _delete_service(self) -> None:
        row = selected_row_data(self._sv_table)
        if not row:
            QMessageBox.information(self, "Chọn dòng", "Vui lòng chọn 1 dịch vụ để xoá.")
            return
        service_id = int(row[0])
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

        self._rl_refresh.clicked.connect(self._reload_roles)
        self._rl_add.clicked.connect(self._add_role)
        self._rl_edit.clicked.connect(self._edit_role)
        self._rl_delete.clicked.connect(self._delete_role)
        self._rl_search.textChanged.connect(self._apply_roles_filter)

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
        for r in self._roles_cache:
            if q and q not in str(r.get("name", "")).lower():
                continue
            rows.append([r["id"], r["name"]])
        self._rl_table.setModel(build_model(["ID", "Tên"], rows))
        self._rl_table.resizeColumnsToContents()

    def _add_role(self) -> None:
        dlg = load_ui("dialog_role.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên chức vụ.")
                return
            try:
                self._roles_repo.create(name)
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
        line_name.setText(str(current.get("name", "")))
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên chức vụ.")
                return
            try:
                self._roles_repo.update(role_id, name)
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

        self._ep_refresh.clicked.connect(self._reload_employees)
        self._ep_add.clicked.connect(self._add_employee)
        self._ep_edit.clicked.connect(self._edit_employee)
        self._ep_delete.clicked.connect(self._delete_employee)
        self._ep_search.textChanged.connect(self._apply_employees_filter)

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
            rows.append([r["id"], name, phone, r.get("salary", 0), role_name])
        self._ep_table.setModel(build_model(["ID", "Họ tên", "SĐT", "Lương", "Chức vụ"], rows))
        self._ep_table.resizeColumnsToContents()

    def _open_employee_dialog(self, current: dict | None = None) -> tuple[str, str | None, float, int | None] | None:
        dlg = load_ui("dialog_employee.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        line_phone = get_child(dlg, QLineEdit, "linePhone")
        spin_salary = get_child(dlg, QDoubleSpinBox, "spinSalary")
        combo_role = get_child(dlg, QComboBox, "comboRole")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        combo_role.clear()
        combo_role.addItem("-- Chọn chức vụ --", None)
        for r in self._roles_repo.list_all():
            combo_role.addItem(str(r["name"]), int(r["id"]))

        if current:
            line_name.setText(str(current.get("name", "")))
            line_phone.setText(str(current.get("phone", "") or ""))
            spin_salary.setValue(float(current.get("salary") or 0))
            role_id = current.get("role_id")
            if role_id is not None:
                idx = combo_role.findData(int(role_id))
                if idx >= 0:
                    combo_role.setCurrentIndex(idx)

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

        self._sf_refresh.clicked.connect(self._reload_shifts)
        self._sf_add.clicked.connect(self._add_shift)
        self._sf_edit.clicked.connect(self._edit_shift)
        self._sf_delete.clicked.connect(self._delete_shift)
        self._sf_search.textChanged.connect(self._apply_shifts_filter)

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
            rows.append([r["id"], name, str(r.get("start_time", "")), str(r.get("end_time", ""))])
        self._sf_table.setModel(build_model(["ID", "Tên ca", "Bắt đầu", "Kết thúc"], rows))
        self._sf_table.resizeColumnsToContents()

    def _open_shift_dialog(self, current: dict | None = None) -> tuple[str, str, str] | None:
        dlg = load_ui("dialog_shift.ui", self)
        line_name = get_child(dlg, QLineEdit, "lineName")
        time_start = get_child(dlg, QTimeEdit, "timeStart")
        time_end = get_child(dlg, QTimeEdit, "timeEnd")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if current:
            line_name.setText(str(current.get("name", "")))

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            name = line_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên ca làm.")
                return None
            start = time_start.time().toString("HH:mm:ss")
            end = time_end.time().toString("HH:mm:ss")
            return name, start, end
        return None

    def _add_shift(self) -> None:
        result = self._open_shift_dialog()
        if not result:
            return
        name, start, end = result
        try:
            self._shifts_repo.create(name, start, end)
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
        name, start, end = result
        try:
            self._shifts_repo.update(shift_id, name, start, end)
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

        self._bk_refresh.clicked.connect(self._reload_bookings)
        self._bk_add.clicked.connect(self._add_booking)
        self._bk_edit.clicked.connect(self._edit_booking)
        self._bk_delete.clicked.connect(self._delete_booking)
        self._bk_search.textChanged.connect(self._apply_bookings_filter)

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
        self._crud_sessions = self._replace_page_with_crud("pageSessions", "Phiên chơi")
        self._ss_search = get_child(self._crud_sessions, QLineEdit, "lineSearch")
        self._ss_refresh = get_child(self._crud_sessions, QPushButton, "btnRefresh")
        self._ss_add = get_child(self._crud_sessions, QPushButton, "btnAdd")
        self._ss_edit = get_child(self._crud_sessions, QPushButton, "btnEdit")
        self._ss_delete = get_child(self._crud_sessions, QPushButton, "btnDelete")
        self._ss_table = get_child(self._crud_sessions, QTableView, "tableView")

        self._ss_add.setText("Bắt đầu")
        self._ss_edit.setText("Kết thúc")
        self._ss_delete.setText("Thêm DV")

        self._ss_refresh.clicked.connect(self._reload_sessions)
        self._ss_add.clicked.connect(self._start_session)
        self._ss_edit.clicked.connect(self._end_session)
        self._ss_delete.clicked.connect(self._add_service_to_session)
        self._ss_search.textChanged.connect(self._apply_sessions_filter)
        self._reload_sessions()

    def _reload_sessions(self) -> None:
        try:
            self._sessions_cache = self._sessions_repo.list_all()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        self._apply_sessions_filter()

    def _apply_sessions_filter(self) -> None:
        q = self._ss_search.text().strip().lower() if hasattr(self, "_ss_search") else ""
        rows = []
        for r in self._sessions_cache:
            table_name = str(r.get("table_name", "") or "")
            if q and q not in table_name.lower() and q not in str(r.get("id", "")).lower():
                continue
            rows.append(
                [
                    r["id"],
                    table_name,
                    str(r.get("start_time", "")),
                    str(r.get("end_time", "")),
                    r.get("total", 0),
                ]
            )
        self._ss_table.setModel(build_model(["ID", "Bàn", "Bắt đầu", "Kết thúc", "Tổng"], rows))
        self._ss_table.resizeColumnsToContents()

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
        combo_sv = get_child(dlg, QComboBox, "comboService")
        spin_qty = get_child(dlg, QSpinBox, "spinQty")
        spin_unit = get_child(dlg, QDoubleSpinBox, "spinUnitPrice")
        buttons = get_child(dlg, QDialogButtonBox, "buttonBox")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        services = self._services_repo.list_all()
        if not services:
            QMessageBox.information(self, "Chưa có dịch vụ", "Bạn cần tạo dịch vụ trước.")
            return
        combo_sv.clear()
        for s in services:
            combo_sv.addItem(f"{s['name']} ({s.get('price',0)}đ)", (int(s["id"]), float(s.get("price", 0) or 0)))

        def sync_price() -> None:
            _, price = combo_sv.currentData()
            spin_unit.setValue(float(price))

        combo_sv.currentIndexChanged.connect(sync_price)
        sync_price()

        if isinstance(dlg, QDialog) and dlg.exec() == QDialog.DialogCode.Accepted:
            service_id, _ = combo_sv.currentData()
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

    # ---------- Invoices (export PDF) ----------
    def _init_invoices_page(self) -> None:
        self._crud_invoices = self._replace_page_with_crud("pageInvoices", "Hoá đơn")
        self._iv_search = get_child(self._crud_invoices, QLineEdit, "lineSearch")
        self._iv_refresh = get_child(self._crud_invoices, QPushButton, "btnRefresh")
        self._iv_add = get_child(self._crud_invoices, QPushButton, "btnAdd")
        self._iv_export = get_child(self._crud_invoices, QPushButton, "btnEdit")
        self._iv_delete = get_child(self._crud_invoices, QPushButton, "btnDelete")
        self._iv_table = get_child(self._crud_invoices, QTableView, "tableView")

        self._iv_add.setEnabled(False)
        self._iv_delete.setEnabled(False)
        self._iv_export.setText("Xuất PDF")

        self._iv_refresh.clicked.connect(self._reload_invoices)
        self._iv_export.clicked.connect(self._export_invoice_pdf)
        self._iv_search.textChanged.connect(self._apply_invoices_filter)

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
            rows.append([r["id"], r.get("session_id", ""), table_name, r.get("total", 0), str(r.get("created_at", ""))])
        self._iv_table.setModel(build_model(["ID", "Phiên", "Bàn", "Tổng", "Tạo lúc"], rows))
        self._iv_table.resizeColumnsToContents()

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
            rows.append([day, r.get("revenue", 0), r.get("invoices", 0)])
        self._stt_table.setModel(build_model(["Ngày", "Doanh thu", "Số HĐ"], rows))
        self._stt_table.resizeColumnsToContents()

    def _show_top_services(self) -> None:
        try:
            rows = self._stats_repo.top_services(10)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
            return
        data = [[r.get("service_name", ""), r.get("qty", 0), r.get("amount", 0)] for r in rows]
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

        self._us_refresh.clicked.connect(self._reload_users)
        self._us_add.clicked.connect(self._add_user_admin)
        self._us_edit.clicked.connect(self._edit_user_role)
        self._us_delete.clicked.connect(self._delete_user_admin)
        self._us_search.textChanged.connect(self._apply_users_filter)
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

