"""Tests de SQLAlchemyTraceStore (Fase 1)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import pytest

from tracelens.schemas.trace import Trace, TraceStatus
from tracelens.storage.trace_store import SQLAlchemyTraceStore

BASE_TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_trace(
    service: str = "web",
    message: str = "msg",
    severity: TraceStatus = TraceStatus.info,
    age_s: int = 0,
) -> Trace:
    return Trace(
        timestamp=BASE_TS + timedelta(seconds=age_s),
        service=service,
        message=message,
        severity=severity,
    )


@pytest.fixture()
async def store(tmp_path) -> AsyncGenerator[SQLAlchemyTraceStore, None]:
    st = SQLAlchemyTraceStore(f"sqlite+aiosqlite:///{tmp_path.as_posix()}/traces.db")
    await st.initialize()
    yield st
    await st.aclose()


async def test_save_and_get(store: SQLAlchemyTraceStore) -> None:
    t = make_trace(service="web", message="started")
    tid = await store.save(t)
    got = await store.get(tid)
    assert got is not None
    assert got.id == tid
    assert got.service == "web"
    assert got.message == "started"
    assert got.severity == TraceStatus.info


async def test_get_missing(store: SQLAlchemyTraceStore) -> None:
    assert await store.get("does-not-exist") is None


async def test_list_filters(store: SQLAlchemyTraceStore) -> None:
    err_web = make_trace(service="web", severity=TraceStatus.error)
    info_web = make_trace(service="web", severity=TraceStatus.info, age_s=5)
    crit_web = make_trace(service="web", severity=TraceStatus.critical)

    await store.save(err_web)
    await store.save(info_web)
    await store.save(crit_web)

    rows = await store.list(service="web")
    assert len(rows) == 3

    rows = await store.list(service="web", severity=[TraceStatus.error, TraceStatus.critical])
    assert {r.severity for r in rows} == {TraceStatus.error, TraceStatus.critical}

    assert await store.list(service="nope") == []


async def test_list_pagination_and_order(store: SQLAlchemyTraceStore) -> None:
    for i in range(5):
        await store.save(make_trace(service="svc", message=f"m{i}", age_s=i))
    rows = await store.list(limit=2)
    assert [r.message for r in rows] == ["m4", "m3"]
    rows = await store.list(limit=2, offset=4)
    assert [r.message for r in rows] == ["m0"]


async def test_count(store: SQLAlchemyTraceStore) -> None:
    assert await store.count() == 0
    await store.save(make_trace(service="web"))
    await store.save(make_trace(service="api"))
    assert await store.count() == 2
    assert await store.count(service="web") == 1


async def test_update_and_delete(store: SQLAlchemyTraceStore) -> None:
    tid = await store.save(make_trace(service="web"))

    updated = await store.update(tid, severity=TraceStatus.warning, labels=["a"])
    assert updated is not None
    assert updated.severity == TraceStatus.warning
    assert updated.labels == ["a"]

    fetched = await store.get(tid)
    assert fetched is not None
    assert fetched.labels == ["a"]

    assert await store.delete(tid) is True
    assert await store.get(tid) is None
    assert await store.delete(tid) is False
