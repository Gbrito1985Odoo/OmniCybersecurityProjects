"""Interfaz VectorStore + implementación ChromaDB (Fase 1).

ChromaDB es el backend del producto. FAISS se considera alternativa:
implementación planteada en Fase 4 (ai/embeddings + ai/vector_client).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

import chromadb

EmbedFn = Callable[[str], Sequence[float]]


@dataclass
class VectorMatch:
    """Resultado de una búsqueda vectorial: texto, metadatos y similitud."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    id: str = ""


class VectorStore(ABC):
    """Interfaz abstracta de store vectorial."""

    @abstractmethod
    async def initialize(self) -> None:
        """Crea el store (idempotente)."""

    @abstractmethod
    def add_texts(
        self, texts: Sequence[str], metadatas: Optional[Sequence[dict]] = None
    ) -> list[str]:
        """Inserta textos; devuelve sus ids."""

    @abstractmethod
    def similarity_search(
        self, query: str, k: int = 10, where: Optional[dict] = None
    ) -> list[VectorMatch]:
        """Busca los k textos más similares a query."""

    @abstractmethod
    def get_by_ids(self, ids: Sequence[str]) -> list[VectorMatch]:
        """Devuelve textos por ids (sin búsqueda)."""

    @abstractmethod
    async def delete(self, ids: Sequence[str]) -> None:
        """Elimina textos por ids."""

    @abstractmethod
    def count(self) -> int:
        """Número de textos almacenados."""


class ChromaVectorStore(VectorStore):
    """Implementación local con ChromaDB persistente (Fase 1)."""

    def __init__(self, persist_dir: str, embed_fn: Optional[EmbedFn] = None) -> None:
        self._persist_dir = persist_dir
        self._embed_fn = embed_fn
        self._collection: Optional[chromadb.Collection] = None

    def _ensure(self) -> None:
        if self._collection is None:
            raise RuntimeError("ChromaVectorStore no está inicializado; llama a initialize()")

    async def initialize(self) -> None:
        """Crea el store (idempotente)."""
        if self._collection is None:
            client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = client.get_or_create_collection(
                name="traces", metadata={"hnsw:space": "cosine"}
            )

    def add_texts(self, texts, metadatas=None):
        """Inserta textos; devuelve sus ids."""
        self._ensure()
        ids = [f"trace-{uuid.uuid4().hex}" for _ in texts]
        kwargs: dict[str, Any] = {"ids": ids, "documents": list(texts)}
        if self._embed_fn is not None:
            kwargs["embeddings"] = [list(self._embed_fn(t)) for t in texts]
        # ChromaDB 1.x rechaza metadatas vacíos: sin `metadatas`, el add()
        # es válido (Fase 1: trazas sin metadatos).
        if metadatas is not None:
            kwargs["metadatas"] = list(metadatas)
        self._collection.add(**kwargs)
        return ids

    def similarity_search(self, query, k=10, where=None):
        """Busca los k textos más similares a query."""
        self._ensure()
        total = self._collection.count()
        if not total:
            return []
        k = min(k, total)
        if self._embed_fn is not None:
            qv = list(self._embed_fn(query))
            result = self._collection.query(query_embeddings=[qv], n_results=k, where=where)
        else:
            result = self._collection.query(query_texts=[query], n_results=k, where=where)
        matches = []
        for rid, doc, meta, dist in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            matches.append(
                VectorMatch(
                    text=doc or "", metadata=meta or {}, score=1.0 - (dist or 0.0), id=rid
                )
            )
        return matches

    def get_by_ids(self, ids):
        """Devuelve textos por ids (sin búsqueda)."""
        self._ensure()
        if not ids:
            return []
        result = self._collection.get(ids=list(ids), include=["documents", "metadatas"])
        return [
            VectorMatch(text=d or "", metadata=m or {}, score=1.0, id=i)
            for i, d, m in zip(result["ids"], result["documents"], result["metadatas"])
        ]

    async def delete(self, ids):
        """Elimina textos por ids."""
        self._ensure()
        if ids:
            self._collection.delete(ids=list(ids))

    def count(self):
        """Número de textos almacenados."""
        self._ensure()
        return self._collection.count()
