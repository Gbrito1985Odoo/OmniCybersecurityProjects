"""Carga de ficheros/directorios con checkpoint de offsets (Fase 2)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Optional

import aiofiles

from tracelens.ingestion.parsers import Parser
from tracelens.storage.trace_store import TraceStore

ProgressFn = Callable[[int, int], None]


class FileIngestor:
    """Carga trazas de un fichero o directorio con checkpoint y reanudación."""

    def __init__(
        self,
        trace_store: TraceStore,
        parser: Parser,
        checkpoint_file: Optional[str] = None,
        chunk_size: int = 64 * 1024,
    ) -> None:
        self._trace_store = trace_store
        self._parser = parser
        self._checkpoint_file = checkpoint_file
        self._chunk_size = chunk_size

    # -- checkpoint ------------------------------------------------------
    def _load_checkpoint(self) -> dict[str, int]:
        if not self._checkpoint_file:
            return {}
        p = Path(self._checkpoint_file)
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return {str(k): int(v) for k, v in data.items()}
            except (OSError, ValueError, TypeError):
                return {}
        return {}

    def _save_checkpoint(self, offsets: dict[str, int]) -> None:
        if not self._checkpoint_file:
            return
        p = Path(self._checkpoint_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(offsets, ensure_ascii=False), encoding="utf-8")

    # -- ingesta ---------------------------------------------------------
    async def load(self, path: str, progress: Optional[ProgressFn] = None) -> int:
        """Carga un fichero o directorio; devuelve trazas guardadas."""
        p = Path(path)
        if p.is_file():
            return await self._load_file(str(p), progress)
        if not p.is_dir():
            return 0
        total = 0
        for f in sorted(p.rglob("*")):
            if f.is_file():
                total += await self._load_file(str(f), progress)
        return total

    async def _load_file(self, path: str, progress: Optional[ProgressFn] = None) -> int:
        offsets = self._load_checkpoint()
        offset = offsets.get(path, 0)
        size = os.path.getsize(path)
        if progress:
            progress(offset, size)
        stored = 0
        fh = await aiofiles.open(path, "rb")
        try:
            await fh.seek(offset)
            while True:
                chunk = await fh.read(self._chunk_size)
                if not chunk:
                    break
                offset += len(chunk)
                text = chunk.decode("utf-8", errors="replace")
                for trace in self._parser.parse(text):
                    await self._trace_store.save(trace)
                    stored += 1
                if progress:
                    progress(offset, size)
        finally:
            await fh.close()
        offsets[path] = offset
        self._save_checkpoint(offsets)
        return stored
