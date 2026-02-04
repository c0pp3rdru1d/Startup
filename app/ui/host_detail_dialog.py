from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QWidget,
    QComboBox,
)

from sqlmodel import select, desc

from app.db import get_session
from app.models import Host, CheckResult


@dataclass
class Row:
    ts: str
    check_type: str
    target: str
    ok: bool
    rtt: Optional[float]
    message: str


class HostResultsModel(QAbstractTableModel):
    COLS = ["Time (UTC)", "Type", "Target", "OK", "RTT (ms)", "Message"]

    def __init__(self):
        super().__init__()
        self.rows: List[Row] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole:
            return None
        return self.COLS[section] if orientation == Qt.Horizontal else section + 1

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        r = self.rows[index.row()]
        c = index.column()

        if role == Qt.DisplayRole:
            if c == 0:
                return r.ts
            if c == 1:
                return r.check_type
            if c == 2:
                return r.target
            if c == 3:
                return "YES" if r.ok else "NO"
            if c == 4:
                return "" if r.rtt is None else f"{r.rtt:.1f}"
            if c == 5:
                return r.message
        return None

    def set_rows(self, rows: List[Row]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class HostDetailDialog(QDialog):
    def __init__(self, host_id: int, parent=None):
        super().__init__(parent)
        self.host_id = int(host_id)
        self.setWindowTitle(f"Host Details #{self.host_id}")
        self.resize(900, 600)

        self.lbl_title = QLabel("")
        self.lbl_stats = QLabel("")
        self.lbl_stats.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.filter_type = QComboBox()
        self.filter_type.addItems(["all", "ping", "tcp"])
        self.filter_type.currentTextChanged.connect(self.refresh)

        self.model = HostResultsModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(self.lbl_title)
        top.addStretch(1)
        top.addWidget(QLabel("Type:"))
        top.addWidget(self.filter_type)
        top.addWidget(self.btn_refresh)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.lbl_stats)
        layout.addWidget(self.view)

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
            host = session.get(Host, self.host_id)
            if not host:
                self.lbl_title.setText("Host not found")
                self.model.set_rows([])
                return

            self.lbl_title.setText(f"{host.name}  —  {host.address}   [tags: {host.tags}]")

            q = select(CheckResult).where(CheckResult.host_id == self.host_id)
            t = self.filter_type.currentText()
            if t != "all":
                q = q.where(CheckResult.check_type == t)
            q = q.order_by(desc(CheckResult.ts)).limit(300)

            results = list(session.exec(q))

            # Summary stats: fail streak across all types (or filtered type)
            streak = 0
            for r in results:
                if r.ok:
                    break
                streak += 1

            total = len(results)
            ok_count = sum(1 for r in results if r.ok)
            uptime = (ok_count / total * 100.0) if total else 0.0

        self.lbl_stats.setText(
            f"Last {total} checks | Uptime: {uptime:.1f}% | Current fail streak: {streak} | TCP ports: {getattr(host,'tcp_ports','')}"
        )

        rows: List[Row] = []
        for r in results:
            rows.append(
                Row(
                    ts=r.ts.strftime("%Y-%m-%d %H:%M:%S"),
                    check_type=r.check_type,
                    target=r.target or "",
                    ok=bool(r.ok),
                    rtt=r.rtt_ms,
                    message=r.message,
                )
            )
        self.model.set_rows(rows)

