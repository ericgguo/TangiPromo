import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QFont, QFontDatabase
from src.main_window import MainWindow

# ────────────────────────────────────────────────────────────────────────────
# Design tokens (keep in sync with main_window.py inline styles)
#   bg.base       = #0b0b0d   canvas / window background
#   bg.surface    = #141418   panels
#   bg.elevated   = #1c1c22   cards / group boxes
#   bg.input      = #23232a   inputs / combos
#   text.primary  = #f4f4f6
#   text.muted    = #8a8a93
#   text.faint    = #5c5c65
#   border        = rgba(255,255,255,0.06)
#   border.soft   = rgba(255,255,255,0.10)
#   accent        = #7c6bff   indigo
#   accent.hover  = #8f80ff
#   accent.press  = #6655e6
#   danger        = #ff5a5f
# ────────────────────────────────────────────────────────────────────────────

DARK_STYLESHEET = """
* { outline: 0; }

QWidget {
    background-color: #141418;
    color: #f4f4f6;
    font-size: 13px;
    font-family: "Inter", "Helvetica Neue", "PingFang SC", "Segoe UI", sans-serif;
}

QMainWindow, QDialog { background-color: #0b0b0d; }

/* ── Group boxes (panel cards) ─────────────────────────────────────────── */
QGroupBox {
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    margin-top: 18px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
    color: #9a9aa3;
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    background-color: #1c1c22;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background: transparent;
}

/* ── Combo / LineEdit / SpinBox — unified field style ──────────────────── */
QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {
    background-color: #23232a;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 28px;
    color: #f4f4f6;
    selection-background-color: #7c6bff;
    selection-color: #ffffff;
}
QComboBox:hover, QLineEdit:hover,
QDoubleSpinBox:hover, QSpinBox:hover {
    background-color: #2a2a33;
    border-color: rgba(255, 255, 255, 0.12);
}
QComboBox:focus, QLineEdit:focus,
QDoubleSpinBox:focus, QSpinBox:focus {
    border-color: #7c6bff;
    background-color: #23232a;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9a9aa3;
    margin-right: 10px;
    width: 0; height: 0;
}
QComboBox::down-arrow:hover { border-top-color: #f4f4f6; }
QComboBox QAbstractItemView {
    background-color: #1c1c22;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    selection-background-color: #7c6bff;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border-radius: 6px;
    min-height: 22px;
}
QComboBox QAbstractItemView::item:hover { background-color: #2a2a33; }

/* ── Buttons ───────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #2a2a33;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 7px 14px;
    min-height: 30px;
    color: #f4f4f6;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #33333d;
    border-color: rgba(255, 255, 255, 0.12);
}
QPushButton:pressed { background-color: #202028; }
QPushButton:disabled { color: #5c5c65; background-color: #1c1c22; }

/* primary action */
QPushButton#primaryBtn {
    background-color: #7c6bff;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primaryBtn:hover { background-color: #8f80ff; }
QPushButton#primaryBtn:pressed { background-color: #6655e6; }
QPushButton#primaryBtn:disabled {
    background-color: #3b3550; color: rgba(255,255,255,0.4);
}

/* destructive */
QPushButton#dangerBtn {
    background-color: transparent;
    border: 1px solid rgba(255, 90, 95, 0.55);
    color: #ff8086;
    font-weight: 500;
}
QPushButton#dangerBtn:hover {
    background-color: rgba(255, 90, 95, 0.15);
    color: #ff9ea2;
    border-color: rgba(255, 90, 95, 0.75);
}
QPushButton#dangerBtn:pressed { background-color: rgba(255, 90, 95, 0.25); }

/* ghost / secondary outlined */
QPushButton#ghostBtn {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 0.10);
    color: #b8b8c0;
}
QPushButton#ghostBtn:hover {
    border-color: rgba(124, 107, 255, 0.55);
    color: #f4f4f6;
    background-color: rgba(124, 107, 255, 0.08);
}

/* ── Slider ────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px;
    background: rgba(255, 255, 255, 0.10);
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #7c6bff;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px; height: 16px;
    background: #ffffff;
    border-radius: 8px;
    margin: -7px 0;
    border: none;
}
QSlider::handle:horizontal:hover {
    background: #f4f4f6;
    /* subtle glow via border trick */
    border: 3px solid rgba(124, 107, 255, 0.35);
    width: 14px; height: 14px;
    margin: -8px 0;
    border-radius: 10px;
}

/* ── Lists ─────────────────────────────────────────────────────────────── */
QListWidget {
    background-color: #17171c;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    outline: none;
    padding: 4px;
}
QListWidget::item {
    padding: 7px 10px;
    border-radius: 6px;
    margin: 1px 2px;
    color: #d4d4dc;
}
QListWidget::item:hover:!selected { background-color: #23232a; }
QListWidget::item:selected {
    background-color: #7c6bff;
    color: #ffffff;
}

/* ── Scrollbars ────────────────────────────────────────────────────────── */
QScrollBar:vertical { width: 8px; background: transparent; margin: 4px 2px; }
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.22); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal { height: 8px; background: transparent; margin: 2px 4px; }
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover { background: rgba(255, 255, 255, 0.22); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ── Text / Code editor ────────────────────────────────────────────────── */
QTextEdit {
    background-color: #0e0e12;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    font-family: 'JetBrains Mono', 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
    font-size: 12px;
    color: #c8e4b0;
    padding: 10px 12px;
    selection-background-color: #7c6bff;
    selection-color: #ffffff;
}
QTextEdit:focus { border-color: rgba(124, 107, 255, 0.55); }

QLabel { background: transparent; border: none; }

/* ── Splitter ──────────────────────────────────────────────────────────── */
QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 1px; background: rgba(255, 255, 255, 0.06); }
QSplitter::handle:horizontal:hover { background: rgba(124, 107, 255, 0.4); }

QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }

/* ── Checkbox ──────────────────────────────────────────────────────────── */
QCheckBox { spacing: 8px; color: #d4d4dc; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1.5px solid rgba(255, 255, 255, 0.18);
    border-radius: 5px;
    background: #23232a;
}
QCheckBox::indicator:hover { border-color: rgba(124, 107, 255, 0.7); }
QCheckBox::indicator:checked {
    background: #7c6bff;
    border-color: #7c6bff;
    image: none;
}
QCheckBox::indicator:checked:hover { background: #8f80ff; }

/* ── SpinBox up/down buttons ───────────────────────────────────────────── */
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    background: transparent;
    border: none;
    width: 16px;
}
QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-bottom: 4px solid #9a9aa3;
    width: 0; height: 0;
}
QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid #9a9aa3;
    width: 0; height: 0;
}
QDoubleSpinBox::up-arrow:hover, QSpinBox::up-arrow:hover { border-bottom-color: #f4f4f6; }
QDoubleSpinBox::down-arrow:hover, QSpinBox::down-arrow:hover { border-top-color: #f4f4f6; }

/* ── Tooltip ───────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #23232a;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    color: #f4f4f6;
    padding: 5px 9px;
    font-size: 12px;
}

/* ── TabWidget (used by side panels) ───────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: #141418;
}
QTabBar::tab {
    background: transparent;
    color: #8a8a93;
    padding: 9px 14px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: #f4f4f6; border-bottom: 2px solid #7c6bff; }
QTabBar::tab:hover:!selected { color: #d4d4dc; }
QTabBar::tab:disabled { color: #3f3f48; }

/* ── MessageBox / Dialog buttons look consistent ───────────────────────── */
QMessageBox { background-color: #1c1c22; }
QMessageBox QLabel { color: #f4f4f6; }

/* ── Menu (context menus) ──────────────────────────────────────────────── */
QMenu {
    background-color: #1c1c22;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 6px;
    color: #f4f4f6;
}
QMenu::item {
    padding: 6px 14px;
    border-radius: 6px;
}
QMenu::item:selected { background-color: #7c6bff; }
QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 0.08);
    margin: 4px 6px;
}

/* ── Progress dialog progress bar ──────────────────────────────────────── */
QProgressBar {
    background-color: #23232a;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: #f4f4f6;
}
QProgressBar::chunk {
    background-color: #7c6bff;
    border-radius: 5px;
}
"""


def run_gui() -> None:
    """启动 GUI 窗口（可被 CLI 的 gui 子命令调用）。"""
    app = QApplication(sys.argv)
    app.setApplicationName("TangiPromo")
    app.setApplicationDisplayName("TangiPromo")
    app.setOrganizationName("TangiPromo")
    app.setOrganizationDomain("promokit.local")
    app.setStyle("Fusion")

    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#0b0b0d"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#f4f4f6"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#141418"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1c1c22"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#f4f4f6"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#2a2a33"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#f4f4f6"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#7c6bff"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#23232a"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#f4f4f6"))
    app.setPalette(pal)

    app.setStyleSheet(DARK_STYLESHEET)

    _avail = frozenset(QFontDatabase.families())
    font = QFont()
    font.setPointSize(13)
    for family in ("Inter", "SF Pro Text", "Helvetica Neue", "Segoe UI", "PingFang SC", "Arial"):
        if family in _avail:
            font.setFamily(family)
            break
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def main() -> None:
    """应用入口：有参数时走 CLI（含 --help），否则启动 GUI。"""
    if len(sys.argv) > 1:
        from src.cli import run_cli
        run_cli()
        return
    run_gui()


if __name__ == "__main__":
    main()
