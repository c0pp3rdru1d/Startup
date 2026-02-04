from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from app.db import init_db
from app.ui.main_window import MainWindow
from app.ui.theme import apply_dark_theme


def main() -> int:
    init_db()

    app = QApplication(sys.argv)
    apply_dark_theme(app)

    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

