"""Tests de parsers (Fase 2): json, syslog, csv y regex personalizable."""

from __future__ import annotations

import json

from tracelens.ingestion.parsers import CsvParser, JsonParser, RegexParser, SyslogParser
from tracelens.schemas.trace import TraceStatus


def test_json_parser_lines() -> None:
    p = JsonParser()
    text = "\n".join(
        json.dumps(d) for d in [
            {"service": "web", "message": "req start", "severity": "warning"},
            {"service": "web", "message": "req done"},
        ]
    )
    traces = p.parse(text)
    assert len(traces) == 2
    assert traces[0].service == "web"
    assert traces[0].severity == TraceStatus.warning
    assert traces[1].severity == TraceStatus.info


def test_json_parser_ignores_invalid_lines() -> None:
    p = JsonParser()
    text = 'not json\n{"service": "x", "message": "m"}\n'
    traces = p.parse(text)
    assert len(traces) == 1
    assert traces[0].service == "x"


def test_syslog_rfc3164() -> None:
    p = SyslogParser()
    text = "<34>Oct 11 22:14:15 host systemd[1]: Started journal.service"
    traces = p.parse(text)
    assert len(traces) == 1
    assert traces[0].service == "host"
    assert traces[0].message == "systemd[1]: Started journal.service"
    assert traces[0].source == "syslog"


def test_syslog_rfc5424_with_ts() -> None:
    p = SyslogParser()
    text = "<34>1 2026-01-01T12:00:00.000Z host app[42]: hello world"
    traces = p.parse(text)
    assert len(traces) == 1
    assert traces[0].service == "host"
    assert traces[0].message == "app[42]: hello world"
    assert traces[0].timestamp.tzinfo is not None


def test_syslog_rfc3164_ignores_garbage() -> None:
    p = SyslogParser()
    traces = p.parse("some plain line\n<3>Jan  1 00:00:01 host app: hello")
    assert len(traces) == 1
    assert traces[0].service == "host"


def test_csv_parser() -> None:
    p = CsvParser()
    text = "ts,host,msg\n2026-01-01T00:00:00Z,web-1,started ok\n"
    traces = p.parse(text)
    assert len(traces) == 1
    assert traces[0].service == "web-1"
    assert "started ok" in traces[0].message


def test_regex_parser() -> None:
    p = RegexParser(
        r"^\[(?P<ts>\S+)\] (?P<host>\S+): (?P<msg>.*)$",
        field_map={"ts": "timestamp", "host": "service", "msg": "message"},
    )
    traces = p.parse("[2026-01-01T10:00:00] frontend: 502 from 10.0.0.1")
    assert len(traces) == 1
    assert traces[0].service == "frontend"
    assert traces[0].message.startswith("502 from 10.0.0.1")


def test_regex_parser_no_match() -> None:
    p = RegexParser(r"^x$")
    assert p.parse("no match") == []
