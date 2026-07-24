"""Shared colour palette and stylesheet fragments for the tray UI.

Centralises the dark-theme colours used across the dashboard and
widgets so they're defined in exactly one place.
"""

from __future__ import annotations

# ── Colour palette ───────────────────────────────────────────────────

BG_PRIMARY = "#1e1e1e"
BG_SECONDARY = "#252525"
BG_CARD = "#2b2b2b"
BG_INPUT = "#2d2d2d"
BG_BUTTON = "#3a3a3a"
BG_BUTTON_HOVER = "#4a4a4a"
BG_BUTTON_PRESSED = "#2a2a2a"
BG_SELECTED = "#3d3d3d"

BORDER = "#444"
BORDER_LIGHT = "#555"
BORDER_HOVER = "#777"

TEXT_PRIMARY = "#ddd"
TEXT_SECONDARY = "#aaa"
TEXT_MUTED = "#888"
TEXT_BRIGHT = "#fff"
TEXT_DISABLED = "#666"

GREEN = "#27ae60"
AMBER = "#f39c12"
RED = "#e74c3c"
BLUE = "#3498db"
GREY = "#95a5a6"

# Severity mapping
SEVERITY_COLOURS: dict[str, str] = {
    "critical": RED,
    "error": RED,
    "warning": AMBER,
    "info": BLUE,
    "ok": GREEN,
    "healthy": GREEN,
    "needs_attention": AMBER,
    "neglected": RED,
    "abandoned": GREY,
}

# Status mapping (service health)
STATUS_COLOURS: dict[str, str] = {
    "ok": GREEN,
    "degraded": AMBER,
    "unreachable": RED,
    "error": RED,
    "active": GREEN,
    "inactive": RED,
    "failed": RED,
    "unknown": GREY,
}


# ── Stylesheet fragments ────────────────────────────────────────────

BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {BG_BUTTON};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 4px;
        padding: 6px 14px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {BG_BUTTON_HOVER};
        border-color: {BORDER_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {BG_BUTTON_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {BG_INPUT};
        color: {TEXT_DISABLED};
        border-color: {BORDER};
    }}
"""

COMBOBOX_STYLE = f"""
    QComboBox {{
        background-color: {BG_INPUT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        min-width: 80px;
    }}
    QComboBox:hover {{
        border-color: {BORDER_HOVER};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {TEXT_SECONDARY};
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        selection-background-color: {BG_SELECTED};
        border: 1px solid {BORDER_LIGHT};
    }}
"""

DASHBOARD_STYLE = f"""
    QMainWindow {{
        background-color: {BG_PRIMARY};
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        background-color: {BG_PRIMARY};
    }}
    QTabBar::tab {{
        background-color: {BG_CARD};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-bottom: none;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {BG_PRIMARY};
        color: {TEXT_BRIGHT};
        border-bottom: 2px solid {BLUE};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {BG_SELECTED};
    }}
    QLabel {{
        color: {TEXT_PRIMARY};
    }}
    QScrollArea {{
        border: none;
        background-color: {BG_PRIMARY};
    }}
"""

CARD_STYLE = f"""
    QFrame#card {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 8px;
    }}
"""

TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {BG_PRIMARY};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        gridline-color: {BORDER};
        font-size: 12px;
    }}
    QTableWidget::item {{
        padding: 4px 8px;
    }}
    QTableWidget::item:selected {{
        background-color: {BG_SELECTED};
    }}
    QHeaderView::section {{
        background-color: {BG_CARD};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        padding: 4px 8px;
        font-size: 12px;
        font-weight: bold;
    }}
"""
