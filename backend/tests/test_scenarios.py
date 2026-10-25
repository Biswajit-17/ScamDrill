"""Unit tests: scenario schema validation (pydantic on startup)."""

import json
import pytest

from backend.app.schemas import Scenario, Stage, Decision, Option, TACTIC_IDS

FIXTURE_DIR = "backend/scenarios"


def _load(name):
    with open(f"{FIXTURE_DIR}/{name}") as f:
        return json.load(f)


def test_bank_call_loads_and_validates():
    data = _load("bank_call.json")
    scenario = Scenario(**data)
    assert scenario.id == "bank_call"
    assert scenario.title == "The bank security call"
    assert [s.id for s in scenario.stages] == ["hook", "trust", "pressure", "credential", "payment"]
    assert [d.id for d in scenario.decisions] == ["d1", "d2", "d3"]
    # persona is fictional
    assert scenario.persona.name == "Daniel Reyes"
    assert scenario.persona.org == "Northgate Bank (fictional)"


def test_parcel_fee_loads_and_validates():
    data = _load("parcel_fee.json")
    scenario = Scenario(**data)
    assert scenario.id == "parcel_fee"
    assert [s.id for s in scenario.stages] == ["hook", "trust", "pressure", "credential", "payment"]
    assert [d.id for d in scenario.decisions] == ["d1", "d2", "d3"]


def test_all_tactics_are_from_fixed_list():
    data = _load("bank_call.json")
    scenario = Scenario(**data)
    used = set()
    for s in scenario.stages:
        used.update(s.tactics)
    for d in scenario.decisions:
        for o in d.options:
            used.add(o.tactic)
    assert used <= TACTIC_IDS, f"Tactics outside fixed list: {used - TACTIC_IDS}"


def test_unknown_tactic_rejected():
    with pytest.raises(Exception):
        Stage(
            id="bad",
            goal="x",
            tactics=["not_a_real_tactic"],
            fallback_lines=["hi"],
        )


def test_duplicate_stage_ids_rejected():
    with pytest.raises(Exception):
        Scenario(
            id="dup",
            title="Dup",
            persona={"name": "X", "org": "Y (fictional)", "role": "r"},
            stages=[
                Stage(id="a", goal="g", tactics=["authority"], fallback_lines=["x"]),
                Stage(id="a", goal="g2", tactics=["urgency"], fallback_lines=["y"]),
            ],
            decisions=[],
        )


def test_decision_after_stage_must_exist():
    with pytest.raises(Exception):
        Scenario(
            id="badref",
            title="BadRef",
            persona={"name": "X", "org": "Y (fictional)", "role": "r"},
            stages=[Stage(id="s1", goal="g", tactics=["authority"], fallback_lines=["x"])],
            decisions=[
                Decision(
                    id="d1",
                    after_stage="nonexistent",
                    prompt="p",
                    options=[
                        Option(id="a", text="t", outcome="safe", tactic="authority", feedback="f")
                    ],
                )
            ],
        )


def test_decision_option_outcome_values():
    data = _load("bank_call.json")
    scenario = Scenario(**data)
    for d in scenario.decisions:
        outcomes = {o.outcome for o in d.options}
        assert outcomes <= {"safe", "unsafe"}


def test_tactic_ids_fixed_list_expected():
    expected = {
        "authority", "urgency", "fear", "isolation", "trust_building",
        "verification_blocking", "credential_request", "remote_access", "payment_request",
    }
    assert TACTIC_IDS == expected