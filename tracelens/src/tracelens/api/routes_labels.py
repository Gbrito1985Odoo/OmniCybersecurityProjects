"""Routes de la API de etiquetas (Fase 3.2)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from tracelens.api.ctx import get_ctx
from tracelens.schemas.label import Label
from tracelens.schemas.trace import TraceStatus

router = APIRouter(prefix="/api/labels", tags=["labels"])


def _labeler():
    from tracelens.labeler import LabelerApi
    ctx = get_ctx()
    if not hasattr(ctx, "rules_api") or ctx.rules_api is None:
        ctx.rules_api = LabelerApi(ctx.trace_store)
    return ctx.rules_api


@router.get("/trace/{trace_id}", summary="Lista etiquetas de una traza")
async def list_by_trace(trace_id: str) -> dict:
    """Lista etiquetas de una traza."""
    labels = await _labeler().get_by_trace(trace_id)
    return {"labels": [l.model_dump(mode="json") for l in labels]}


@router.post("/fusionar", summary="Fusiona etiquetas: from_name -> to_name")
async def fuse_labels(payload: dict) -> dict:
    """Fusiona todas las etiquetas `from_name` en `to_name`."""
    count = await _labeler().fuse(payload["from_name"], payload["to_name"])
    return {"fused": count}


@router.post("/{trace_id}", summary="Crea una etiqueta manual en una traza", status_code=201)
async def create_label(trace_id: str, label: dict) -> dict:
    """Crea una etiqueta manual (name + category opcional)."""
    name = label.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="Se requiere 'name'")
    created = await _labeler().add_manual(
        trace_id, name=name, category=label.get("category"),
        confidence=label.get("confidence"),
    )
    return created.model_dump(mode="json")


@router.get("/by-name/{name}", summary="Obtiene etiquetas por nombre")
async def get_by_name(name: str) -> dict:
    """Etiquetas con un nombre."""
    labels = await _labeler().get_by_name(name)
    return {"labels": [l.model_dump(mode="json") for l in labels]}


@router.put("/{label_id}", summary="Renombra una etiqueta")
async def rename_label(label_id: int, payload: dict) -> dict:
    """Renombra una etiqueta existente."""
    labels = await _labeler().rename(payload["from_name"], payload["to_name"])
    return {"updated": len(labels)}


@router.delete("/{label_id}", summary="Elimina una etiqueta")
async def delete_label(label_id: int) -> dict:
    """Elimina una etiqueta por id."""
    deleted = await _labeler().delete(label_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
    return {"deleted": label_id}


@router.get("/stats", summary="Estadísticas de etiquetas")
async def label_stats(name: Optional[str] = None) -> dict:
    """Estadísticas de etiquetas (frecuencia y última actualización)."""
    return await _labeler().stats(name)
