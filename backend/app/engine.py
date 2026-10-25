"""Deterministic call engine (state machine).

The server decides when a stage advances (turn counts, decisions, hang up).
The model only phrases the caller's line for the current stage. Decision
outcomes are scored from the JSON, never from the model.

Stateless: CallState is owned by the client and echoed each request. This
module is a pure function of (state, input) -> (state, output).
"""

import random
from typing import Optional, Tuple

from .schemas import (
    CallState,
    CallStartResponse,
    CallTurnResponse,
    Decision,
    DecisionResponse,
    Scenario,
    Stage,
    TranscriptEntry,
)


def start_call(scenario: Scenario, language: str) -> Tuple[CallState, CallStartResponse]:
    """Initialize a new call. Returns (state, response) with the first caller
    line to be filled in by the router (which calls the LLM)."""
    state = CallState(
        scenario_id=scenario.id,
        language=language,
        current_stage_id=scenario.stages[0].id,
        stage_turns=0,
        total_turns=0,
    )
    first_stage = scenario.stages[0]
    response = CallStartResponse(
        caller_line="",  # filled by router after LLM call
        tactics=first_stage.tactics,
        stage=first_stage.id,
        stage_turns=0,
        decision_card=None,
        call_ended=False,
    )
    return state, response


def advance_stage(
    state: CallState, scenario: Scenario
) -> Tuple[CallState, Optional[Stage]]:
    """Move to the next stage if one exists. Returns (state, next_stage or
    None if call is over)."""
    stages = scenario.stages
    current_idx = None
    for i, s in enumerate(stages):
        if s.id == state.current_stage_id:
            current_idx = i
            break
    if current_idx is None:
        state.call_ended = True
        return state, None
    if current_idx + 1 >= len(stages):
        state.call_ended = True
        return state, None
    next_stage = stages[current_idx + 1]
    state.current_stage_id = next_stage.id
    state.stage_turns = 0
    return state, next_stage


def decision_due(scenario: Scenario, state: CallState) -> Optional[Decision]:
    """Return the decision that fires after the current stage, if any."""
    if not state.current_stage_id:
        return None
    return scenario.decision_after_stage(state.current_stage_id)


def apply_decision(
    state: CallState, scenario: Scenario, decision_id: str, option_id: str
) -> DecisionResponse:
    """Score a decision from the JSON (never the model). Update weak_spot_map
    and state. Advance stage if the decision has a following stage."""
    decision = None
    for d in scenario.decisions:
        if d.id == decision_id:
            decision = d
            break
    if decision is None:
        raise ValueError(f"Unknown decision id: {decision_id}")

    option = None
    for o in decision.options:
        if o.id == option_id:
            option = o
            break
    if option is None:
        raise ValueError(f"Unknown option id: {option_id} for decision {decision_id}")

    # Record decision
    state.decisions_taken.append(
        {
            "decision_id": decision_id,
            "option_id": option_id,
            "outcome": option.outcome,
            "tactic": option.tactic,
        }
    )

    # Weak-spot map: unsafe marks tactic as "worked on you", safe as "resisted"
    if option.outcome == "unsafe":
        state.weak_spot_map[option.tactic] = "worked"
    else:
        state.weak_spot_map[option.tactic] = "resisted"

    # Advance stage after this decision's stage
    state, _ = advance_stage(state, scenario)

    return DecisionResponse(
        decision_id=decision_id,
        option_id=option_id,
        outcome=option.outcome,
        tactic=option.tactic,
        feedback=option.feedback,
        weak_spot_map=dict(state.weak_spot_map),
        state=state,
    )


def hang_up(state: CallState) -> CallState:
    """End the call immediately. The debrief covers what happened so far."""
    state.hang_up = True
    state.call_ended = True
    return state


def build_decision_card(decision: Decision) -> dict:
    return {
        "id": decision.id,
        "prompt": decision.prompt,
        "options": [
            {"id": o.id, "text": o.text} for o in decision.options
        ],
    }


def add_transcript_entry(
    state: CallState, role: str, content: str, tactics: Optional[list[str]] = None
) -> None:
    state.transcript.append(
        TranscriptEntry(role=role, content=content, tactics=tactics)
    )
    if role == "caller":
        state.stage_turns += 1
        state.total_turns += 1