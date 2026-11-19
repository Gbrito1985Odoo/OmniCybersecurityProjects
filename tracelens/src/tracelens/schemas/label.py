"""Esquemas Pydantic para etiquetas (Fase 4: motor IA)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from tracelens.schemas.common import utcnow


class Label(BaseModel):
    """Etiqueta asignada a una traza.

    Fuentes: auto (IA), manual (usuario/API) y rule (motor de reglas).
    """

    id: Optional[int] = None
    trace_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: Optional[str] = None  # categoría del vocabulario controlado
    source: Literal["auto", "manual", "rule"] = "auto"
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utcnow)
