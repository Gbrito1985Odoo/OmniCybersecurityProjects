"""Ses Previously: motor de reglas de filtrado — allow/deny, combinación
AND/OR, listas blancas/negras, dry-run y métricas (Fase 3.1a)."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional

from tracelens.schemas.rule import Rule, RuleMatch
from tracelens.schemas.trace import Span, Trace, TraceStatus


class RuleMatchError(ValueError):
    """Error al evaluar o crear un RuleMatch inválido."""


def _lookup(trace: Trace, field: str, default=None):
    """Lee un campo de una traza (service, message, severity... + metadata)."""
    value = getattr(trace, field, None)
    if value is not None:
        return value
    return trace.metadata.get(field, default)


def _norm(value) -> object:
    """Normaliza un valor para comparación segura (strings minusculas)."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip().lower()
        return v or None
    return value


class RuleMatcher(ABC):
    """Evalúa un RuleMatch contra una traza."""

    @abstractmethod
    def matches(self, trace: Trace) -> bool:
        """True si la traza cumple la condición."""


class RegexMatcher(RuleMatcher):
    def __init__(self, m: RuleMatch) -> None:
        self._m = m
        flags = 0 if m.case_sensitive else re.IGNORECASE
        self._rx = re.compile(str(m.value), flags)

    def matches(self, trace: Trace) -> bool:
        value = _lookup(trace, self._m.field)
        return bool(value is not None and self._rx.search(str(value)))


class ExactMatcher(RuleMatcher):
    def __init__(self, m: RuleMatch) -> None:
        self._m = m

    def matches(self, trace: Trace) -> bool:
        value = _lookup(trace, self._m.field)
        return _norm(value) == _norm(self._m.value)


class ContainsMatcher(RuleMatcher):
    def __init__(self, m: RuleMatch) -> None:
        self._m = m

    def matches(self, trace: Trace) -> bool:
        value = _lookup(trace, self._m.field)
        return value is not None and str(_norm(self._m.value) or "") in str(value).lower()


class StartsWithMatcher(RuleMatcher):
    def __init__(self, m: RuleMatch) -> None:
        self._m = m

    def matches(self, trace: Trace) -> bool:
        value = _lookup(trace, self._m.field)
        return value is not None and str(value).startswith(str(self._m.value))


class EndsWithMatcher(RuleMatcher):
    def __init__(self, m: RuleMatch) -> None:
        self._m = m

    def matches(self, trace: Trace) -> bool:
        value = _lookup(trace, self._m.field)
        return value is not None and str(value).endswith(str(self._m.value))


class NumericMatcher(RuleMatcher):
    """Comparadores numéricos (gt/lt/gte/lte); maneja severidad (enum str)."""

    def __init__(self, m: RuleMatch, op: str) -> None:
        self._m = m
        self._op = op

    def matches(self, trace: Trace) -> bool:
        value = _lookup(trace, self._m.field)
        if value is None:
            return False
        try:
            if isinstance(value, TraceStatus):
                target = TraceStatus(str(self._m.value).lower())
                ordered = [TraceStatus.info, TraceStatus.warning, TraceStatus.error, TraceStatus.critical]
                a, b = ordered.index(value), ordered.index(target)
                return {"gt": a > b, "lt": a < b, "gte": a >= b, "lte": a <= b}[self._op]
            num = float(value)
            target = float(self._m.value)
        except (TypeError, ValueError):
            return False
        return {"gt": num > target, "lt": num < target, "gte": num >= target, "lte": num <= target}[self._op]


class InMatcher(RuleMatcher):
    """in / not_in: pertenencia a una lista de valores."""

    def __init__(self, m: RuleMatch) -> None:
        self._m = m

    def matches(self, trace: Trace) -> bool:
        value = _lookup(trace, self._m.field)
        if not isinstance(self._m.value, list):
            return False
        in_list = _norm(value) in [_norm(v) for v in self._m.value]
        return in_list if self._m.operator == "in" else not in_list


class NotMatcher(RuleMatcher):
    """not: negación de un matcher hijo (opcional)."""

    def __init__(self, inner: RuleMatcher) -> None:
        self._inner = inner

    def matches(self, trace: Trace) -> bool:
        return not self._inner.matches(trace)


def create_matcher(m: RuleMatch) -> RuleMatcher:
    """Construye el matcher apropiado para un RuleMatch."""
    op = m.operator
    if op == "regex":
        return RegexMatcher(m)
    if op == "equals":
        return ExactMatcher(m)
    if op == "contains":
        return ContainsMatcher(m)
    if op == "startswith":
        return StartsWithMatcher(m)
    if op == "endswith":
        return EndsWithMatcher(m)
    if op == "gt":
        return NumericMatcher(m, "gt")
    if op == "lt":
        return NumericMatcher(m, "lt")
    if op == "gte":
        return NumericMatcher(m, "gte")
    if op == "lte":
        return NumericMatcher(m, "lte")
    if op in ("in", "not_in"):
        return InMatcher(m)
    raise RuleMatchError(f"Operador inválido: {op}")


def rule_matches(rule: Rule, trace: Trace) -> bool:
    """Evalúa `matches` (AND) o `any_of_groups` (OR); una regla sin condiciones se aplica."""
    matchers = [create_matcher(x) for x in rule.matches if _lookup(trace, x.field) is not None]
    if rule.matches:
        return all(m.matches(trace) for m in matchers)
    if rule.any_of_groups:
        return any(
            all(create_matcher(x).matches(trace) for x in g if _lookup(trace, x.field) is not None)
            for g in rule.any_of_groups
            if g
        )
    return True


class RuleEngine:
    """Motor de reglas: allow/deny con prioridades, dry-run y métricas."""

    def __init__(self) -> None:
        self._rules: list[Rule] = []

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    # -- CRUD -------------------------------------------------------------
    def add_rule(self, rule: Rule) -> Rule:
        self._rules.append(rule)
        self._reorder()
        return rule

    def update_rule(self, rule: Rule) -> Rule:
        self._rules = [r if r.id == rule.id else rule for r in self._rules]
        self._reorder()
        return rule

    def delete_rule(self, name: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) != before

    def _reorder(self) -> None:
        self._rules.sort(key=lambda r: (-r.priority, r.id or 0))

    def _active(self) -> list[Rule]:
        return [r for r in self._rules if r.enabled]

    # -- evaluación -------------------------------------------------------
    def evaluate(self, trace: Trace) -> bool:
        """True si la traza está permitida (no filtrada)."""
        for rule in self._active():
            if rule_matches(rule, trace):
                return bool(rule.white_list)
        return True

    def evaluate_many(self, traces: list[Trace]) -> list[Trace]:
        """Filtra trazas; devuelve las permitidas."""
        return [t for t in traces if self.evaluate(t)]

    def matched_rule(self, trace: Trace) -> Optional[Rule]:
        """Regla activa cuyo resultado se aplica (None si no aplica)."""
        for rule in self._active():
            if rule_matches(rule, trace):
                return rule
        return None

    def dry_run(self, traces: list[Trace]) -> dict:
        """Evalúa contra trazas históricas; devuelve allow/deny y métricas."""
        by_rule: dict[str, int] = {r.name: 0 for r in self._rules}
        filtered = 0
        for t in traces:
            if not self.evaluate(t):
                filtered += 1
                mr = self.matched_rule(t)
                if mr:
                    by_rule[mr.name] = by_rule.get(mr.name, 0) + 1
        return {
            "total": len(traces),
            "filtered": filtered,
            "allowed": len(traces) - filtered,
            "by_rule": {k: v for k, v in by_rule.items() if v},
        }
