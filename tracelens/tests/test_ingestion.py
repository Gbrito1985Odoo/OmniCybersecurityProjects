"""Tests de ingesta (Fase 2): FileIngestor con checkpoint y reanudación."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tracelens.ingestion import FileIngestor, JsonParser


def make_jsonl(tmp_path: Path, lines: int) -> str:
    p = tmp_path / "traces.jsonl"
    p.write_text(
        "\n".join(json.dumps({"service": "svc", "message": f"m{i}"}) for i in range(lines)) + "\n",
        encoding="utf-8",
    )
    return str(p)


class _CountingStore:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def save(self, trace):
        self.calls.append(trace.message)


@pytest.fixture()
def store() -> _CountingStore:
    return _CountingStore()


async def test_load_file_all_lines(store: _CountingStore, tmp_path: Path) -> None:
    path = make_jsonl(tmp_path, 5)
    ing = FileIngestor(store, JsonParser())
    stored = await ing.load(path)
    assert stored == 5
    assert store.calls == ["m0", "m1", "m2", "m3", "m4"]


def _jsonl_prefix_bytes(path: str, lines: int) -> int:
    """Bytes de `lines` líneas del archivo (offset de checkpoint)."""
    text = Path(path).read_text(encoding="utf-8")
    return len("\n".join(text.splitlines()[:lines]) + "\n")


async def test_load_file_resume_from_checkpoint(store: _CountingStore, tmp_path: Path) -> None:
    path = make_jsonl(tmp_path, 5)
    checkpoint = tmp_path / "cp.json"
    checkpoint.write_text(json.dumps({path: _jsonl_prefix_bytes(path, 2)}), encoding="utf-8")
    ing = FileIngestor(store, JsonParser(), checkpoint_file=str(checkpoint))
    stored = await ing.load(path)
    assert stored == 3
    assert store.calls == ["m2", "m3", "m4"]


async def test_load_missing_file(store: _CountingStore, tmp_path: Path) -> None:
    ing = FileIngestor(store, JsonParser())
    assert await ing.load(str(tmp_path / "nope.jsonl")) == 0
    assert store.calls == []


async def test_checkpoint_saved(tmp_path: Path) -> None:
    path = make_jsonl(tmp_path, 2)
    checkpoint = tmp_path / "cp.json"

    class _S:
        async def save(self, trace):
            pass

    ing = FileIngestor(_S(), JsonParser(), checkpoint_file=str(checkpoint))
    await ing.load(path)
    data = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert data == {path: Path(path).stat().st_size}
