"""Esquemas Pydantic para trazas normalizadas (Fase 1).

Parsing de trazas crudas -> Trace llega en la Fase 2 (ingesta/parsers).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from tracelens.schemas.common import utcnow


class TraceStatus(str, Enum):
    """Severidad de una traza (Fase 3: motor de reglas)."""

    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"

    @classmethod
    def order(cls, status: "TraceStatus") -> int:
        """Orden de severidad: info < warning < error < critical."""
        return {"info": 0, "warning": 1, "error": 2, "critical": 3}[status.value]

    @classmethod
    def is_at_least(cls, status: "TraceStatus", minimum: "TraceStatus") -> bool:
        """True si `status` está al menos en la severidad `minimum`."""
        return cls.order(status) >= cls.order(minimum)


class SpanKind(str, Enum):
    """Tipo de un seguimiento dentro de una traza."""

    server = "server"
    client = "client"
    internal = "internal"
    background = "background"


class Span(BaseModel):
    """Un seguimiento dentro de una traza."""

    name: str = Field(min_length=1)
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.info
    error: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    """Traza normalizada: unidad base de almacenamiento y análisis."""

    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=utcnow)
    service: str = Field(min_length=1)
    message: str
    severity: TraceStatus = TraceStatus.info
    source: Optional[str] = None  # archivo:línea, endpoint u origen de la traza
    trace_id: Optional[str] = None  # ID del trace-padre (para correlación)
    labels: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw: Optional[dict[str, Any]] = None
    spans: list[Span] = Field(default_factory=list)
