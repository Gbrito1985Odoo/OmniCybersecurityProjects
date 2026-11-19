"""Engine de etiquetado (Fase 3.2): derivación de etiquetas por reglas."""

from __future__ import annotations

from collections import Counter

from tracelens.rules import RuleEngine
from tracelens.schemas.label import Label
from tracelens.schemas.trace import Trace


def tags_from_trace(rule_engine: RuleEngine, trace: Trace) -> list[str]:
    """Deriva etiquetas (nombre = nombre de la regla) cuando una regla aplica."""
    names: list[str] = []
    for rule in rule_engine._active():  # noqa: SLF001 (documentado)
        from tracelens.rules.engine import rule_matches
        if rule_matches(rule, trace):
            names.append(rule.name)
    return names


class LabelsByRuleEngine:
    """Etiquetas derivadas de reglas; stand-alone para Fase 3.2/3.3."""

    def __init__(self, rule_engine: RuleEngine) -> None:
        self.rule_engine = rule_engine

    def tags(self, trace: Trace) -> list[str]:
        return tags_from_trace(self.rule_engine, trace)
