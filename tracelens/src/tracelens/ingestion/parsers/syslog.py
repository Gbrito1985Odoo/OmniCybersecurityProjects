"""Parser syslog RFC5424/RFC3164 (Fase 2)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from tracelens.ingestion.parsers.common import Parser
from tracelens.ingestion.parsers.common import raw_to_trace
from tracelens.schemas.common import utcnow
from tracelens.schemas.trace import Trace

# RFC5424: <PRI>VERSION TIMESTAMP HOSTNAME APPNAME[PID]: MSG
_RFC5424_RE = re.compile(
    r"^<\d{1,3}>\d+ \S+ (?P<rest>.*)$",
    re.DOTALL,
)
# RFC3164: <PRI>MMM dd HH:MM:SS HOSTNAME MSG
_RFC3164_RE = re.compile(
    r"^<\d{1,3}>(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<rest>.*)$",
    re.DOTALL,
)


def _rfc3164_ts(month: str, day: str, time_str: str) -> datetime:
    """Convierte la marca RFC3164 (mes/día/hora, sin año) en datetime."""
    try:
        dt = datetime.strptime(f"{month} {int(day):02d} {time_str}", "%b %d %H:%M:%S")
    except ValueError:
        return datetime.now(timezone.utc)
    return dt.replace(tzinfo=timezone.utc)


class SyslogParser(Parser):
    """Trazas syslog RFC5424/RFC3164."""

    name = "syslog"

    def parse(self, text: str) -> list[Trace]:
        traces: list[Trace] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            m = _RFC5424_RE.match(line)
            if m is not None:
                rest = m.group("rest")
                ts = _iso_ts(rest.split(" ", 1)[0]) or utcnow()
            else:
                m = _RFC3164_RE.match(line)
                if m is None:
                    continue
                rest = m.group("rest")
                ts = _rfc3164_ts(m.group("month"), m.group("day"), m.group("time"))
            parts = rest.split(" ", 1)
            service = parts[0]
            message = parts[1] if len(parts) > 1 else ""
            traces.append(
                raw_to_trace(
                    {
                        "timestamp": ts,
                        "service": service,
                        "message": message,
                        "source": "syslog",
                    },
                    source="syslog",
                )
            )
        return traces


def _iso_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
