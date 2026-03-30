import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QFont
from src.main_window import MainWindow

DARK_STYLESHEET = """
QWidget {
    background-color: #141416;
    color: #f2f2f7;
    font-size: 13px;
    font-family: "Helvetica Neue", "PingFang SC", "SF Pro Text", sans-serif;
}
QMainWindow { background-color: #0e0e10; }
QGroupBox {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    margin-top: 16px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
    color: #98989d;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    background-color: rgba(44, 44, 46, 0.35);
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 2px 8px;
    background-color: transparent;
}
QComboBox {
    background-color: rgba(58, 58, 60, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 6px 12px;
    min-height: 30px;
    selection-background-color: #0a84ff;
}
QComboBox:hover { border-color: rgba(10, 132, 255, 0.45); background-color: #3a3a3c; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #aeaeb2;
    width: 0; height: 0;
}
QComboBox QAbstractItemView {
    background-color: #2c2c2e;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    selection-background-color: #0a84ff;
    padding: 6px;
    outline: none;
}
QPushButton {
    background-color: rgba(58, 58, 60, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 7px 16px;
    min-height: 32px;
    font-weight: 550;
}
QPushButton:hover { background-color: #48484a; border-color: rgba(255, 255, 255, 0.16); }
QPushButton:pressed { background-color: #2c2c2e; }
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5ac8fa, stop:1 #0a84ff);
    border: none;
    color: white;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #7ad4ff, stop:1 #409cff);
}
QPushButton#primaryBtn:pressed { background-color: #0070d9; }
QPushButton#dangerBtn {
    background-color: rgba(255, 69, 58, 0.92);
    border: none;
    color: white;
}
QPushButton#dangerBtn:hover { background-color: #ff6961; }
QPushButton#ghostBtn {
    background-color: transparent;
    border: 1px dashed rgba(255, 255, 255, 0.2);
    color: #aeaeb2;
}
QPushButton#ghostBtn:hover { border-color: rgba(10, 132, 255, 0.5); color: #f2f2f7; }
QSlider::groove:horizontal {
    height: 5px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 20px; height: 20px;
    background: #ffffff;
    border-radius: 10px;
    margin: -8px 0;
    border: 1px solid rgba(0, 0, 0, 0.12);
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5ac8fa, stop:1 #0a84ff);
    border-radius: 3px;
}
QListWidget {
    background-color: rgba(28, 28, 30, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 8px;
    margin: 2px 6px;
}
QListWidget::item:selected { background-color: #0a84ff; color: white; }
QListWidget::item:hover:!selected { background-color: rgba(58, 58, 60, 0.85); }
QScrollBar:vertical {
    width: 10px; background: transparent; margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.18); border-radius: 5px; min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.28); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.18); border-radius: 5px; min-width: 28px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QTextEdit {
    background-color: #0c0c0e;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
    font-size: 12px;
    color: #b4f396;
    padding: 10px;
    selection-background-color: #0a84ff;
}
QLineEdit {
    background-color: rgba(58, 58, 60, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 6px 12px;
    min-height: 30px;
    selection-background-color: #0a84ff;
}
QLineEdit:focus { border-color: #0a84ff; }
QLabel { background: transparent; border: none; }
QSplitter::handle { background: rgba(255, 255, 255, 0.06); }
QSplitter::handle:horizontal { width: 2px; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    background: rgba(44, 44, 46, 0.9);
}
QCheckBox::indicator:checked {
    background: #0a84ff;
    border-color: #0a84ff;
    image: none;
}
QDoubleSpinBox, QSpinBox {
    background-color: rgba(58, 58, 60, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 5px 10px;
    min-height: 30px;
}
QToolTip {
    background-color: #3a3a3c;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: #f2f2f7;
    padding: 6px 10px;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TangiPromo")
    app.setApplicationDisplayName("TangiPromo")
    app.setOrganizationName("TangiPromo")
    app.setOrganizationDomain("promokit.local")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)

    font = QFont("Helvetica Neue")
    font.setPointSize(13)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
