from __future__ import annotations

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication) -> None:
    """
    A clean, readable dark theme using Fusion palette.
    Centralize theme here so we can evolve styling later.
    """
    app.setStyle("Fusion")

    p = QPalette()
    p.setColor(QPalette.Window, QColor(30, 30, 34))
    p.setColor(QPalette.WindowText, QColor(230, 230, 235))
    p.setColor(QPalette.Base, QColor(22, 22, 26))
    p.setColor(QPalette.AlternateBase, QColor(30, 30, 34))
    p.setColor(QPalette.ToolTipBase, QColor(230, 230, 235))
    p.setColor(QPalette.ToolTipText, QColor(230, 230, 235))
    p.setColor(QPalette.Text, QColor(230, 230, 235))
    p.setColor(QPalette.Button, QColor(40, 40, 46))
    p.setColor(QPalette.ButtonText, QColor(230, 230, 235))
    p.setColor(QPalette.BrightText, QColor(255, 0, 0))

    # Accent colors
    p.setColor(QPalette.Highlight, QColor(78, 135, 255))
    p.setColor(QPalette.HighlightedText, QColor(10, 10, 12))

    # Disabled
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(140, 140, 150))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(140, 140, 150))

    app.setPalette(p)

    # A little extra polish (not too much; we’re not making a Vegas casino)
    app.setStyleSheet("""
        QToolTip { 
            color: #e6e6eb; 
            background-color: #2a2a30; 
            border: 1px solid #4e87ff; 
            padding: 6px;
        }
        QHeaderView::section {
            background-color: #2a2a30;
            color: #e6e6eb;
            padding: 6px;
            border: 0px;
            border-bottom: 1px solid #3a3a44;
        }
        QLineEdit, QComboBox {
            padding: 6px;
            border-radius: 6px;
            border: 1px solid #3a3a44;
            background: #16161a;
        }
        QPushButton {
            padding: 6px 10px;
            border-radius: 8px;
            border: 1px solid #3a3a44;
            background: #28282e;
        }
        QPushButton:hover {
            border: 1px solid #4e87ff;
        }
        QPushButton:pressed {
            background: #1f1f25;
        }
    """)

