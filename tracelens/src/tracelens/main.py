"""Punto de entrada FastAPI: API REST (Fases 2+)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from tracelens.api.ctx import make_ctx, set_ctx
from tracelens.api.routes_ingest import router as ingest_router
from tracelens.api.routes_labels import router as labels_router
from tracelens.api.routes_rules import router as rules_router
from tracelens.api.routes_traces import router as traces_router
from tracelens.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa almacenamiento al arrancar (Fase 2+)."""
    settings = get_settings()
    set_ctx(make_ctx(settings))
    yield


def create_app() -> FastAPI:
    """Crea la app FastAPI con el router base."""
    app = FastAPI(title="TraceLens API", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {"service": "tracelens", "version": "0.1.0", "docs": "/docs"}

    app.include_router(traces_router)
    app.include_router(ingest_router)
    app.include_router(rules_router)
    app.include_router(labels_router)
    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
