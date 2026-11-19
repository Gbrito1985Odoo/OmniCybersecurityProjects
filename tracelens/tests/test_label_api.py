"""Tests de API de etiquetas (Fase 3.2): CRUD de etiquetas, stats, fusionar."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tracelens.api.ctx import APPCtx, set_ctx
from tracelens.main import app
from tracelens.schemas.trace import Trace
from tracelens.storage.trace_store import SQLAlchemyTraceStore


@pytest.fixture()
async def store(tmp_path):
    st = SQLAlchemyTraceStore(f"sqlite+aiosqlite:///{tmp_path.as_posix()}/t.db")
    await st.initialize()
    yield st
    await st.aclose()


@pytest.fixture()
async def client(store: SQLAlchemyTraceStore):
    set_ctx(APPCtx(config=None, trace_store=store))  # type: ignore[arg-type]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


async def _trace(store: SQLAlchemyTraceStore, service: str = "web") -> str:
    return await store.save(Trace(service=service, message="m"))


async def test_create_get_list_delete_label(store: SQLAlchemyTraceStore, client: AsyncClient) -> None:
    tid = await _trace(store)
    r = await client.post(f"/api/labels/{tid}", json={"name": "incident", "category": "infra"})
    assert r.status_code == 201
    label_id = r.json()["id"]
    assert label_id is not None

    r = await client.get(f"/api/labels/trace/{tid}")
    assert any(x["name"] == "incident" for x in r.json()["labels"])

    r = await client.get("/api/labels/by-name/incident")
    assert r.status_code == 200

    r = await client.delete(f"/api/labels/{label_id}")
    assert r.status_code in (200, 204)


async def test_rename_fusionar_eliminar(store: SQLAlchemyTraceStore, client: AsyncClient) -> None:
    tid = await _trace(store)
    r = await client.post(f"/api/labels/{tid}", json={"name": "x"})
    assert r.status_code == 201
    r2 = await client.post(f"/api/labels/{tid}", json={"name": "y"})
    assert r2.status_code == 201

    r = await client.put("/api/labels/1", json={"from_name": "x", "to_name": "z"})
    assert r.status_code == 200
    r = await client.get("/api/labels/by-name/z")
    assert len(r.json()["labels"]) == 1

    r = await client.post("/api/labels/fusionar", json={"from_name": "z", "to_name": "y"})
    assert r.status_code == 200
    r = await client.get("/api/labels/by-name/y")
    assert len(r.json()["labels"]) == 2


async def test_stats_endpoint(store: SQLAlchemyTraceStore, client: AsyncClient) -> None:
    r = await client.get("/api/labels/stats")
    assert r.status_code == 200
    assert r.json()["total_labels"] == 0
