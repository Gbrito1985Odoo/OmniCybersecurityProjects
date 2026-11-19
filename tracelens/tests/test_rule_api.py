"""Tests de la API de reglas (Fase 3.1a) — CRUD via API (RED antes de implementación)."""

from __future__ import annotations

import pytest

from tracelens.rules.engine import RuleEngine
from tracelens.rules.api import RulesApi
from tracelens.schemas.rule import Rule


@pytest.fixture()
def api() -> RulesApi:
    return RulesApi(RuleEngine())


def test_create_get_delete() -> None:
    api = RulesApi(RuleEngine())
    rule = api.create_rule(Rule(name="r", black_list=True))
    assert rule.id is not None
    got = api.get_rule(rule.id)
    assert got is not None and got.name == "r"
    assert api.delete_rule(rule.id) is True
    assert api.get_rule(rule.id) is None


def test_get_missing(api: RulesApi) -> None:
    assert api.get_rule(999) is None


def test_list_rules() -> None:
    api = RulesApi(RuleEngine())
    api.create_rule(Rule(name="a"))
    api.create_rule(Rule(name="b"))
    assert len(api.list_rules()) == 2


def test_hot_reload_on_modify() -> None:
    api = RulesApi(RuleEngine())
    rule = api.create_rule(Rule(name="r", black_list=True))
    rule.enabled = False
    api.update_rule(rule)
    assert api.get_rule(rule.id).enabled is False
    assert api.engine.evaluate(api._sample()) is True
