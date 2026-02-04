from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QSortFilterProxyModel, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QDialog,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QMessageBox,
    QTableView,
)

from sqlmodel import select
from app.db import get_session
from app.models import Host
from app.ui.host_detail_dialog import HostDetailDialog


class HostDialog(QDialog):
    def __init__(self, parent=None, host: Host | None = None):
        super().__init__(parent)
        self.setWindowTitle("Host")
        self._host = host

        self.name = QLineEdit(host.name if host else "")
        self.addr = QLineEdit(host.address if host else "")
        self.tcp_ports = QLineEdit(getattr(host, "tcp_ports", "") if host else "")
        self.tcp_ports.setPlaceholderText("e.g. 3389,445,5985 (leave blank to disable TCP checks)")

        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(host.enabled if host else True)

        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Address", self.addr)
        form.addRow("Tags (comma)", self.tags)
        form.addRow("TCP Ports (comma)", self.tcp_ports)
        form.addRow("", self.enabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, str, str, str, bool]:
        return (
            self.name.text().strip(),
            self.addr.text().strip(),
            self.tags.text().strip(),
            self.tcp_ports.text().strip(),
            self.enabled.isChecked(),
        )


class HostsModel(QAbstractTableModel):
    COLS = ["ID", "Name", "Address", "Tags", "TCP Ports", "Enabled"]

    def __init__(self):
        super().__init__()
        self.hosts: List[Host] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.hosts)

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
        h = self.hosts[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return str(h.id)
            if col == 1:
                return h.name
            if col == 2:
                return h.address
            if col == 3:
                return h.tags
            if col == 4:
                return getattr(h, "tcp_ports", "22,80,443")
            if col == 5:
                return "Yes" if h.enabled else "No"

        return None

    def set_hosts(self, hosts: List[Host]) -> None:
        self.beginResetModel()
        self.hosts = hosts
        self.endResetModel()

    def get_host_at(self, row: int) -> Optional[Host]:
        if 0 <= row < len(self.hosts):
            return self.hosts[row]
        return None


class HostsFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._needle = ""

    def set_search(self, text: str) -> None:
        self._needle = (text or "").strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._needle:
            return True

        m: HostsModel = self.sourceModel()  # type: ignore
        h = m.get_host_at(source_row)
        if not h:
            return False

        blob = f"{h.name} {h.address} {h.tags} {getattr(h,'tcp_ports','')}".lower()
        return self._needle in blob


class HostsWidget(QWidget):
    hosts_changed = Signal()

    def __init__(self):
        super().__init__()

        self.model = HostsModel()
        self.proxy = HostsFilterProxy()
        self.proxy.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setSelectionMode(QTableView.SingleSelection)
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.doubleClicked.connect(self.open_details)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search hosts (name, address, tags, ports)…")
        self.search.textChanged.connect(self.proxy.set_search)

        self.btn_add = QPushButton("Add")
        self.btn_edit = QPushButton("Edit")
        self.btn_del = QPushButton("Delete")
        self.btn_refresh = QPushButton("Refresh")

        self.btn_add.clicked.connect(self.add_host)
        self.btn_edit.clicked.connect(self.edit_host)
        self.btn_del.clicked.connect(self.delete_host)
        self.btn_refresh.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(QLabel("Hosts"))
        top.addStretch(1)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_edit)
        top.addWidget(self.btn_del)
        top.addWidget(self.btn_refresh)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.search)
        layout.addWidget(self.view)

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
            hosts = list(session.exec(select(Host)))
        self.model.set_hosts(hosts)
        self.hosts_changed.emit()

    def _selected_host(self) -> Host | None:
        idxs = self.view.selectionModel().selectedRows()
        if not idxs:
            return None
        proxy_index = idxs[0]
        source_index = self.proxy.mapToSource(proxy_index)
        return self.model.get_host_at(source_index.row())

    def open_details(self) -> None:
        h = self._selected_host()
        if not h or h.id is None:
            return
        dlg = HostDetailDialog(int(h.id), parent=self)
        dlg.exec()

    def add_host(self) -> None:
        dlg = HostDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        name, addr, tags, tcp_ports, enabled = dlg.get_data()
        if not name or not addr:
            QMessageBox.warning(self, "Validation", "Name and Address are required.")
            return

        with get_session() as session:
            session.add(Host(name=name, address=addr, tags=tags, tcp_ports=tcp_ports, enabled=enabled))
            session.commit()

        self.refresh()

    def edit_host(self) -> None:
        host = self._selected_host()
        if not host or host.id is None:
            QMessageBox.information(self, "Edit", "Select a host row first.")
            return

        dlg = HostDialog(self, host=host)
        if dlg.exec() != QDialog.Accepted:
            return

        name, addr, tags, tcp_ports, enabled = dlg.get_data()
        if not name or not addr:
            QMessageBox.warning(self, "Validation", "Name and Address are required.")
            return

        with get_session() as session:
            h2 = session.get(Host, host.id)
            if not h2:
                QMessageBox.warning(self, "Edit", "Host not found.")
                return
            h2.name = name
            h2.address = addr
            h2.tags = tags
            h2.tcp_ports = tcp_ports
            h2.enabled = enabled
            session.add(h2)
            session.commit()

        self.refresh()

    def delete_host(self) -> None:
        host = self._selected_host()
        if not host or host.id is None:
            QMessageBox.information(self, "Delete", "Select a host row first.")
            return

        if QMessageBox.question(self, "Delete", f"Delete host #{host.id}?") != QMessageBox.Yes:
            return

        with get_session() as session:
            h2 = session.get(Host, host.id)
            if h2:
                session.delete(h2)
                session.commit()

        self.refresh()

