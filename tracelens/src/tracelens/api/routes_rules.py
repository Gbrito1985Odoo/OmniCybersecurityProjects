"""Routes de la API de reglas (Fase 3.1a): CRUD sobre RulesApi."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from tracelens.api.ctx import get_ctx
from tracelens.rules import RuleEngine
from tracelens.schemas.rule import Rule

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _get_api():
    from tracelens.rules.api import RulesApi
    ctx = get_ctx()
    if not hasattr(ctx, "rules_api") or ctx.rules_api is None:
        ctx.rules_api = RulesApi(RuleEngine())
    return ctx.rules_api


@router.get("/", summary="Lista reglas")
def list_rules() -> dict:
    """Lista reglas (ordenadas por prioridad)."""
    return {"rules": [r.model_dump(mode="json") for r in _get_api().list_rules()]}


@router.post("/", summary="Crea una regla", status_code=201)
def create_rule(rule: Rule) -> dict:
    """Crea una regla; devuelve el objeto creado con id asignado."""
    created = _get_api().create_rule(rule)
    return created.model_dump(mode="json")


@router.get("/{name}", summary="Obtiene una regla por nombre")
def get_rule(name: str) -> dict:
    """Obtiene una regla por nombre."""
    rule = _get_api().get_rule(name)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Regla {name!r} no encontrada")
    return rule.model_dump(mode="json")


@router.put("/{name}", summary="Actualiza una regla")
def update_rule(name: str, rule: Rule) -> dict:
    """Actualiza una regla existente."""
    rule.name = name
    updated = _get_api().update_rule(rule)
    return updated.model_dump(mode="json")


@router.delete("/{name}", summary="Elimina una regla")
def delete_rule(name: str) -> dict:
    """Elimina una regla por nombre."""
    ok = _get_api().delete_rule(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Regla {name!r} no encontrada")
    return {"deleted": name}
