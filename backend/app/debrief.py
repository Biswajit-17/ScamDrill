"""Debrief generation.

Calls the reasoning model (MODEL_REASON) with a JSON blob of the scenario
summary, decisions taken, and tactic outcome map. Validates the response.
On failure, falls back to the static feedback strings in the scenario JSON so
the debrief page always renders.
"""

import json
from typing import List

from .schemas import CallState, Debrief, DebriefResponse, Scenario
from .llm import generate_debrief, get_model_reason


def _build_debrief_input(scenario: Scenario, state: CallState) -> dict:
    """Assemble the JSON-only input for the debrief model. No invented events."""
    moments_input = []
    for d in state.decisions_taken:
        moments_input.append({
            "decision_id": d.get("decision_id"),
            "outcome": d.get("outcome"),
            "tactic": d.get("tactic"),
        })
    return {
        "scenario": {
            "id": scenario.id,
            "title": scenario.title,
            "persona": scenario.persona.model_dump(),
        },
        "language": state.language,
        "decisions": moments_input,
        "weak_spot_map": state.weak_spot_map,
        "hang_up": state.hang_up,
        "call_ended": state.call_ended,
    }


def _static_debrief(scenario: Scenario, state: CallState) -> Debrief:
    """Build a debrief purely from scenario feedback strings (no model)."""
    moments: List[dict] = []
    rules = []
    tactic_to_advice = {
        "authority": "Hang up and call the number on your bank card or statement.",
        "urgency": "Take your time. Real organisations won't rush you.",
        "fear": "Don't act out of fear. Verify through an official channel.",
        "isolation": "You can hang up and speak with someone you trust.",
        "trust_building": "Knowing a few details doesn't prove who someone is.",
        "verification_blocking": "Never let a caller stop you from calling back officially.",
        "credential_request": "Never share a one-time code with anyone.",
        "remote_access": "Never install software a caller asks you to install.",
        "payment_request": "Never send money to a 'safe account' a caller names.",
    }
    for d in state.decisions_taken:
        tactic = d.get("tactic", "")
        outcome = d.get("outcome", "")
        decision_id = d.get("decision_id", "")
        if outcome == "unsafe":
            what = f"On {decision_id}, you chose the unsafe option using the {tactic} tactic."
            say = tactic_to_advice.get(tactic, "Verify through an official channel before acting.")
        else:
            what = f"On {decision_id}, you resisted the {tactic} tactic."
            say = "Good — keep verifying through official channels."
        moments.append({
            "decision_id": decision_id,
            "what_happened": what,
            "say_instead": say,
        })
    if not moments:
        moments.append({
            "decision_id": "none",
            "what_happened": "No decisions were recorded during the call.",
            "say_instead": "If you ever get a real suspicious call, hang up and call the official number.",
        })
    rules = [
        "Hang up and call back using the number on your card or statement.",
        "Never share one-time codes or passwords with anyone who calls you.",
        "Never install software or send money because a caller pressures you to.",
    ]
    summary = f"Debrief for {scenario.title}. You made {len(state.decisions_taken)} decision(s). "
    summary += "Review each moment and what to say instead next time."
    return Debrief(summary=summary, moments=moments, rules=rules)


def generate_debrief_with_fallback(
    scenario: Scenario, state: CallState, language: str = "en"
) -> DebriefResponse:
    """Generate the debrief, with a static fallback so it always renders."""
    system_prompt = (
        "You are a calm coach. Using ONLY the JSON below, write a short debrief in "
        f"{language}. Do not invent events. Do not mention anything not in the data. "
        "Return ONLY JSON: {\"summary\": \"<=60 words\", \"moments\": "
        "[{\"decision_id\": \"...\", \"what_happened\": \"...\", \"say_instead\": \"...\"}], "
        "\"rules\": [\"...\", \"...\", \"...\"]}"
    )
    user_prompt = json.dumps(_build_debrief_input(scenario, state))

    fallback_used = False
    try:
        debrief = generate_debrief(system_prompt, user_prompt, temperature=0.3, max_tokens=600)
    except Exception:
        fallback_used = True
        debrief = _static_debrief(scenario, state)

    return DebriefResponse(
        summary=debrief.summary,
        moments=debrief.moments,
        rules=debrief.rules,
        weak_spot_map=dict(state.weak_spot_map),
        fallback_used=fallback_used,
    )