from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QStatusBar,
)

from app.ui.hosts_widget import HostsWidget
from app.ui.results_widget import ResultsWidget
from app.ui.alerts_widget import AlertsWidget
from app.monitor import MonitorThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SentinelDesk")
        self.resize(1200, 750)

        self.tabs = QTabWidget()

        self.hosts = HostsWidget()
        self.results = ResultsWidget()
        self.alerts = AlertsWidget()

        self.tabs.addTab(self.hosts, "Hosts")
        self.tabs.addTab(self.results, "Results")
        self.tabs.addTab(self.alerts, "Alerts")

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(self.tabs)
        self.setCentralWidget(root)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready.")

        self.monitor = MonitorThread(interval_s=10, timeout_ms=1000, parent=self)
        self.monitor.result.connect(self.results.on_new_result)
        self.monitor.alert.connect(self.alerts.on_alert)
        self.monitor.status.connect(self.statusBar().showMessage)

        self.hosts.hosts_changed.connect(self.results.refresh)

        self.monitor.start()

    def closeEvent(self, event):
        try:
            self.monitor.stop()
            self.monitor.wait(2000)
        finally:
            event.accept()

