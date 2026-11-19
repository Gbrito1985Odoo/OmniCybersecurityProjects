"""API de etiquetas (Fase 3.2): CRUD de etiquetas + stats + fusionar."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from tracelens.labeler.engine import LabelsByRuleEngine, tags_from_trace
from tracelens.rules import RuleEngine
from tracelens.schemas.label import Label
from tracelens.storage.trace_store import TraceStore


class LabelerApi:
    """API de etiquetas: CRUD, derivación por reglas, stats, fusionar."""

    def __init__(
        self,
        trace_store: TraceStore,
        rule_engine: Optional[RuleEngine] = None,
    ) -> None:
        self._store = trace_store
        self._rule_engine = rule_engine or RuleEngine()

    # -- CRUD ---------------------------------------------------------------
    async def add_manual(
        self, trace_id: str, name: str, category: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Label:
        """Etiqueta manual creada por el usuario."""
        label = Label(trace_id=trace_id, name=name, category=category,
                      source="manual", confidence=confidence)
        label.id = await self._store.add_label(label)
        return label

    async def add_auto(
        self, trace_id: str, name: str, confidence: Optional[float] = None,
    ) -> Label:
        """Etiqueta generada por IA/reglas."""
        label = Label(trace_id=trace_id, name=name, source="auto", confidence=confidence)
        label.id = await self._store.add_label(label)
        return label

    async def get_by_trace(self, trace_id: str) -> list[Label]:
        """Etiquetas de una traza."""
        return await self._store.get_labels_by_trace(trace_id)

    async def get_by_name(self, name: str) -> list[Label]:
        """Etiquetas con un nombre (todas)."""
        return await self._store.get_labels_by_name(name)

    async def delete_by_name(self, name: str) -> int:
        """Elimina todas las etiquetas con un nombre; devuelve count."""
        labels = await self._store.get_labels_by_name(name)
        for label in labels:
            await self._store.delete_label(label.id)
        return len(labels)

    async def rename(self, old_name: str, new_name: str) -> list[Label]:
        """Renombra una etiqueta (mantiene ids)."""
        labels = await self._store.get_labels_by_name(old_name)
        for label in labels:
            label.name = new_name
            await self._store.update_label(label)
        return labels

    async def delete(self, label_id: int) -> bool:
        """Elimina una etiqueta."""
        return await self._store.delete_label(label_id)

    async def delete_by_name(self, name: str) -> int:
        """Elimina todas las etiquetas con un nombre; devuelve count."""
        labels = await self._store.get_labels_by_name(name)
        for label in labels:
            await self._store.delete_label(label.id)
        return len(labels)

    async def fuse(self, from_name: str, to_name: str) -> int:
        """Fusiona todas las etiquetas de `from_name` en `to_name`; devuelve count."""
        labels = await self._store.get_labels_by_name(from_name)
        for label in labels:
            label.name = to_name
            await self._store.update_label(label)
        return len(labels)

    async def stats(self, name: Optional[str] = None) -> dict:
        """Estadísticas por etiqueta (frecuencia, última actualización)."""
        all_labels = await self._store.list_labels()
        counter = Counter(l.name for l in all_labels)
        stats: dict = {}
        for name_, count in counter.items():
            if name is not None and name_ != name:
                continue
            recent = [l for l in all_labels if l.name == name_]
            stats[name_] = {
                "count": count,
                "last_updated_at": max(l.created_at for l in recent).isoformat(),
            }
        if name is not None and name not in stats:
            stats[name] = {"count": 0}
        total = sum(s["count"] for s in stats.values())
        return {"total_labels": total, "by_name": stats}

    # -- derivación por reglas (Fase 3.2) ------------------------------------
    async def apply_rules(self, trace_id: str) -> list[Label]:
        """Aplica etiquetas por reglas a una traza (reglas activas)."""
        trace = await self._store.get(trace_id)
        if trace is None:
            return []
        out = []
        for name in tags_from_trace(self._rule_engine, trace):
            label = await self.add_auto(trace_id, name)
            label.source = "rule"
            out.append(label)
        return out

    def _rule_tags(self, trace) -> list[str]:
        engine = LabelsByRuleEngine(self._rule_engine)
        return engine.tags(trace)
