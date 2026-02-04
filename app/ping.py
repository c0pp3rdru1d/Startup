from __future__ import annotations

import platform
import subprocess
import re
import socket
from dataclasses import dataclass
from typing import Optional


@dataclass
class PingResult:
    ok: bool
    rtt_ms: Optional[float]
    message: str


_RTT_RE = re.compile(r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE)


def ping_once(host: str, timeout_ms: int = 1000) -> PingResult:
    system = platform.system().lower()

    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        cmd = ["ping", "-c", "1", host]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(2, timeout_ms / 1000 + 1),
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        ok = proc.returncode == 0

        rtt = None
        m = _RTT_RE.search(out)
        if m:
            try:
                rtt = float(m.group(1))
            except ValueError:
                rtt = None

        msg = "OK" if ok else "No reply"
        return PingResult(ok=ok, rtt_ms=rtt, message=msg)

    except subprocess.TimeoutExpired:
        return PingResult(ok=False, rtt_ms=None, message="Timeout")
    except Exception as e:
        return PingResult(ok=False, rtt_ms=None, message=f"Ping error: {e}")


def tcp_check(host: str, port: int, timeout_ms: int = 800) -> PingResult:
    """
    TCP connect check. RTT is approximate connect time.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(max(0.2, timeout_ms / 1000))
    try:
        import time

        t0 = time.time()
        s.connect((host, int(port)))
        rtt = (time.time() - t0) * 1000.0
        return PingResult(ok=True, rtt_ms=rtt, message="TCP open")
    except Exception as e:
        return PingResult(ok=False, rtt_ms=None, message=f"TCP fail: {type(e).__name__}")
    finally:
        try:
            s.close()
        except Exception:
            pass

