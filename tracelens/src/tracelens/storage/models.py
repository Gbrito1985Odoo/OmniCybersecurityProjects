"""Modelos SQLAlchemy (Fase 1): tablas de trazas, etiquetas, reglas,
chat y suscripciones de entrega."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timestamp UTC con zona definida."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base de los modelos SQLAlchemy."""


class TraceORM(Base):
    """Tabla de trazas."""

    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True, default="info")
    source: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    raw: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    spans: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LabelORM(Base):
    """Tabla de etiquetas."""

    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("traces.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RuleORM(Base):
    """Tabla de reglas de filtrado."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    origin: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    white_list: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    black_list: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    matches: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    any_of_groups: Mapped[list[list[dict[str, Any]]]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatSessionORM(Base):
    """Tabla de conversaciones (chat RAG, Fase 6)."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatMessageORM(Base):
    """Tabla de mensajes de chat."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    citations: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ReportORM(Base):
    """Tabla de informes."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="markdown")
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeliverySubscriptionORM(Base):
    """Tabla de suscripciones de entrega."""

    __tablename__ = "delivery_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    recipients: Mapped[list[str]] = mapped_column(JSON, default=list)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="markdown")
    cron: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
