from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from sqlmodel import select, desc

from app.db import get_session
from app.models import Host, CheckResult


class ResultsWidget(QWidget):
    COLS = ["Time (UTC)", "Host", "Address", "OK", "RTT (ms)", "Message"]

    def __init__(self):
        super().__init__()

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setSortingEnabled(False)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(QLabel("Latest Results"))
        top.addStretch(1)
        top.addWidget(self.btn_refresh)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        # Show the most recent N results across all hosts
        N = 200
        with get_session() as session:
            results = list(session.exec(select(CheckResult).order_by(desc(CheckResult.ts)).limit(N)))
            host_map = {h.id: h for h in session.exec(select(Host))}

        self.table.setRowCount(0)
        for r in results:
            h = host_map.get(r.host_id)
            host_name = h.name if h else f"#{r.host_id}"
            host_addr = h.address if h else "?"

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(r.ts.strftime("%Y-%m-%d %H:%M:%S")))
            self.table.setItem(row, 1, QTableWidgetItem(host_name))
            self.table.setItem(row, 2, QTableWidgetItem(host_addr))
            self.table.setItem(row, 3, QTableWidgetItem("YES" if r.ok else "NO"))
            self.table.setItem(row, 4, QTableWidgetItem("" if r.rtt_ms is None else f"{r.rtt_ms:.1f}"))
            self.table.setItem(row, 5, QTableWidgetItem(r.message))

    def on_new_result(self, host_id: int, ok: bool, rtt_ms, ts, message: str) -> None:
        # Simple approach: refresh the view so it stays current.
        # Later we’ll do incremental updates for performance.
        self.refresh()

