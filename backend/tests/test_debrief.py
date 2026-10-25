"""Unit tests: debrief static fallback and response shape."""

import json

from backend.app.schemas import Scenario, CallState
from backend.app.debrief import _static_debrief, generate_debrief_with_fallback


def _scenario():
    with open("backend/scenarios/bank_call.json") as f:
        return Scenario(**json.load(f))


def _state_with_decisions():
    s = _scenario()
    state = CallState(scenario_id="bank_call", language="en")
    state.decisions_taken = [
        {"decision_id": "d1", "option_id": "a", "outcome": "unsafe", "tactic": "authority"},
        {"decision_id": "d2", "option_id": "b", "outcome": "safe", "tactic": "isolation"},
    ]
    state.weak_spot_map = {"authority": "worked", "isolation": "resisted"}
    return s, state


def test_static_debrief_renders():
    s, state = _state_with_decisions()
    d = _static_debrief(s, state)
    assert d.summary
    assert len(d.summary) <= 120
    assert len(d.moments) == 2
    assert d.moments[0].decision_id == "d1"
    assert d.moments[1].decision_id == "d2"
    assert len(d.rules) == 3
    for rule in d.rules:
        assert len(rule) > 0


def test_static_debrief_no_decisions():
    s = _scenario()
    state = CallState(scenario_id="bank_call", language="en")
    d = _static_debrief(s, state)
    assert d.moments
    assert d.rules


def test_generate_debrief_with_fallback_uses_static_on_error():
    # Without API keys, generate_debrief will raise -> fallback to static.
    s, state = _state_with_decisions()
    resp = generate_debrief_with_fallback(s, state, language="en")
    assert resp.summary
    assert resp.fallback_used is True  # no API key configured
    assert resp.weak_spot_map == {"authority": "worked", "isolation": "resisted"}
    assert len(resp.moments) == 2
    assert len(resp.rules) == 3