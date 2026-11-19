"""Esquemas Pydantic para informes generados (Fase 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from tracelens.schemas.common import utcnow


class Report(BaseModel):
    """Informe generado: contenido, formato y rango de tiempo."""

    id: Optional[int] = None
    report_type: str = Field(min_length=1)  # daily | weekly | incident | range | adhoc
    title: str = Field(min_length=1)
    content: str
    format: Literal["markdown", "html", "pdf", "json"] = "markdown"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    file_path: Optional[str] = None
    generated_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
