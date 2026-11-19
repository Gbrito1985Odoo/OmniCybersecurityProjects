"""Tests de los endpoints de reglas (Fase 3.1b): CRUD via HTTP."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tracelens.api.ctx import APPCtx, set_ctx
from tracelens.config import AppConfig
from tracelens.main import app


@pytest.fixture()
async def client():
    set_ctx(APPCtx(config=AppConfig(), trace_store=None))  # type: ignore[arg-type]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


async def test_create_list_get_delete(client: AsyncClient) -> None:
    r = await client.post("/api/rules/", json={"name": "black-db", "black_list": True})
    assert r.status_code == 201
    rule = r.json()
    assert rule["id"] is not None
    assert rule["name"] == "black-db"

    r2 = await client.get("/api/rules/")
    assert any(x["name"] == "black-db" for x in r2.json()["rules"])

    r3 = await client.get(f"/api/rules/{rule['name']}")
    assert r3.status_code == 200

    r4 = await client.delete(f"/api/rules/{rule['name']}")
    assert r4.status_code == 200

    assert (await client.get(f"/api/rules/{rule['name']}")).status_code == 404


async def test_update_rule(client: AsyncClient) -> None:
    r = await client.post("/api/rules/", json={"name": "r1", "white_list": True})
    assert r.status_code == 201
    r = await client.put("/api/rules/r1", json={"name": "r1", "white_list": True, "enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False


async def test_create_invalid_422(client: AsyncClient) -> None:
    r = await client.post("/api/rules/", json={"name": ""})
    assert r.status_code == 422
