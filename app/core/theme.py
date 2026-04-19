from __future__ import annotations

from PySide6.QtWidgets import QApplication


def app_stylesheet() -> str:
    # Xanh dương (đậm hơn pastel một chút, vẫn không tối như navy)
    primary = "#4293e6"
    primary_hover = "#3a8adb"
    primary_pressed = "#2f7bc8"
    ring = "#a3cef5"

    text = "#1e3a5f"
    muted = "#5c7a9a"
    bg = "#f4f8fd"
    card = "#ffffff"
    border = "#e5e7eb"  # gray-200

    success = "#16a34a"
    warning = "#f59e0b"
    danger = "#ef4444"

    return f"""
    * {{
      font-family: "Segoe UI", "Inter", "Arial";
      color: {text};
    }}

    QWidget {{
      background: {bg};
    }}

    /* Cards */
    QFrame[card="true"] {{
      background: {card};
      border: 1px solid {border};
      border-radius: 16px;
    }}

    QLabel[muted="true"] {{
      color: {muted};
    }}

    /* Inputs */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTextEdit, QTimeEdit {{
      background: {card};
      border: 1px solid #d1d5db;
      border-radius: 10px;
      padding: 8px 10px;
      selection-background-color: {ring};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus, QTextEdit:focus, QTimeEdit:focus {{
      border: 1px solid {primary};
    }}

    /* Buttons */
    QPushButton {{
      border: 1px solid #d1d5db;
      border-radius: 10px;
      padding: 8px 12px;
      background: #f9fafb;
    }}
    QPushButton:hover {{
      background: #f3f4f6;
    }}
    QPushButton:disabled {{
      background: #f8fafc;
      color: #94a3b8;
      border-color: #e2e8f0;
    }}
    QPushButton[variant="primary"] {{
      background: {primary};
      border: 1px solid {primary};
      color: white;
      font-weight: 600;
    }}
    QPushButton[variant="primary"]:hover {{
      background: {primary_hover};
      border-color: {primary_hover};
    }}
    QPushButton[variant="primary"]:pressed {{
      background: {primary_pressed};
      border-color: {primary_pressed};
    }}
    QPushButton[variant="danger"] {{
      background: {danger};
      border: 1px solid {danger};
      color: white;
      font-weight: 600;
    }}
    QPushButton[variant="danger"]:hover {{
      background: #dc2626;
      border-color: #dc2626;
    }}

    /* Tables */
    QTableView {{
      background: {card};
      border: 1px solid {border};
      border-radius: 12px;
      gridline-color: {border};
      selection-background-color: #d4e8fc;
      selection-color: {text};
    }}
    QHeaderView::section {{
      background: #f1f5f9;
      border: none;
      border-bottom: 1px solid {border};
      padding: 8px 10px;
      font-weight: 600;
      color: {text};
    }}

    /* Session board */
    QFrame[tableStatus="empty"] {{
      border: 1px solid #bfdbfe;
    }}
    QFrame[tableStatus="playing"] {{
      border: 1px solid #a7f3d0;
    }}
    QFrame[tableStatus="maintenance"] {{
      border: 1px solid #fde68a;
    }}
    QLabel[badge="true"] {{
      padding: 3px 8px;
      border-radius: 999px;
      font-weight: 600;
      font-size: 12px;
    }}
    QLabel[badgeType="empty"] {{
      background: #eff6ff;
      color: {primary};
    }}
    QLabel[badgeType="playing"] {{
      background: #ecfdf5;
      color: {success};
    }}
    QLabel[badgeType="maintenance"] {{
      background: #fffbeb;
      color: {warning};
    }}
    """


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(app_stylesheet())

