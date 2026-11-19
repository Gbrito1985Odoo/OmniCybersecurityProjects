"""Tests de AppConfig y loaders de config.yaml (Fase 1)."""

from __future__ import annotations

from pathlib import Path

from tracelens.config import AppConfig, load_yaml_file


def test_defaults(monkeypatch) -> None:
    for key in ("TRACELENS_DB_URL", "TRACELENS_ANALYSIS_MODEL", "TRACELENS_EMBED_MODEL"):
        monkeypatch.delenv(key, raising=False)
    cfg = AppConfig()
    assert cfg.db_url == "sqlite+aiosqlite:///./data/tracelens.db"
    assert cfg.vector_store_type == "chroma"
    assert cfg.chroma_persist_dir == "./data/chroma"
    assert cfg.ollama_host == "http://localhost:11434"
    assert cfg.analysis_model == "llama3.2:3b"
    assert cfg.embed_model == "nomic-embed-text"
    assert cfg.ingestion_buffer_size == 1000
    assert cfg.ingestion_checkpoint_interval == 100
    assert cfg.data_dir == "data"


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("TRACELENS_DB_URL", "sqlite+aiosqlite:///:memory:")
    cfg = AppConfig()
    assert cfg.db_url == "sqlite+aiosqlite:///:memory:"


def test_load_yaml_file(tmp_path: Path) -> None:
    f = tmp_path / "config.yaml"
    f.write_text("log_level: DEBUG\n", encoding="utf-8")
    data = load_yaml_file(f)
    assert data["log_level"] == "DEBUG"
    assert load_yaml_file(tmp_path / "missing.yaml") == {}
