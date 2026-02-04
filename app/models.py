from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Host(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str
    tags: str = ""
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # IMPORTANT: default empty to avoid false TCP failures on endpoints
    tcp_ports: str = ""  # comma-separated, e.g. "22,80,443"


class CheckResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    host_id: int = Field(index=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)

    check_type: str = Field(default="ping", index=True)  # "ping" or "tcp"
    target: str = Field(default="", index=True)          # e.g. "443" for tcp

    ok: bool
    rtt_ms: Optional[float] = None
    message: str = ""


class AlertEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    host_id: int = Field(index=True)

    check_type: str = Field(index=True)   # ping/tcp
    target: str = Field(default="", index=True)

    severity: str = "CRIT"  # MVP
    message: str = ""

