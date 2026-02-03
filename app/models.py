from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Host(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str  # IP or DNS name
    tags: str = ""  # comma-separated for MVP
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CheckResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host_id: int = Field(index=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)

    ok: bool
    rtt_ms: Optional[float] = None
    message: str = ""

