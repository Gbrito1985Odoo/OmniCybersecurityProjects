"""Rules yaml store (Fase 3.1b): reglas.yaml por defecto y CRUD."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from tracelens.schemas.rule import Rule, RuleMatch

# rules.yaml por defecto (Fase 3.1a)
DEFAULT_RULES_YAML = """rules: []
"""


class RulesYamlStore:
    """Reglas en un archivo YAML con hot-reload del engine."""

    def __init__(self, path: Optional[str] = None) -> None:
        from tracelens.config import PROJECT_ROOT
        self._path = Path(path) if path else PROJECT_ROOT / "config" / "rules.yaml"

    def save(self, rules: list[Rule]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "rules": [
                {
                    "name": r.name,
                    "enabled": r.enabled,
                    "priority": r.priority,
                    "origin": r.origin,
                    "white_list": r.white_list,
                    "black_list": r.black_list,
                    "matches": [m.model_dump(exclude_none=True) for m in r.matches],
                    "any_of_groups": [[m.model_dump(exclude_none=True) for m in g] for g in r.any_of_groups],
                    "tags": r.tags,
                }
                for r in rules
            ]
        }
        self._path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    def load(self) -> list[Rule]:
        if not self._path.is_file():
            return []
        raw = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        out = []
        for i, item in enumerate(raw.get("rules") or []):
            out.append(Rule(id=i + 1, **item))
        return out
