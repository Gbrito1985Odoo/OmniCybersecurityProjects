"""Parser regex personalizable (Fase 2)."""

from __future__ import annotations

import re
from typing import Optional

from tracelens.ingestion.parsers.common import Parser
from tracelens.ingestion.parsers.common import raw_to_trace
from tracelens.schemas.trace import Trace


class RegexParser(Parser):
    """Parser personalizable: regex con grupos nombrados -> campos Trace.

    Ejemplo:
        RegexParser(
            r"^\\[(?P<ts>\\S+)\\] (?P<host>\\S+): (?P<msg>.*)$",
            field_map={"ts": "timestamp", "host": "service", "msg": "message"},
        )
    """

    name = "regex"

    def __init__(
        self,
        pattern: str,
        field_map: Optional[dict[str, str]] = None,
        source: str = "regex",
    ) -> None:
        self.regex = re.compile(pattern)
        self.field_map = field_map or {}
        self.source = source

    def parse(self, text: str) -> list[Trace]:
        traces = []
        for line in text.splitlines():
            if not line.strip():
                continue
            m = self.regex.match(line)
            if not m:
                continue
            raw = {
                self.field_map.get(name, name): value
                for name, value in m.groupdict().items()
                if value is not None
            }
            traces.append(raw_to_trace(raw, source=self.source))
        return traces
