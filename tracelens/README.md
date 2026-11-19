# TraceLens

Analizador inteligente de trazas (logs/traces) con IA local: etiquetado automático,
filtrado con listas blancas/negras, informes automatizados y chat RAG sobre las trazas.

> **Fase 1 (en desarrollo):** núcleo y almacenamiento — estructura del proyecto,
> config, esquemas Pydantic, `TraceStore` (SQLAlchemy) y `VectorStore` (ChromaDB).

## Stack

- Python 3.11+ / FastAPI + Uvicorn
- SQLite (por defecto) / PostgreSQL vía SQLAlchemy async
- ChromaDB local (vector store); embeddings vía Ollama (Fase 4)
- CLI Typer, APScheduler para informes, Jinja2, pytest

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
pip install -e ".[dev]"
```

## Pruebas (Fase 1)

```bash
python -m pytest
```

## Configuración

`config/config.yaml` + variables de entorno `TRACELENS_*` (ver `.env.example`).

El resto de las fases completan: ingesta/parsers (Fase 2), filtrado/etiquetado
(Fase 3), motor IA (Fase 4), informes/entrega (Fase 5), chat RAG (Fase 6) y
frontend/Docker/README final (Fase 7).
