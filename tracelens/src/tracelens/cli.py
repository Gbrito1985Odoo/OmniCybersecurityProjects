"""CLI Typer (Fases 2+)."""

from __future__ import annotations

import typer

from tracelens.config import get_settings
from tracelens.rules import RuleEngine
from tracelens.services.rules_yaml import RulesYamlStore

app = typer.Typer(help="TraceLens CLI: ingesta, análisis, informes y chat.")


@app.command()
def health() -> None:
    """Verifica el estado del servicio y la configuración."""
    settings = get_settings()
    typer.echo(f"TraceLens OK (db: {settings.db_url}, log: {settings.log_level})")


@app.command()
def rules_list() -> None:
    """Lista las reglas de filtrado."""
    engine = RuleEngine()
    store = RulesYamlStore()
    for r in store.load():
        typer.echo(f"{r.name}: {'WHITE' if r.white_list else 'BLACK'} {len(r.matches)} matches")


@app.command()
def labels_list(store_path: str = ".tracelens/labels.json") -> None:
    """Lista las etiquetas (Fase 3.2)."""
    from tracelens.labeler.api import LabelerApi
    from tracelens.storage.trace_store import SQLAlchemyTraceStore
    import asyncio
    store = SQLAlchemyTraceStore("sqlite+aiosqlite:///./data/tracelens.db")
    asyncio.run(store.initialize())
    lab = LabelerApi(store)
    labels = asyncio.run(lab.stats())["by_name"]
    for name, info in sorted(labels.items()):
        typer.echo(f"{name}: {info['count']}")
    asyncio.run(store.aclose())


@app.command()
def labels_add(trace_id: str, name: str) -> None:
    """Añade una etiqueta manual a una traza (Fase 3.2)."""
    from tracelens.labeler.api import LabelerApi
    from tracelens.storage.trace_store import SQLAlchemyTraceStore
    import asyncio
    store = SQLAlchemyTraceStore("sqlite+aiosqlite:///./data/tracelens.db")
    asyncio.run(store.initialize())
    asyncio.run(LabelerApi(store).add_manual(trace_id, name))
    asyncio.run(store.aclose())
    typer.echo(f"Etiqueta '{name}' añadida a {trace_id[:8]}...")


@app.command()
def labels_stats() -> None:
    """Estadísticas de etiquetas (Fase 3.2)."""
    from tracelens.labeler.api import LabelerApi
    from tracelens.storage.trace_store import SQLAlchemyTraceStore
    import asyncio
    store = SQLAlchemyTraceStore("sqlite+aiosqlite:///./data/tracelens.db")
    asyncio.run(store.initialize())
    stats = asyncio.run(LabelerApi(store).stats())["by_name"]
    for name, info in sorted(stats.items()):
        typer.echo(f"{name}: {info['count']}")
    asyncio.run(store.aclose())


@app.command()
def rules_check() -> None:
    """Valida la configuración de reglas (dry-run sin trazas)."""
    engine = RuleEngine()
    store = RulesYamlStore()
    for r in store.load():
        engine.add_rule(r)
    typer.echo(f"{len(engine.rules)} reglas cargadas OK")


if __name__ == "__main__":  # pragma: no cover
    app()
