"""Ctx de la app: almacenamiento (TraceStore, VectorStore) y parser activo.

Modular para Fases 2+: añade slots e instancias de RouteRegistry/VectorClient.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from tracelens.config import AppConfig
from tracelens.ingestion import FileIngestor, Parser
from tracelens.storage import ChromaVectorStore, SQLAlchemyTraceStore

if TYPE_CHECKING:
    pass


@dataclass
class APPCtx:
    """Ctx de la app: storages y parser activo (Fases 2+)."""

    config: AppConfig
    trace_store: SQLAlchemyTraceStore
    vector_store: Optional[ChromaVectorStore] = None
    parser: Optional[Parser] = None
    checkpoint_file: Optional[str] = None
    rules_api: Optional[object] = None  # RulesApi (Fase 3)
    _stamps: dict = field(default_factory=dict)


_ctx_instance: Optional[APPCtx] = None


def set_ctx(ctx: APPCtx) -> None:
    """Establece el ctx de la app (por defecto: acceso via get_ctx())."""
    global _ctx_instance
    _ctx_instance = ctx


def get_ctx(ctx: Optional[APPCtx] = None) -> APPCtx:
    """Recupera el ctx; así se inyecta en los routers."""
    global _ctx_instance
    if ctx is not None:
        _ctx_instance = ctx
    if _ctx_instance is None:
        raise RuntimeError("APPCtx no está configurado; llama a set_ctx()")
    return _ctx_instance


def make_ctx(config: AppConfig) -> APPCtx:
    """Ctx por defecto (Fase 1: TraceStore SQLAlchemy + VectorStore ChromaDB)."""
    import pathlib

    config.data_path.mkdir(parents=True, exist_ok=True)
    ctx = APPCtx(
        config=config,
        trace_store=SQLAlchemyTraceStore(config.db_url),
    )
    return ctx
