"""Parsers de trazas (Fase 2): JSON lines, syslog, CSV y regex personalizable.

Contrato: `Parser.parse(text) -> list[Trace]`. Todos los parsers operan sobre
texto (línea o bloque) y devuelven las trazas que contiene.
"""

from tracelens.ingestion.parsers.common import Parser, raw_to_trace, to_severity, to_timestamp
from tracelens.ingestion.parsers.csv import CsvParser
from tracelens.ingestion.parsers.json import JsonParser
from tracelens.ingestion.parsers.passthrough import PassthroughParser
from tracelens.ingestion.parsers.regex import RegexParser
from tracelens.ingestion.parsers.syslog import SyslogParser

__all__ = [
    "CsvParser",
    "JsonParser",
    "Parser",
    "PassthroughParser",
    "RegexParser",
    "SyslogParser",
    "raw_to_trace",
    "to_severity",
    "to_timestamp",
]
