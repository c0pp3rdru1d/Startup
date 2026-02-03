from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QStatusBar,
)
from PySide6.QtCore import Qt

from app.ui.hosts_widget import HostsWidget
from app.ui.results_widget import ResultsWidget
from app.monitor import MonitorThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SentinelDesk")
        self.resize(1100, 700)

        self.tabs = QTabWidget()

        self.hosts = HostsWidget()
        self.results = ResultsWidget()

        self.tabs.addTab(self.hosts, "Hosts")
        self.tabs.addTab(self.results, "Results")

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(self.tabs)
        self.setCentralWidget(root)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready.")

        # Monitoring thread
        self.monitor = MonitorThread(interval_s=10, timeout_ms=1000, parent=self)
        self.monitor.result.connect(self.results.on_new_result)
        self.monitor.status.connect(self.statusBar().showMessage)

        # If hosts change, refresh result view convenience
        self.hosts.hosts_changed.connect(self.results.refresh)

        self.monitor.start()

    def closeEvent(self, event):
        try:
            self.monitor.stop()
            self.monitor.wait(2000)
        finally:
            event.accept()

