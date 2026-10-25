"""FastAPI routes for ScamDrill.

Endpoints:
  GET    /api/scenarios
  POST   /api/call/start
  POST   /api/call/turn
  POST   /api/call/decision
  POST   /api/debrief
  GET    /healthz

Stateless: the client holds CallState and echoes it each request.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from .schemas import (
    CallState,
    CallStartRequest,
    CallStartResponse,
    CallTurnRequest,
    CallTurnResponse,
    DecisionRequest,
    DecisionResponse,
    DebriefRequest,
    DebriefResponse,
    Scenario,
    ScenarioSummary,
    Stage,
)
from . import engine as eng
from . import guardrails as gr
from . import debrief as deb
from .llm import generate_caller_line

router = APIRouter()

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"

# ---------------------------------------------------------------------------
# Scenario registry (loaded + validated on startup)
# ---------------------------------------------------------------------------

_scenarios: Dict[str, Scenario] = {}


def load_scenarios() -> Dict[str, Scenario]:
    scenarios: Dict[str, Scenario] = {}
    if not SCENARIOS_DIR.exists():
        return scenarios
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            scenario = Scenario(**data)
            scenarios[scenario.id] = scenario
        except Exception as exc:  # pragma: no cover - startup validation
            print(f"[scamdrill] failed to load scenario {path}: {exc}")
    return scenarios


def get_scenarios() -> Dict[str, Scenario]:
    if not _scenarios:
        _scenarios.update(load_scenarios())
    return _scenarios


# ---------------------------------------------------------------------------
# Cost protection: per-IP rate limit + global daily cap
# ---------------------------------------------------------------------------

_ip_calls: Dict[str, List[float]] = {}
_daily_calls = 0
_daily_reset_day = time.strftime("%Y%m%d")


def _rate_limit_ok(request: Request) -> bool:
    """Per-IP rough rate limit (max 60 calls/minute) + DAILY_CALL_CAP."""
    global _daily_calls, _daily_reset_day
    now = time.time()
    day = time.strftime("%Y%m%d")
    if day != _daily_reset_day:
        _daily_reset_day = day
        _daily_calls = 0

    cap = int(os.getenv("DAILY_CALL_CAP", "1000000"))
    if _daily_calls >= cap:
        return False

    client_ip = request.client.host if request.client else "unknown"
    window = _ip_calls.setdefault(client_ip, [])
    window[:] = [t for t in window if now - t < 60.0]
    if len(window) >= 60:
        return False
    window.append(now)
    _daily_calls += 1
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_caller_system_prompt(scenario: Scenario, stage: Stage, language: str) -> str:
    persona = scenario.persona
    tactics_str = ", ".join(stage.tactics)
    return (
        "You are playing a fictional scam caller in a training simulation that teaches "
        "people to recognise scams.\n"
        f"Persona: {persona.name}, {persona.role} at {persona.org}. Everything is fictional.\n"
        f"Current stage goal: {stage.goal}\n"
        f"Use only these pressure tactics in this stage: {tactics_str}\n"
        f"Rules: reply in {language}. 1 to 3 short sentences. Stay in character.\n"
        "Never include real company names, real phone numbers, real URLs or email addresses.\n"
        "Never give real instructions for committing fraud.\n"
        'Reply with ONLY the words the caller says out loud: plain text, no JSON, no quotation marks, no stage directions.'
    )


def _build_caller_user_prompt(state: CallState, stage: Stage, user_message: str) -> str:
    transcript_lines = []
    for e in state.transcript[-8:]:
        tag = "Caller" if e.role == "caller" else "User"
        transcript_lines.append(f"{tag}: {e.content}")
    transcript_str = "\n".join(transcript_lines) if transcript_lines else "(start of call)"
    return (
        f"Conversation so far:\n{transcript_str}\n\n"
        f"User just said: {user_message}\n"
        f"Reply as the caller for the current stage ({stage.id})."
    )


def _apply_output_filter(
    line_text: str, tactics: list[str], fallback_lines: list[str]
) -> tuple[str, list[str], bool]:
    """Run output filter. Returns (text, tactics, fallback_used)."""
    if gr.output_safe(line_text):
        return line_text, tactics, False
    import random
    fallback = random.choice(fallback_lines) if fallback_lines else (
        "I'm sorry, I didn't catch that. Could you repeat?"
    )
    return fallback, [], True


def _decision_pending(scenario: Scenario, state: CallState):
    """Return the decision due after the current stage if not yet taken."""
    if not state.current_stage_id:
        return None
    taken_ids = {d.get("decision_id") for d in state.decisions_taken}
    stage = scenario.stage_by_id(state.current_stage_id)
    if stage is None or state.stage_turns < stage.min_turns:
        return None
    decision = scenario.decision_after_stage(state.current_stage_id)
    if decision and decision.id not in taken_ids:
        return decision
    return None


def _require_rate_limit(request: Request):
    if not _rate_limit_ok(request):
        raise HTTPException(
            status_code=503,
            detail="Demo is at capacity. Please try again later.",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/scenarios", response_model=List[ScenarioSummary])
def list_scenarios():
    scenarios = get_scenarios()
    return [ScenarioSummary(id=s.id, title=s.title) for s in scenarios.values()]


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.post("/api/call/start", response_model=CallStartResponse)
def call_start(req: CallStartRequest, request: Request):
    _require_rate_limit(request)
    scenarios = get_scenarios()
    scenario = scenarios.get(req.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown scenario")

    state, _ = eng.start_call(scenario, req.language)
    stage = scenario.stage_by_id(state.current_stage_id)
    if stage is None:
        raise HTTPException(status_code=500, detail="No stages in scenario")

    system_prompt = _build_caller_system_prompt(scenario, stage, req.language)
    user_prompt = _build_caller_user_prompt(state, stage, "")

    line, fb_used = generate_caller_line(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        stage_tactics=stage.tactics,
        fallback_lines=stage.fallback_lines,
        temperature=0.7,
        max_tokens=1000,
    )
    state.fallback_used = fb_used

    message, tactics, fb2 = _apply_output_filter(
        line.message.strip(), line.tactics, stage.fallback_lines
    )
    if fb2:
        state.fallback_used = True

    eng.add_transcript_entry(state, "caller", message, tactics)

    decision = _decision_pending(scenario, state)
    decision_card = None
    if decision:
        decision_card = eng.build_decision_card(decision)

    return CallStartResponse(
        caller_line=message,
        tactics=tactics,
        stage=stage.id,
        stage_turns=state.stage_turns,
        decision_card=decision_card,
        call_ended=state.call_ended,
    )


@router.post("/api/call/turn", response_model=CallTurnResponse)
def call_turn(req: CallTurnRequest, request: Request):
    _require_rate_limit(request)
    scenarios = get_scenarios()
    scenario = scenarios.get(req.state.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown scenario")

    state = req.state

    if state.hang_up or state.call_ended:
        return CallTurnResponse(
            caller_line="",
            tactics=[],
            stage=state.current_stage_id or "",
            stage_turns=state.stage_turns,
            decision_card=None,
            call_ended=True,
        )

    pending = _decision_pending(scenario, state)
    if pending:
        return CallTurnResponse(
            caller_line="",
            tactics=[],
            stage=state.current_stage_id,
            stage_turns=state.stage_turns,
            decision_card=eng.build_decision_card(pending),
            call_ended=False,
        )

    masked_message, masked = gr.mask_input(req.user_message)
    gr.fraud_instruction(masked_message)
    eng.add_transcript_entry(state, "user", masked_message)

    stage = scenario.stage_by_id(state.current_stage_id)
    if stage is None:
        state.call_ended = True
        return CallTurnResponse(
            caller_line="",
            tactics=[],
            stage=state.current_stage_id or "",
            stage_turns=state.stage_turns,
            decision_card=None,
            call_ended=True,
        )

    if state.stage_turns >= stage.max_turns:
        state, next_stage = eng.advance_stage(state, scenario)
        if next_stage is None:
            state.call_ended = True
            return CallTurnResponse(
                caller_line="",
                tactics=[],
                stage=state.current_stage_id or "",
                stage_turns=state.stage_turns,
                decision_card=None,
                call_ended=True,
            )
        stage = next_stage

    system_prompt = _build_caller_system_prompt(scenario, stage, state.language)
    user_prompt = _build_caller_user_prompt(state, stage, masked_message)

    line, fb_used = generate_caller_line(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        stage_tactics=stage.tactics,
        fallback_lines=stage.fallback_lines,
        temperature=0.7,
        max_tokens=1000,
    )
    state.fallback_used = state.fallback_used or fb_used

    message, tactics, fb2 = _apply_output_filter(
        line.message.strip(), line.tactics, stage.fallback_lines
    )
    if fb2:
        state.fallback_used = True

    eng.add_transcript_entry(state, "caller", message, tactics)

    decision = _decision_pending(scenario, state)
    decision_card = None
    if decision:
        decision_card = eng.build_decision_card(decision)

    return CallTurnResponse(
        caller_line=message,
        tactics=tactics,
        stage=stage.id,
        stage_turns=state.stage_turns,
        decision_card=decision_card,
        call_ended=state.call_ended,
        masked=masked,
    )


@router.post("/api/call/decision", response_model=DecisionResponse)
def call_decision(req: DecisionRequest, request: Request):
    _require_rate_limit(request)
    scenarios = get_scenarios()
    scenario = scenarios.get(req.state.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown scenario")

    state = req.state
    response = eng.apply_decision(state, scenario, req.decision_id, req.option_id)
    return response


@router.post("/api/debrief", response_model=DebriefResponse)
def call_debrief(req: DebriefRequest, request: Request):
    _require_rate_limit(request)
    scenarios = get_scenarios()
    scenario = scenarios.get(req.state.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown scenario")

    return deb.generate_debrief_with_fallback(
        scenario, req.state, language=req.state.language
    )



