"""Fallback: cada línea no vacía se convierte en un mensaje de traza."""

from tracelens.ingestion.parsers.common import Parser
from tracelens.ingestion.parsers.common import raw_to_trace
from tracelens.schemas.trace import Trace


class PassthroughParser(Parser):
    """Fallback: cada línea no vacía se convierte en un mensaje de traza."""

    name = "passthrough"

    def parse(self, text: str) -> list[Trace]:
        return [
            raw_to_trace({"message": ln, "source": "passthrough"})
            for ln in text.splitlines()
            if ln.strip()
        ]
