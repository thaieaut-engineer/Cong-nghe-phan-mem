from __future__ import annotations

from PySide6.QtWidgets import QApplication


def app_stylesheet() -> str:
    # ===== Palette (theo ảnh ý tưởng) =====
    # Sidebar dark navy
    side_bg = "#1f3a5f"
    side_bg_hover = "#27466e"
    side_bg_active = "#2f5a8a"
    side_text = "#e6eef9"
    side_text_muted = "#b6c8e0"
    side_divider = "#2a4a72"

    # Topbar (light)
    top_bg = "#f4f8fd"
    top_border = "#dbe6f3"

    # Content
    primary = "#2f7bc8"
    primary_hover = "#2a6fb5"
    primary_pressed = "#235e9c"
    ring = "#a3cef5"

    text = "#1e3a5f"
    muted = "#5c7a9a"
    bg = "#eef3fa"
    card = "#ffffff"
    border = "#e5e7eb"

    # Status colors (Sơ đồ bàn)
    st_empty = "#22a06b"        # Bàn trống - xanh lá
    st_empty_dark = "#178a59"
    st_playing = "#e87a3c"      # Đang chơi - cam
    st_playing_dark = "#cf6927"
    st_maintenance = "#f1b740"  # Có điện / Bảo trì - vàng
    st_booked = "#3d83d8"       # Đặt trước - xanh dương
    st_vip = "#c0392b"          # Bàn VIP - đỏ
    st_neutral = "#2f3e4f"      # Bàn thường (rảnh không session) - xám đậm

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

    /* ===== Sidebar (dark navy) ===== */
    QFrame#sidebar {{
      background: {side_bg};
      border-right: 1px solid {side_divider};
      color: {side_text};
    }}
    QFrame#sidebar QLabel {{
      color: {side_text};
      background: transparent;
    }}
    QFrame#sidebar QLabel#lblBrand {{
      color: #ffffff;
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 0.5px;
      padding: 8px 16px;
    }}
    QFrame#sidebar QLabel#lblUser {{
      color: {side_text_muted};
      font-size: 12px;
      padding: 0 16px 6px 16px;
    }}
    QFrame#sidebar QListWidget {{
      background: transparent;
      border: none;
      outline: none;
      padding: 4px 8px;
    }}
    QFrame#sidebar QListWidget::item {{
      color: {side_text};
      padding: 11px 14px;
      margin: 2px 4px;
      border-radius: 8px;
      border: none;
    }}
    QFrame#sidebar QListWidget::item:hover {{
      background: {side_bg_hover};
    }}
    QFrame#sidebar QListWidget::item:selected {{
      background: {side_bg_active};
      color: #ffffff;
      font-weight: 600;
    }}
    QFrame#sidebar QPushButton#btnLogout {{
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.18);
      color: #ffffff;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 600;
      margin: 0 12px;
    }}
    QFrame#sidebar QPushButton#btnLogout:hover {{
      background: rgba(255,255,255,0.16);
    }}

    /* ===== Topbar (light) ===== */
    QFrame#topbar {{
      background: {top_bg};
      border-bottom: 1px solid {top_border};
    }}

    /* ===== Cards ===== */
    QFrame[card="true"] {{
      background: {card};
      border: 1px solid {border};
      border-radius: 14px;
    }}

    QLabel[muted="true"] {{
      color: {muted};
    }}

    /* ===== Inputs ===== */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTextEdit, QTimeEdit, QDateEdit {{
      background: {card};
      border: 1px solid #d1d5db;
      border-radius: 8px;
      padding: 7px 10px;
      selection-background-color: {ring};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QDateTimeEdit:focus, QTextEdit:focus, QTimeEdit:focus, QDateEdit:focus {{
      border: 1px solid {primary};
    }}

    /* ===== Buttons ===== */
    QPushButton {{
      border: 1px solid #d1d5db;
      border-radius: 8px;
      padding: 7px 12px;
      background: #ffffff;
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

    /* ===== Tables (data grid) ===== */
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

    /* ===== Sơ đồ bàn — thẻ trạng thái ===== */
    QFrame[tableCard="true"] {{
      border-radius: 10px;
      border: none;
      background-color: {st_neutral};
    }}
    QFrame[tableCard="true"][tableStatus="empty"] {{
      background-color: {st_empty};
    }}
    QFrame[tableCard="true"][tableStatus="playing"] {{
      background-color: {st_playing};
    }}
    QFrame[tableCard="true"][tableStatus="maintenance"] {{
      background-color: {st_maintenance};
    }}
    QFrame[tableCard="true"][tableStatus="booked"] {{
      background-color: {st_booked};
    }}
    QFrame[tableCard="true"][tableStatus="vip"] {{
      background-color: {st_vip};
    }}
    QFrame[tableCard="true"][tableStatus="neutral"] {{
      background-color: {st_neutral};
    }}
    QFrame[tableCard="true"] QLabel {{
      color: #ffffff;
      background: transparent;
    }}
    QLabel[tableName="true"] {{
      color: #ffffff;
      font-size: 18px;
      font-weight: 800;
    }}
    QLabel[tableType="true"] {{
      color: rgba(255,255,255,0.85);
      font-size: 12px;
    }}
    QLabel[statusTag="true"] {{
      color: rgba(255,255,255,0.95);
      font-size: 12px;
      font-weight: 600;
    }}
    QLabel[clockBig="true"] {{
      color: #ffffff;
      font-size: 22px;
      font-weight: 800;
    }}
    QLabel[clockUnit="true"] {{
      color: rgba(255,255,255,0.85);
      font-size: 11px;
    }}
    QLabel[startTime="true"] {{
      color: rgba(255,255,255,0.92);
      font-size: 11px;
    }}
    QLabel[discountTag="true"] {{
      color: rgba(255,255,255,0.95);
      font-size: 11px;
      background: rgba(0,0,0,0.18);
      padding: 2px 6px;
      border-radius: 8px;
    }}
    QLabel[priceBig="true"] {{
      color: #ffffff;
      font-size: 14px;
      font-weight: 800;
    }}

    /* ===== Filter pills (Đang chơi / Bàn trống / Có điện / Đặt trước) ===== */
    QPushButton[filterPill="empty"],
    QPushButton[filterPill="playing"],
    QPushButton[filterPill="maintenance"],
    QPushButton[filterPill="booked"],
    QPushButton[filterPill="all"] {{
      border: none;
      color: #ffffff;
      border-radius: 18px;
      padding: 6px 16px;
      font-weight: 600;
    }}
    QPushButton[filterPill="all"] {{ background-color: #5c7a9a; }}
    QPushButton[filterPill="empty"] {{ background-color: {st_empty}; }}
    QPushButton[filterPill="playing"] {{ background-color: {st_playing}; }}
    QPushButton[filterPill="maintenance"] {{ background-color: {st_maintenance}; color: #4b3a08; }}
    QPushButton[filterPill="booked"] {{ background-color: {st_booked}; }}
    QPushButton[filterPill="empty"]:hover,
    QPushButton[filterPill="playing"]:hover,
    QPushButton[filterPill="maintenance"]:hover,
    QPushButton[filterPill="booked"]:hover,
    QPushButton[filterPill="all"]:hover {{
      /* nhấn nhẹ */
      padding: 6px 16px;
    }}
    QPushButton[filterPill="all"][active="true"],
    QPushButton[filterPill="empty"][active="true"],
    QPushButton[filterPill="playing"][active="true"],
    QPushButton[filterPill="maintenance"][active="true"],
    QPushButton[filterPill="booked"][active="true"] {{
      border: 2px solid #1f3a5f;
    }}

    /* ===== Counter chips ngay dưới filter (vd: "(2) Đặt bàn") ===== */
    QLabel[counterChip="empty"],
    QLabel[counterChip="playing"],
    QLabel[counterChip="maintenance"],
    QLabel[counterChip="booked"] {{
      color: #ffffff;
      border-radius: 8px;
      padding: 4px 10px;
      font-weight: 600;
      font-size: 12px;
    }}
    QLabel[counterChip="empty"] {{ background-color: {st_empty}; }}
    QLabel[counterChip="playing"] {{ background-color: {st_playing}; }}
    QLabel[counterChip="maintenance"] {{ background-color: {st_maintenance}; color: #4b3a08; }}
    QLabel[counterChip="booked"] {{ background-color: {st_booked}; }}

    /* ===== Dashboard KPI cards ===== */
    QFrame[kpi="true"] {{
      background-color: #ffffff;
      border: 1px solid {border};
      border-left: 4px solid {primary};
      border-radius: 12px;
    }}
    QFrame[kpi="true"][accent="blue"] {{ border-left-color: {primary}; }}
    QFrame[kpi="true"][accent="green"] {{ border-left-color: {st_empty}; }}
    QFrame[kpi="true"][accent="orange"] {{ border-left-color: {st_playing}; }}
    QFrame[kpi="true"][accent="yellow"] {{ border-left-color: {st_maintenance}; }}
    QFrame[kpi="true"][accent="red"] {{ border-left-color: {danger}; }}
    QFrame[kpi="true"][accent="purple"] {{ border-left-color: #8b5cf6; }}
    QLabel[kpiLabel="true"] {{
      color: {muted};
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    QLabel[kpiValue="true"] {{
      color: {text};
      font-size: 22px;
      font-weight: 800;
    }}
    QLabel[kpiIcon="true"] {{
      font-size: 24px;
    }}
    QLabel[sectionTitle="true"] {{
      color: {text};
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 0.3px;
      padding-top: 4px;
    }}
    QLabel[greeting="true"] {{
      color: {muted};
      font-size: 12px;
    }}

    /* ===== Features dialog (Tính năng) ===== */
    QDialog#tableFeaturesDialog {{
      background: {primary};
    }}
    QDialog#tableFeaturesDialog QLabel {{
      color: #ffffff;
      background: transparent;
    }}
    QDialog#tableFeaturesDialog QLabel#featuresTitle {{
      font-size: 14px;
      font-weight: 700;
      color: rgba(255,255,255,0.92);
    }}
    QDialog#tableFeaturesDialog QPushButton[featureBtn="true"] {{
      background: transparent;
      border: none;
      color: #ffffff;
      font-weight: 600;
      padding: 14px 8px;
      border-radius: 12px;
      text-align: center;
    }}
    QDialog#tableFeaturesDialog QPushButton[featureBtn="true"]:hover {{
      background: rgba(255,255,255,0.10);
    }}
    QDialog#tableFeaturesDialog QPushButton[featureBtn="true"][active="true"] {{
      background: {primary_pressed};
    }}
    QDialog#tableFeaturesDialog QFrame#billSeparator {{
      background: rgba(255,255,255,0.18);
      max-height: 1px;
      min-height: 1px;
      border: none;
    }}
    QDialog#tableFeaturesDialog QLabel[billLine="true"] {{
      color: rgba(255,255,255,0.95);
      font-size: 13px;
    }}
    QDialog#tableFeaturesDialog QLabel[billValue="true"] {{
      color: #ffffff;
      font-size: 13px;
      font-weight: 700;
    }}
    """


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(app_stylesheet())
