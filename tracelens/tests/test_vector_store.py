"""Tests de ChromaVectorStore (Fase 1)."""

from __future__ import annotations

import hashlib

import pytest

from tracelens.storage.vector_store import ChromaVectorStore, VectorStore


def hash_embed(text: str, dim: int = 8) -> list[float]:
    """Embeddador hash simple para tests (Fase 4: embeddings reales)."""
    vec = []
    for i in range(dim):
        h = hashlib.sha256(f"{text}:{i}".encode()).hexdigest()
        vec.append(int(h[:8], 16) / 0xFFFFFFFF * 2 - 1)
    return vec


@pytest.fixture()
async def vs(tmp_path):
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"), embed_fn=lambda t: hash_embed(t)
    )
    await store.initialize()
    return store


def test_implements_interface(vs: ChromaVectorStore) -> None:
    assert isinstance(vs, VectorStore)


def test_add_and_search(vs: ChromaVectorStore) -> None:
    ids = vs.add_texts(["hello world", "another thing"], [{"n": 1}, {"n": 2}])
    assert len(ids) == 2
    matches = vs.similarity_search("hello world", k=1)
    assert matches
    assert matches[0].text == "hello world"


def test_get_by_ids_and_count(vs: ChromaVectorStore) -> None:
    ids = vs.add_texts(["a", "b"])
    assert vs.count() == 2
    got = vs.get_by_ids(ids[:1])
    assert [m.id for m in got] == [ids[0]]


def test_search_empty(vs: ChromaVectorStore) -> None:
    assert vs.similarity_search("a") == []
    assert vs.count() == 0


async def test_delete(vs: ChromaVectorStore) -> None:
    ids = vs.add_texts(["a"])
    await vs.delete(ids)
    assert vs.count() == 0


def test_where_filter(vs: ChromaVectorStore) -> None:
    vs.add_texts(["a"], [{"source": "syslog"}])
    vs.add_texts(["b"], [{"source": "json"}])
    matches = vs.similarity_search("a", k=10, where={"source": "syslog"})
    assert len(matches) == 1
    assert matches[0].text == "a"
