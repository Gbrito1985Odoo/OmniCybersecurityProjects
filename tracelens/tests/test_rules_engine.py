"""Tests del motor de reglas (Fase 3.1a) — TDD RED: fallan antes de la implementación.

Motor: allow/deny por campos, combinación AND/OR, dry-run contra trazas históricas.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tracelens.rules.engine import RuleEngine
from tracelens.schemas.rule import Rule, RuleMatch
from tracelens.schemas.trace import Trace, TraceStatus

TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def trace(service: str = "web", msg: str = "hello", severity: str = "info",
          source: str = "ingest", **meta) -> Trace:
    return Trace(service=service, message=msg, severity=TraceStatus(severity),
                 source=source, timestamp=TS, metadata=meta)


@pytest.fixture()
def engine() -> RuleEngine:
    return RuleEngine()


class TestWhiteBlackLists:
    def test_allow_unconditional(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="w", white_list=True))
        assert engine.evaluate(trace(service="api")) is True

    def test_deny_unconditional(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="b", black_list=True))
        assert engine.evaluate(trace(service="api")) is False

    def test_white_list_wins_by_priority(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="deny", black_list=True))
        engine.add_rule(Rule(name="allow", white_list=True, priority=1))
        assert engine.evaluate(trace(service="api")) is True

    def test_black_list_wins_by_priority(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="allow", white_list=True))
        engine.add_rule(Rule(name="deny", black_list=True, priority=1))
        assert engine.evaluate(trace(service="api")) is False

    def test_no_rules_allow(self, engine: RuleEngine) -> None:
        assert engine.evaluate(trace()) is True


class TestFieldMatching:
    def test_exact(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True,
                             matches=[RuleMatch(field="service", operator="equals", value="db")]))
        assert engine.evaluate(trace(service="db")) is False
        assert engine.evaluate(trace(service="web")) is True

    def test_contains(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True,
                             matches=[RuleMatch(field="message", operator="contains", value="timeout")]))
        assert engine.evaluate(trace(msg="request timeout")) is False
        assert engine.evaluate(trace(msg="ok")) is True

    def test_regex(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True,
                             matches=[RuleMatch(field="message", operator="regex", value=r"502")]))
        assert engine.evaluate(trace(msg="GET / http 502")) is False

    def test_severity_gte(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True,
                             matches=[RuleMatch(field="severity", operator="gte", value="error")]))
        assert engine.evaluate(trace(severity="critical")) is False
        assert engine.evaluate(trace(severity="info")) is True

    def test_custom_metadata_field(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True,
                             matches=[RuleMatch(field="host", operator="equals", value="evil")]))
        assert engine.evaluate(trace(host="evil")) is False

    def test_multi_match_AND(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True, matches=[
            RuleMatch(field="service", operator="equals", value="web"),
            RuleMatch(field="severity", operator="gte", value="error"),
        ]))
        assert engine.evaluate(trace(service="web", severity="error")) is False
        assert engine.evaluate(trace(service="web", severity="info")) is True


class TestLogic:
    def test_or_group(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True, any_of_groups=[
            [RuleMatch(field="service", operator="equals", value="a")],
            [RuleMatch(field="service", operator="equals", value="b")],
        ]))
        assert engine.evaluate(trace(service="a")) is False
        assert engine.evaluate(trace(service="b")) is False
        assert engine.evaluate(trace(service="c")) is True

    def test_multiple_rules_priority(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="base", black_list=True, priority=0,
                             matches=[RuleMatch(field="service", operator="equals", value="x")]))
        engine.add_rule(Rule(name="ex", white_list=True, priority=10,
                             matches=[RuleMatch(field="service", operator="equals", value="x")]))
        assert engine.evaluate(trace(service="x")) is True
        assert engine.evaluate(trace(service="y")) is True


class TestCRUD:
    def test_add_delete_rules(self, engine: RuleEngine) -> None:
        rule = Rule(name="r")
        engine.add_rule(rule)
        assert len(engine.rules) == 1
        assert engine.delete_rule(rule.name) is True
        assert engine.delete_rule("missing") is False

    def test_disabled_rule_ignored(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="r", black_list=True, enabled=False))
        assert engine.evaluate(trace()) is True

    def test_evaluate_many(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="no-a", black_list=True,
                             matches=[RuleMatch(field="service", operator="equals", value="a")]))
        out = engine.evaluate_many([trace(service="a"), trace(service="b")])
        assert [t.service for t in out] == ["b"]

    def test_evaluate_many_unconditional_black(self, engine: RuleEngine) -> None:
        engine.add_rule(Rule(name="b", black_list=True))
        assert engine.evaluate_many([trace(service="a"), trace(service="b")]) == []
