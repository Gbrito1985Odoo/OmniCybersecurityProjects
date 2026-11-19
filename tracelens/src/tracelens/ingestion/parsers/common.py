"""Contrato Parser + funciones compartidas de parsers (Fase 2).

`Parser.parse(text) -> list[Trace]`; módulo hoja sin importes circulares
(importado por parsers/__init__ antes de los parsers concretos).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from tracelens.schemas.common import utcnow
from tracelens.schemas.trace import Span, Trace, TraceStatus


class Parser(ABC):
    """Contrato de un parser de trazas (Fase 2)."""

    name: str = "base"

    @abstractmethod
    def parse(self, text: str) -> list[Trace]:
        """Parsea texto (línea o bloque); devuelve las trazas que contiene."""


def to_severity(value: object) -> TraceStatus:
    """Convierte cualquier valor a TraceStatus; default info."""
    if isinstance(value, TraceStatus):
        return value
    try:
        return TraceStatus(str(value).lower())
    except ValueError:
        return TraceStatus.info


def to_timestamp(value: object) -> Optional[datetime]:
    """Convierte ISO/RFC3339 con zona UTC; None si no se puede parsear."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def raw_to_trace(raw: dict[str, Any], source: str = "ingest") -> Trace:
    """Convierte el diccionario crudo extraído por un parser en Trace."""
    timestamp = to_timestamp(raw.get("timestamp")) or utcnow()
    service = raw.get("service") or raw.get("hostname") or source
    return Trace(
        timestamp=timestamp,
        service=str(service),
        message=str(raw.get("message") or ""),
        severity=to_severity(raw.get("severity")),
        source=str(raw.get("source") or source),
        raw=dict(raw),
    )
