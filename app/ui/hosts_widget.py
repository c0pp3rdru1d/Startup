from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QCheckBox,
    QLabel,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
)

from sqlmodel import select

from app.db import get_session
from app.models import Host


class HostDialog(QDialog):
    def __init__(self, parent=None, host: Host | None = None):
        super().__init__(parent)
        self.setWindowTitle("Host")
        self._host = host

        self.name = QLineEdit(host.name if host else "")
        self.addr = QLineEdit(host.address if host else "")
        self.tags = QLineEdit(host.tags if host else "")
        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(host.enabled if host else True)

        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Address", self.addr)
        form.addRow("Tags", self.tags)
        form.addRow("", self.enabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, str, str, bool]:
        return (
            self.name.text().strip(),
            self.addr.text().strip(),
            self.tags.text().strip(),
            self.enabled.isChecked(),
        )


class HostsWidget(QWidget):
    hosts_changed = Signal()

    COLS = ["ID", "Name", "Address", "Tags", "Enabled"]

    def __init__(self):
        super().__init__()

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setSortingEnabled(True)

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
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
            hosts = list(session.exec(select(Host)))

        self.table.setRowCount(0)
        for h in hosts:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(h.id)))
            self.table.setItem(row, 1, QTableWidgetItem(h.name))
            self.table.setItem(row, 2, QTableWidgetItem(h.address))
            self.table.setItem(row, 3, QTableWidgetItem(h.tags))
            self.table.setItem(row, 4, QTableWidgetItem("Yes" if h.enabled else "No"))

        self.hosts_changed.emit()

    def _selected_host_id(self) -> int | None:
        items = self.table.selectedItems()
        if not items:
            return None
        # ID is column 0
        try:
            return int(items[0].text())
        except ValueError:
            return None

    def add_host(self) -> None:
        dlg = HostDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        name, addr, tags, enabled = dlg.get_data()
        if not name or not addr:
            QMessageBox.warning(self, "Validation", "Name and Address are required.")
            return

        with get_session() as session:
            session.add(Host(name=name, address=addr, tags=tags, enabled=enabled))
            session.commit()

        self.refresh()

    def edit_host(self) -> None:
        hid = self._selected_host_id()
        if hid is None:
            QMessageBox.information(self, "Edit", "Select a host row first.")
            return

        with get_session() as session:
            host = session.get(Host, hid)
            if not host:
                QMessageBox.warning(self, "Edit", "Host not found.")
                return

        dlg = HostDialog(self, host=host)
        if dlg.exec() != QDialog.Accepted:
            return

        name, addr, tags, enabled = dlg.get_data()
        if not name or not addr:
            QMessageBox.warning(self, "Validation", "Name and Address are required.")
            return

        with get_session() as session:
            host2 = session.get(Host, hid)
            if not host2:
                QMessageBox.warning(self, "Edit", "Host not found.")
                return
            host2.name = name
            host2.address = addr
            host2.tags = tags
            host2.enabled = enabled
            session.add(host2)
            session.commit()

        self.refresh()

    def delete_host(self) -> None:
        hid = self._selected_host_id()
        if hid is None:
            QMessageBox.information(self, "Delete", "Select a host row first.")
            return

        if QMessageBox.question(self, "Delete", f"Delete host #{hid}?") != QMessageBox.Yes:
            return

        with get_session() as session:
            host = session.get(Host, hid)
            if host:
                session.delete(host)
                session.commit()

        self.refresh()

