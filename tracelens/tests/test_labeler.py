"""Tests del labeler (Fase 3.2): etiquetas manuales, por reglas y via API."""

from __future__ import annotations

import pytest

from tracelens.labeler import LabelerApi
from tracelens.rules import RuleEngine
from tracelens.schemas.rule import Rule, RuleMatch
from tracelens.schemas.label import Label
from tracelens.schemas.trace import Trace, TraceStatus
from tracelens.storage.trace_store import SQLAlchemyTraceStore
from tracelens.storage.vector_store import ChromaVectorStore


@pytest.fixture()
async def store(tmp_path) -> SQLAlchemyTraceStore:
    st = SQLAlchemyTraceStore(f"sqlite+aiosqlite:///{tmp_path.as_posix()}/t.db")
    await st.initialize()
    yield st
    await st.aclose()


def make_trace(**kw) -> Trace:
    kw.setdefault("service", "web")
    return Trace(message="m", severity=TraceStatus.info, **kw)


async def test_manual_label_add_and_list(store: SQLAlchemyTraceStore) -> None:
    lab = LabelerApi(store)
    t = make_trace()
    tid = await store.save(t)
    label = await lab.add_manual(tid, name="incident", category="infra", confidence=0.9)
    assert label.id is not None
    assert label.source == "manual"
    all_labels = await lab.get_by_trace(tid)
    assert len(all_labels) == 1 and all_labels[0].name == "incident"


async def test_rule_derived_labels(store: SQLAlchemyTraceStore) -> None:
    engine = RuleEngine()
    engine.add_rule(Rule(name="db-health", black_list=True,
                         matches=[RuleMatch(field="service", operator="equals", value="db")]))
    lab = LabelerApi(store, rule_engine=engine)
    t = make_trace(service="db")
    tid = await store.save(t)
    stored = await lab.apply_rules(tid)
    assert [x.name for x in stored] == ["db-health"]
    assert stored[0].source == "rule"


async def test_labeler_stats(store: SQLAlchemyTraceStore) -> None:
    lab = LabelerApi(store)
    t1 = await store.save(make_trace())
    t2 = await store.save(make_trace())
    await lab.add_manual(t1, name="x")
    await lab.add_manual(t2, name="x")
    stats = await lab.stats()
    assert stats["by_name"]["x"]["count"] == 2
