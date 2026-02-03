from __future__ import annotations

import time
from datetime import datetime
from typing import List, Tuple

from PySide6.QtCore import QThread, Signal

from sqlmodel import select

from app.db import get_session
from app.models import Host, CheckResult
from app.ping import ping_once


class MonitorThread(QThread):
    # Emits (host_id, ok, rtt_ms, ts, message)
    result = Signal(int, bool, object, object, str)
    status = Signal(str)

    def __init__(self, interval_s: int = 10, timeout_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.interval_s = max(1, int(interval_s))
        self.timeout_ms = max(100, int(timeout_ms))
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        self.status.emit(f"Monitor running: interval={self.interval_s}s timeout={self.timeout_ms}ms")

        while self._running:
            start = time.time()
            hosts: List[Host] = []

            try:
                with get_session() as session:
                    hosts = list(session.exec(select(Host).where(Host.enabled == True)))  # noqa: E712
            except Exception as e:
                self.status.emit(f"DB read error: {e}")
                hosts = []

            for h in hosts:
                if not self._running:
                    break

                pr = ping_once(h.address, timeout_ms=self.timeout_ms)
                ts = datetime.utcnow()

                try:
                    with get_session() as session:
                        session.add(
                            CheckResult(
                                host_id=h.id or 0,
                                ts=ts,
                                ok=pr.ok,
                                rtt_ms=pr.rtt_ms,
                                message=pr.message,
                            )
                        )
                        session.commit()
                except Exception as e:
                    self.status.emit(f"DB write error for {h.address}: {e}")

                self.result.emit(h.id or 0, pr.ok, pr.rtt_ms, ts, pr.message)

            elapsed = time.time() - start
            sleep_for = max(0.1, self.interval_s - elapsed)

            # Sleep in small chunks so stop() is responsive
            end_time = time.time() + sleep_for
            while self._running and time.time() < end_time:
                time.sleep(0.1)

        self.status.emit("Monitor stopped.")

