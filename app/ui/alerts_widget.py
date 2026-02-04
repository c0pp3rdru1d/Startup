from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableView

from sqlmodel import select, desc

from app.db import get_session
from app.models import AlertEvent, Host


@dataclass
class AlertRow:
    ts: str
    severity: str
    host: str
    check_type: str
    target: str
    message: str


class AlertsModel(QAbstractTableModel):
    COLS = ["Time (UTC)", "Severity", "Host", "Type", "Target", "Message"]

    def __init__(self):
        super().__init__()
        self.rows: List[AlertRow] = []

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
                return r.severity
            if c == 2:
                return r.host
            if c == 3:
                return r.check_type
            if c == 4:
                return r.target
            if c == 5:
                return r.message
        return None

    def set_rows(self, rows: List[AlertRow]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def prepend(self, row: AlertRow, max_rows: int = 500) -> None:
        self.beginInsertRows(QModelIndex(), 0, 0)
        self.rows.insert(0, row)
        self.endInsertRows()
        if len(self.rows) > max_rows:
            extra = len(self.rows) - max_rows
            self.beginRemoveRows(QModelIndex(), max_rows, max_rows + extra - 1)
            del self.rows[max_rows:max_rows + extra]
            self.endRemoveRows()


class AlertsWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.model = AlertsModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(QLabel("Alerts"))
        top.addStretch(1)
        top.addWidget(self.btn_refresh)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.view)

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
            evts = list(session.exec(select(AlertEvent).order_by(desc(AlertEvent.ts)).limit(300)))
            hosts = {h.id: h for h in session.exec(select(Host))}

        rows: List[AlertRow] = []
        for e in evts:
            h = hosts.get(e.host_id)
            host_label = h.name if h else f"#{e.host_id}"
            rows.append(
                AlertRow(
                    ts=e.ts.strftime("%Y-%m-%d %H:%M:%S"),
                    severity=e.severity,
                    host=host_label,
                    check_type=e.check_type,
                    target=e.target or "",
                    message=e.message,
                )
            )
        self.model.set_rows(rows)

    def on_alert(self, ts, severity: str, host_id: int, check_type: str, target: str, message: str) -> None:
        host_label = f"#{host_id}"
        try:
            with get_session() as session:
                h = session.get(Host, int(host_id))
                if h:
                    host_label = h.name
        except Exception:
            pass

        self.model.prepend(
            AlertRow(
                ts=ts.strftime("%Y-%m-%d %H:%M:%S"),
                severity=severity,
                host=host_label,
                check_type=check_type,
                target=target or "",
                message=message,
            )
        )

