from __future__ import annotations

import platform
import subprocess
import re
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
        # -n 1 = one echo request
        # -w timeout in ms
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        # -c 1 = one packet
        # -W timeout in seconds (integer); macOS uses -W in ms? Actually macOS differs.
        # Use -t on mac? It’s messy. We'll do a conservative approach:
        # Linux: -W seconds. macOS: -W ms (in some versions). We'll use 1 and rely on overall subprocess timeout.
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

