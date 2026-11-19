"""Esquemas Pydantic para reglas de filtrado y etiquetado (Fase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from tracelens.schemas.common import utcnow

RuleOperator = Literal[
    "regex",
    "equals",
    "contains",
    "startswith",
    "endswith",
    "gt",
    "lt",
    "gte",
    "lte",
    "in",
    "not_in",
]


class RuleMatch(BaseModel):
    """Condición simple: campo, operador y valor."""

    field: str = Field(min_length=1)  # service, message, level, source, trace_id, raw...
    operator: RuleOperator
    value: Any = None
    case_sensitive: bool = True


class Rule(BaseModel):
    """Regla de filtrado/etiquetado configurable.

    Lista blanca (ignorar coincidencias) / lista negra (forzar análisis).
    Condiciones: `matches` combinadas con AND; grupos de `any_of_groups`
    combinados entre sí con OR.
    """

    id: Optional[int] = None
    name: str = Field(min_length=1)
    enabled: bool = True
    priority: int = 0
    origin: Optional[str] = None  # fichero, host o servicio
    white_list: bool = False
    black_list: bool = False
    matches: list[RuleMatch] = Field(default_factory=list)
    any_of_groups: list[list[RuleMatch]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None
