from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QTableView


def build_model(headers: list[str], rows: list[list[Any]]) -> QStandardItemModel:
    model = QStandardItemModel()
    model.setColumnCount(len(headers))
    model.setHorizontalHeaderLabels(headers)

    for r in rows:
        items: list[QStandardItem] = []
        for v in r:
            item = QStandardItem("" if v is None else str(v))
            item.setEditable(False)
            items.append(item)
        model.appendRow(items)
    return model


def configure_table_view(view: QTableView) -> None:
    view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    view.setAlternatingRowColors(True)
    view.horizontalHeader().setStretchLastSection(True)
    view.verticalHeader().setVisible(False)


def selected_row_data(view: QTableView) -> list[str] | None:
    sel = view.selectionModel()
    if sel is None or not sel.hasSelection():
        return None
    row = sel.selectedRows()[0].row()
    model = view.model()
    if model is None:
        return None
    cols = model.columnCount()
    return [model.index(row, c).data(Qt.ItemDataRole.DisplayRole) for c in range(cols)]

