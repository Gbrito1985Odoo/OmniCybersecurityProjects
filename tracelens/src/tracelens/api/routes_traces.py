"""API de consultas y gestión de trazas (Fases 2+).

Routes: GET /api/traces (listado paginado + filtros), GET /api/traces/{id},
PUT /api/traces/{id}, DELETE /api/traces/{id}, GET /api/traces/stats.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from tracelens.schemas.trace import TraceStatus
from tracelens.storage.trace_store import TraceStore

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("/", summary="Lista trazas (paginado y filtros)")
async def list_traces(
    service: Optional[str] = None,
    severity: Optional[list[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ctx: "APPCtx" = None,  # type: ignore[assignment]
) -> dict:
    """Lista trazas (nuevas primero). Ctx inyectado por la app."""
    from tracelens.api.ctx import get_ctx

    store: TraceStore = get_ctx(ctx).trace_store
    traces = await store.list(service=service, severity=severity, limit=limit, offset=offset)
    return {
        "traces": [t.model_dump(mode="json") for t in traces],
        "total": await store.count(service=service, severity=severity),
    }


@router.get("/{trace_id}", summary="Devuelve una traza por id")
async def get_trace(trace_id: str, ctx: "APPCtx" = None) -> dict:
    """Devuelve una traza por id."""
    from tracelens.api.ctx import get_ctx

    t = await get_ctx(ctx).trace_store.get(trace_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Traza no encontrada")
    return t.model_dump(mode="json")


@router.put("/{trace_id}", summary="Actualiza campos de una traza")
async def update_trace(
    trace_id: str,
    fields: dict,
    ctx: "APPCtx" = None,
) -> dict:
    """Actualiza campos de una traza."""
    from tracelens.api.ctx import get_ctx

    t = await get_ctx(ctx).trace_store.update(trace_id, **fields)
    if t is None:
        raise HTTPException(status_code=404, detail="Traza no encontrada")
    return t.model_dump(mode="json")


@router.delete("/{trace_id}", summary="Elimina una traza")
async def delete_trace(trace_id: str, ctx: "APPCtx" = None) -> dict:
    """Elimina una traza."""
    from tracelens.api.ctx import get_ctx

    deleted = await get_ctx(ctx).trace_store.delete(trace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Traza no encontrada")
    return {"deleted": trace_id}
