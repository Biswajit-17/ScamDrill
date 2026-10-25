"""Unit tests: engine state transitions, decision scoring, hang up."""

import json
import pytest

from backend.app.schemas import Scenario, CallState
from backend.app import engine as eng


def _scenario():
    with open("backend/scenarios/bank_call.json") as f:
        return Scenario(**json.load(f))


def test_start_call_sets_first_stage():
    s = _scenario()
    state, resp = eng.start_call(s, "en")
    assert state.scenario_id == "bank_call"
    assert state.current_stage_id == "hook"
    assert state.stage_turns == 0
    assert state.call_ended is False
    assert resp.stage == "hook"


def test_decision_scoring_unsafe_marks_worked():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    resp = eng.apply_decision(state, s, "d1", "a")  # unsafe, authority
    assert resp.outcome == "unsafe"
    assert resp.tactic == "authority"
    assert state.weak_spot_map.get("authority") == "worked"


def test_decision_scoring_safe_marks_resisted():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    resp = eng.apply_decision(state, s, "d1", "b")  # safe, authority
    assert resp.outcome == "safe"
    assert state.weak_spot_map.get("authority") == "resisted"


def test_decision_records_in_decisions_taken():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    eng.apply_decision(state, s, "d1", "b")
    assert len(state.decisions_taken) == 1
    assert state.decisions_taken[0]["decision_id"] == "d1"
    assert state.decisions_taken[0]["option_id"] == "b"
    assert state.decisions_taken[0]["outcome"] == "safe"


def test_unknown_decision_rejected():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    with pytest.raises(Exception):
        eng.apply_decision(state, s, "nope", "a")


def test_unknown_option_rejected():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    with pytest.raises(Exception):
        eng.apply_decision(state, s, "d1", "z")


def test_hang_up_ends_call():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    state = eng.hang_up(state)
    assert state.hang_up is True
    assert state.call_ended is True


def test_advance_stage_moves_to_next():
    s = _scenario()
    state, _ = eng.start_call(s, "en")  # hook
    state, nxt = eng.advance_stage(state, s)
    assert nxt is not None
    assert nxt.id == "trust"
    assert state.current_stage_id == "trust"
    assert state.stage_turns == 0


def test_advance_past_last_stage_ends_call():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    # walk through all stages
    stages = [st.id for st in s.stages]
    for _ in range(len(stages)):
        state, nxt = eng.advance_stage(state, s)
    assert state.call_ended is True


def test_decision_due_returns_correct_decision():
    s = _scenario()
    state, _ = eng.start_call(s, "en")  # stage = hook
    d = eng.decision_due(s, state)
    assert d is not None
    assert d.id == "d1"  # d1.after_stage == "hook"


def test_decision_card_shape():
    s = _scenario()
    state, _ = eng.start_call(s, "en")
    d = eng.decision_due(s, state)
    card = eng.build_decision_card(d)
    assert card["id"] == "d1"
    assert "prompt" in card
    assert len(card["options"]) == 3
    for o in card["options"]:
        assert "id" in o and "text" in o