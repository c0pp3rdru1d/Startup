from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, List

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableView,
)

from sqlmodel import select, desc

from app.db import get_session
from app.models import Host, CheckResult


@dataclass
class ResultRow:
    ts_str: str
    host_name: str
    host_addr: str
    check_type: str
    target: str
    ok: bool
    rtt: Optional[float]
    message: str


class ResultsModel(QAbstractTableModel):
    COLS = ["Time (UTC)", "Host", "Address", "Type", "Target", "OK", "RTT (ms)", "Message"]

    def __init__(self):
        super().__init__()
        self.rows: List[ResultRow] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.COLS[section]
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        r = self.rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return r.ts_str
            if col == 1:
                return r.host_name
            if col == 2:
                return r.host_addr
            if col == 3:
                return r.check_type
            if col == 4:
                return r.target
            if col == 5:
                return "YES" if r.ok else "NO"
            if col == 6:
                return "" if r.rtt is None else f"{r.rtt:.1f}"
            if col == 7:
                return r.message

        if role == Qt.ForegroundRole and col in (0, 1, 2, 3, 4, 5, 6):
            return QColor(170, 255, 170) if r.ok else QColor(255, 170, 170)

        return None

    def set_rows(self, rows: List[ResultRow]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def prepend_row(self, row: ResultRow, max_rows: int = 800) -> None:
        self.beginInsertRows(QModelIndex(), 0, 0)
        self.rows.insert(0, row)
        self.endInsertRows()

        if len(self.rows) > max_rows:
            extra = len(self.rows) - max_rows
            start = max_rows
            end = max_rows + extra - 1
            self.beginRemoveRows(QModelIndex(), start, end)
            del self.rows[start:start + extra]
            self.endRemoveRows()


class ResultsWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.model = ResultsModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setSelectionMode(QTableView.SingleSelection)
        self.view.horizontalHeader().setStretchLastSection(True)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(QLabel("Latest Results"))
        top.addStretch(1)
        top.addWidget(self.btn_refresh)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.view)

        self.refresh()

    def refresh(self) -> None:
        N = 400
        with get_session() as session:
            results = list(session.exec(select(CheckResult).order_by(desc(CheckResult.ts)).limit(N)))
            hosts = list(session.exec(select(Host)))
            host_map = {h.id: h for h in hosts}

        rows: List[ResultRow] = []
        for r in results:
            h = host_map.get(r.host_id)
            host_name = h.name if h else f"#{r.host_id}"
            host_addr = h.address if h else "?"

            rows.append(
                ResultRow(
                    ts_str=r.ts.strftime("%Y-%m-%d %H:%M:%S"),
                    host_name=host_name,
                    host_addr=host_addr,
                    check_type=getattr(r, "check_type", "ping"),
                    target=getattr(r, "target", "") or "",
                    ok=bool(r.ok),
                    rtt=r.rtt_ms,
                    message=r.message,
                )
            )

        self.model.set_rows(rows)

    def on_new_result(self, host_id: int, check_type: str, target: str, ok: bool, rtt_ms, ts, message: str) -> None:
        host_name = f"#{host_id}"
        host_addr = "?"

        try:
            with get_session() as session:
                h = session.get(Host, int(host_id))
                if h:
                    host_name = h.name
                    host_addr = h.address
        except Exception:
            pass

        self.model.prepend_row(
            ResultRow(
                ts_str=ts.strftime("%Y-%m-%d %H:%M:%S"),
                host_name=host_name,
                host_addr=host_addr,
                check_type=check_type,
                target=target or "",
                ok=bool(ok),
                rtt=None if rtt_ms is None else float(rtt_ms),
                message=message,
            ),
            max_rows=800,
        )

