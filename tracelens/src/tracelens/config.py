"""Gestión de configuración: AppConfig (Pydantic Settings) + cargadores YAML.

Fase 1: AppConfig (env TRACELENS_*) y `config.yaml`. Secciones adicionales:
reglas (Fase 3), reports (Fase 5) y chat (Fase 6).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raíz del proyecto (contiene config/, src/, data/ ...).
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CONFIG_DIR: Path = PROJECT_ROOT / "config"
DEFAULT_CONFIG_FILE: Path = CONFIG_DIR / "config.yaml"


class AppConfig(BaseSettings):
    """Configuración global de TraceLens (prefijo de env: TRACELENS_)."""

    model_config = SettingsConfigDict(env_prefix="TRACELENS_", env_file=".env", extra="ignore")

    # Base de datos (SQLite por defecto; PostgreSQL vía SQLAlchemy async)
    db_url: str = "sqlite+aiosqlite:///./data/tracelens.db"

    # Vector store: ChromaDB (ChromaVectorStore)
    vector_store_type: str = "chroma"
    chroma_persist_dir: str = "./data/chroma"

    # Ollama: runtime de LLM local
    ollama_host: str = "http://localhost:11434"
    analysis_model: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"

    # Ingesta (Fase 2)
    ingestion_buffer_size: int = 1000
    ingestion_checkpoint_interval: int = 100

    # Logging (structlog/loguru)
    log_level: str = "INFO"

    # Audit de conversaciones (Fase 6)
    audit_enabled: bool = True

    # Directorios
    data_dir: str = "data"
    config_dir: str = "config"
    prompts_dir: str = "prompts"

    @property
    def data_path(self) -> Path:
        return PROJECT_ROOT / self.data_dir

    @property
    def config_path(self) -> Path:
        return PROJECT_ROOT / self.config_dir

    @property
    def prompts_path(self) -> Path:
        return PROJECT_ROOT / self.prompts_dir


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Lee un archivo YAML a diccionario; devuelve {} si no existe."""
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def get_config_file() -> Path:
    """Ruta del config.yaml activo."""
    return DEFAULT_CONFIG_FILE


@lru_cache(maxsize=1)
def get_settings() -> AppConfig:
    """AppConfig compartido por la app."""
    return AppConfig()
