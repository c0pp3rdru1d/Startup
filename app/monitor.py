from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

from PySide6.QtCore import QThread, Signal
from sqlmodel import select, desc

from app.db import get_session
from app.models import Host, CheckResult, AlertEvent
from app.ping import ping_once, tcp_check


def _parse_ports(s: str) -> List[int]:
    out: List[int] = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            p = int(part)
            if 1 <= p <= 65535:
                out.append(p)
        except ValueError:
            continue
    seen = set()
    uniq = []
    for p in out:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq


class MonitorThread(QThread):
    # (host_id, check_type, target, ok, rtt_ms, ts, message)
    result = Signal(int, str, str, bool, object, object, str)

    # (ts, severity, host_id, check_type, target, message)
    alert = Signal(object, str, int, str, str, str)

    status = Signal(str)

    def __init__(self, interval_s: int = 10, timeout_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.interval_s = max(1, int(interval_s))
        self.timeout_ms = max(100, int(timeout_ms))
        self._running = True

        # Automatic alert policy (MVP defaults)
        self.ping_fail_threshold = 3
        self.tcp_fail_threshold = 3
        self.cooldown_seconds = 300  # 5 minutes

        # In-memory cooldown tracker to avoid DB-heavy lookups
        self._last_alert_at: Dict[Tuple[int, str, str], datetime] = {}

    def stop(self) -> None:
        self._running = False

    def _store_result(self, host_id: int, check_type: str, target: str, ok: bool, rtt_ms, ts, message: str) -> None:
        try:
            with get_session() as session:
                session.add(
                    CheckResult(
                        host_id=host_id,
                        ts=ts,
                        check_type=check_type,
                        target=target or "",
                        ok=ok,
                        rtt_ms=rtt_ms,
                        message=message,
                    )
                )
                session.commit()
        except Exception as e:
            self.status.emit(f"DB write error: {e}")

    def _fail_streak(self, host_id: int, check_type: str, target: str, limit: int = 50) -> int:
        with get_session() as session:
            recent = list(
                session.exec(
                    select(CheckResult)
                    .where(
                        CheckResult.host_id == host_id,
                        CheckResult.check_type == check_type,
                        CheckResult.target == (target or ""),
                    )
                    .order_by(desc(CheckResult.ts))
                    .limit(limit)
                )
            )
        streak = 0
        for r in recent:
            if r.ok:
                break
            streak += 1
        return streak

    def _maybe_alert(self, host: Host, check_type: str, target: str, threshold: int) -> None:
        host_id = int(host.id or 0)
        key = (host_id, check_type, target or "")
        now = datetime.utcnow()

        streak = self._fail_streak(host_id, check_type, target)
        if streak < threshold:
            return

        # Cooldown
        last = self._last_alert_at.get(key)
        if last and (now - last) < timedelta(seconds=self.cooldown_seconds):
            return

        msg = f"{host.name} ({host.address}) {check_type.upper()} {target or ''} failing: streak={streak}".strip()

        # store alert event
        try:
            with get_session() as session:
                session.add(
                    AlertEvent(
                        ts=now,
                        host_id=host_id,
                        check_type=check_type,
                        target=(target or ""),
                        severity="CRIT",
                        message=msg,
                    )
                )
                session.commit()
        except Exception as e:
            self.status.emit(f"DB alert write error: {e}")

        self._last_alert_at[key] = now
        self.alert.emit(now, "CRIT", host_id, check_type, (target or ""), msg)

    def run(self) -> None:
        self.status.emit(f"Monitor running: interval={self.interval_s}s timeout={self.timeout_ms}ms")

        while self._running:
            loop_start = time.time()

            try:
                with get_session() as session:
                    hosts: List[Host] = list(session.exec(select(Host).where(Host.enabled == True)))  # noqa: E712
            except Exception as e:
                self.status.emit(f"DB read error: {e}")
                hosts = []

            for h in hosts:
                if not self._running:
                    break
                host_id = int(h.id or 0)

                # PING
                pr = ping_once(h.address, timeout_ms=self.timeout_ms)
                ts = datetime.utcnow()
                self._store_result(host_id, "ping", "", pr.ok, pr.rtt_ms, ts, pr.message)
                self.result.emit(host_id, "ping", "", pr.ok, pr.rtt_ms, ts, pr.message)

                # Automatic ping alert
                if not pr.ok:
                    self._maybe_alert(h, "ping", "", threshold=self.ping_fail_threshold)

                # TCP (only if ports configured)
                ports = _parse_ports(getattr(h, "tcp_ports", "") or "")
                if ports:
                    for p in ports:
                        if not self._running:
                            break
                        tr = tcp_check(h.address, p, timeout_ms=min(1200, self.timeout_ms))
                        ts2 = datetime.utcnow()
                        tgt = str(p)

                        self._store_result(host_id, "tcp", tgt, tr.ok, tr.rtt_ms, ts2, tr.message)
                        self.result.emit(host_id, "tcp", tgt, tr.ok, tr.rtt_ms, ts2, tr.message)

                        # Automatic tcp alert
                        if not tr.ok:
                            self._maybe_alert(h, "tcp", tgt, threshold=self.tcp_fail_threshold)

            elapsed = time.time() - loop_start
            sleep_for = max(0.1, self.interval_s - elapsed)

            end_time = time.time() + sleep_for
            while self._running and time.time() < end_time:
                time.sleep(0.1)

        self.status.emit("Monitor stopped.")

