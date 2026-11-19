"""Services de la API de reglas (Fase 3.1a).

RulesApi: CRUD sobre RulesEngine + RulesYamlStore con hot-reload.
"""

from __future__ import annotations

from tracelens.rules.engine import RuleEngine
from tracelens.schemas.rule import Rule
from tracelens.services.rules_yaml import RulesYamlStore


class RulesApi:
    """API de reglas: CRUD + dry-run + métricas."""

    def __init__(self, engine: RuleEngine, store: RulesYamlStore | None = None,
                 reload_path: str | None = None) -> None:
        self.engine = engine
        self._store = store or RulesYamlStore(reload_path)
        if reload_path:
            self._reload()

    # -- CRUD -------------------------------------------------------------
    def create_rule(self, rule: Rule) -> Rule:
        ids = [r.id for r in self.engine.rules if r.id is not None]
        rule.id = (max(ids) + 1) if ids else 1
        self.engine.add_rule(rule)
        self._save()
        return rule

    def update_rule(self, rule: Rule) -> Rule:
        self.engine.update_rule(rule)
        self._save()
        return rule

    def delete_rule(self, key) -> bool:
        ok = self._delete_by_key(key)
        if ok:
            self._save()
        return ok

    def _delete_by_key(self, key) -> bool:
        target = self.get_rule(key)
        if target is None:
            return False
        return self.engine.delete_rule(target.name)

    def get_rule(self, key) -> Rule | None:
        """Obtiene una regla por nombre o id."""
        k = str(key)
        return next(
            (r for r in self.engine.rules
             if r.name == k or (r.id is not None and str(r.id) == k)),
            None,
        )

    def delete_rule(self, key) -> bool:
        target = self.get_rule(key)
        if target is None:
            return False
        return self.engine.delete_rule(target.name)

    def list_rules(self) -> list[Rule]:
        return self.engine.rules

    # -- evaluación / métricas --------------------------------------------
    def evaluate(self, trace) -> bool:
        return self.engine.evaluate(trace)

    def dry_run(self, traces) -> dict:
        return self.engine.dry_run(traces)

    # -- persistencia ------------------------------------------------------
    def _save(self) -> None:
        self._store.save(self.engine.rules)

    def _reload(self) -> None:
        loaded = self._store.load()
        self.engine._rules = loaded  # noqa: SLF001

    def _sample(self, trace=None):
        """Traza de ejemplo para tests (crea una simple si falta)."""
        if trace is not None:
            return trace
        from tracelens.schemas.trace import Trace
        return Trace(service="web", message="test")
