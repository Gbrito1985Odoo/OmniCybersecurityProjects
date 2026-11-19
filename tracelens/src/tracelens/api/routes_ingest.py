"""API de ingesta y operación sobre trazas (Fases 2-3).

Routes: POST /api/ingest/file (carga de fichero/directorio con checkpoint),
POST /api/ingest/tail (RFC5424/3164 + regex configurable), POST /api/ingest/udp
y TCP (pares datagram/segmento), GET /api/traces (listado paginado y filtros),
GET /api/traces/{id}, PUT /api/traces/{id}, POST /api/ingest/ping.

Compartidos entre módulos: APPCtx creado por la app; los endpoints usan
asyncio.Queue por espera: el motor de entrega de logs (UDP/TCP) consigue
Trama como diccionario JSON del payload entrante y las convierte en Trace.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile

from tracelens.config import AppConfig
from tracelens.ingestion import FileIngestor
from tracelens.ingestion.parsers import JsonParser, RegexParser
from tracelens.schemas.trace import Trace
from tracelens.storage.trace_store import TraceStore

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


def _to_trace(payload: dict[str, Any]) -> Trace:
    """Convierte el diccionario del payload UDP/TCP en Trace."""
    from tracelens.ingestion.parsers import raw_to_trace

    return raw_to_trace(payload, source="network")


@router.post("/file", summary="Carga de ficheros o directorios")
async def ingest_file(
    path: str,
    ctx: "APPCtx",
    progress: bool = False,
) -> dict[str, Any]:
    """Carga trazas de fichero(s)/directorio; con checkpoint y reanudación."""
    ingestor = FileIngestor(ctx.trace_store, ctx.parser, checkpoint_file=ctx.checkpoint_file)
    stored = await ingestor.load(path)
    return {"path": path, "stored": stored}


@router.post("/upload", summary="Sube un fichero")
async def ingest_upload(
    file: UploadFile,
    ctx: "APPCtx",
) -> dict[str, Any]:
    """Recibe un fichero multipart, lo guarda en data/uploads y lo parsea."""
    from pathlib import Path

    data_dir = Path(ctx.config.data_path)
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / "uploads" / file.filename
    target.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    target.write_bytes(content)
    ingestor = FileIngestor(ctx.trace_store, ctx.parser)
    stored = await ingestor.load(str(target))
    return {"path": str(target), "stored": stored}


@router.post("/tail", summary="Tailing de fichero con transformación (RFC5424/3164/regex)")
async def ingest_tail(
    request: Request,
    ctx: "APPCtx",
) -> dict[str, Any]:
    """Captura líneas de un fichero: parser auto-detectado RFC5424/RFC3164/regex."""
    form = await request.form()
    paths = form.getlist("paths")
    if not paths:
        raise HTTPException(status_code=400, detail="Se requiere 'paths'")
    stop_event = asyncio.Event()
    # El polling del tail termina al cerrar el request (client disconnect).
    async def _stop_when_disconnected():
        await request.is_disconnected()
        stop_event.set()
    asyncio.create_task(_stop_when_disconnected())
    collected: list[Trace] = []

    async def on_line(line: str):
        for t in ctx.parser.parse(line):
            collected.append(t)

    await ctx.parser.tail_files(paths, on_line, stop_event)
    await ctx.trace_store.batch_save(collected)
    return {"captured": len(collected)}


@router.post("/udp", summary="Ingesta UDP (datagramas -> Trama)")
async def ingest_udp(request: Request, ctx: "APPCtx") -> dict[str, Any]:
    """Recibe datagramas UDP (uno por payload JSON), convierte y guarda."""
    payloads = await request.json()
    if isinstance(payloads, dict):
        payloads = [payloads]
    stored = 0
    for raw in payloads:
        t = _to_trace(raw)
        await ctx.trace_store.save(t)
        stored += 1
    return {"stored": stored}


@router.post("/tcp", summary="Ingesta TCP (bytes -> Trama)")
async def ingest_tcp(request: Request, ctx: "APPCtx") -> dict[str, Any]:
    """Recibe bytes TCP (un texto JSON por línea), convierte y guarda."""
    text = await request.body()
    raw_lines = [ln for ln in text.decode("utf-8", errors="replace").splitlines() if ln.strip()]
    stored = 0
    for raw in raw_lines:
        try:
            t = _to_trace(json.loads(raw))
        except json.JSONDecodeError:
            continue
        await ctx.trace_store.save(t)
        stored += 1
    return {"stored": stored}


class _SyncToAsyncTail:
    """Adaptador: tail blocking -> tail asyncio."""

    def __init__(self, coro):
        self._coro = coro

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self._coro.__anext__()
        except StopAsyncIteration:
            raise
