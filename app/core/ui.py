from __future__ import annotations

from pathlib import Path
from typing import Type, TypeVar

from PySide6.QtCore import QFile, QObject
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget


def ui_path(relative: str) -> str:
    base = Path(__file__).resolve().parents[1] / "ui"
    return str((base / relative).resolve())


def load_ui(relative: str, parent: QWidget | None = None) -> QWidget:
    path = ui_path(relative)
    file = QFile(path)
    if not file.exists():
        raise FileNotFoundError(path)
    if not file.open(QFile.ReadOnly):
        raise RuntimeError(f"Cannot open UI file: {path}")
    try:
        loader = QUiLoader()
        widget = loader.load(file, parent)
        if widget is None:
            raise RuntimeError(f"Failed to load UI: {path}")
        return widget
    finally:
        file.close()


T = TypeVar("T", bound=QObject)


def get_child(root: QObject, cls: Type[T], name: str) -> T:
    child = root.findChild(cls, name)
    if child is None:
        raise LookupError(f"Widget not found: {name} ({cls.__name__})")
    return child

