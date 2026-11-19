"""Parser CSV (Fase 2): cabecera + columnas mapeadas a campos Trace."""

from __future__ import annotations

import csv
import io
from typing import Optional

from tracelens.ingestion.parsers.common import Parser
from tracelens.ingestion.parsers.common import raw_to_trace
from tracelens.schemas.trace import Trace


class CsvParser(Parser):
    """Trazas desde CSV: primer fichero con cabecera y columnas mapeadas."""

    name = "csv"

    DEFAULT_HEADER_MAP: dict[str, str] = {"host": "service", "ts": "timestamp", "msg": "message"}

    def __init__(self, header_map: Optional[dict[str, str]] = None) -> None:
        merged = dict(self.DEFAULT_HEADER_MAP)
        if header_map:
            merged.update(header_map)
        self.header_map = merged

    def parse(self, text: str) -> list[Trace]:
        traces: list[Trace] = []
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if not lines:
            return traces
        reader = csv.DictReader(io.StringIO("\n".join(lines)))
        for row in reader:
            raw = {
                self.header_map.get(k, k): v for k, v in row.items() if v is not None
            }
            traces.append(raw_to_trace(raw, source="csv"))
        return traces
