"""Esquemas Pydantic para el chat asistido por IA (Fase 6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from tracelens.schemas.common import utcnow


class ChatMessage(BaseModel):
    """Mensaje de una conversación RAG (SSE: streaming token a token)."""

    id: Optional[int] = None
    session_id: int = Field(ge=1)  # Fase 6: id de la sesión ORM
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    tool_call_id: Optional[str] = None  # Fase 6: function-calling
    citations: list[str] = Field(default_factory=list)  # Fase 6: IDs de trazas citadas
    extra: dict[str, Any] = Field(default_factory=dict)  # Fase 6: metadatos
    created_at: datetime = Field(default_factory=utcnow)


class ChatSession(BaseModel):
    """Conversación con el chat RAG: historial persistido y recuperable."""

    id: Optional[int] = None
    session_key: str = Field(min_length=1)  # agent/persona a la que sirve
    title: Optional[str] = None
    status: Literal["active", "closed"] = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None
