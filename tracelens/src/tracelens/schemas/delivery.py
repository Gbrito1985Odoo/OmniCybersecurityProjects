"""Esquemas Pydantic para suscripciones de entrega de informes (Fase 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from tracelens.schemas.common import utcnow


class DeliverySubscription(BaseModel):
    """Suscripción: canal, destinatarios, formato, frecuencia y filtros."""

    id: Optional[int] = None
    name: str = Field(min_length=1)
    report_type: Optional[str] = None  # filtro: daily | weekly | incident | adhoc
    channel: Literal["email", "webhook", "local", "s3", "slack", "telegram"]
    recipients: list[str] = Field(default_factory=list)
    format: Literal["markdown", "html", "pdf", "json"] = "markdown"
    cron: Optional[str] = None  # expresión cron; sin cron = manual
    enabled: bool = True
    last_sent_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
