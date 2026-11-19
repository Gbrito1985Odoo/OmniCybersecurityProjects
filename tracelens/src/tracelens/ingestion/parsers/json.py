"""Parser JSON Lines (Fase 2): una traza por línea."""

from __future__ import annotations

import json

from tracelens.ingestion.parsers.common import Parser
from tracelens.ingestion.parsers.common import raw_to_trace
from tracelens.schemas.trace import Trace


class JsonParser(Parser):
    """Trazas en formato JSON lines (una traza por línea)."""

    name = "json"

    def parse(self, text: str) -> list[Trace]:
        traces = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                traces.append(raw_to_trace(data, source="json"))
        return traces
