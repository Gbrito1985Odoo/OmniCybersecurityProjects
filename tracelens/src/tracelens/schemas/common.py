"""Utilidades compartidas de esquemas Pydantic."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timestamp UTC con zona definida."""
    return datetime.now(timezone.utc)
