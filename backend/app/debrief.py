"""Debrief generation.

Calls the model (plain-text, no JSON mode) with a summary of decisions taken
and tactic outcome map. The model replies with simple plain-text pieces:
  - One short say_instead line per unsafe decision
  - Three rules, separated by simple delimiters
Code assembles the JSON response from those pieces. On any failure
(model error, parse error, empty output), the static fallback is used so
the debrief page always renders.
"""

import re
import json
from typing import List

from .schemas import CallState, Debrief, DebriefResponse, Scenario
from .llm import generate_debrief, get_call_log, clear_call_log


def _extract_say_instead(lines: list[str]) -> list[str]:
    """Return non-empty say_ininstead lines from the model output."""
    result: list[str] = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("Rule") and not line.startswith("RULE"):
            result.append(line)
    return result


def _extract_rules(text: str) -> list[str]:
    """Extract exactly 3 rules from model output.

    Rules may be prefixed with "Rule 1", "Rule 2", "Rule 3" or "1.", "2.", "3."
    or separated by newlines/delimiters. We grab the first 3 sentence-like
    segments that look like recommendations.
    """
    rules: list[str] = []
    # Try explicit "Rule N:" or "N." patterns first
    for m in re.finditer(r"(?:Rule|rule)\s*[123]:\\s*(.+)$", text, re.IGNORECASE | re.MULTILINE):
        val = m.group(1).strip()
        if val and val not in rules:
            rules.append(val)
    if len(rules) < 3:
        for m in re.finditer(r"^[123]\.\s*(.+)$", text, re.MULTILINE):
            val = m.group(1).strip()
            if val and val not in rules:
                rules.append(val)
    if len(rules) < 3:
        for line in text.splitlines():
            s = line.strip()
            if s and len(s) > 10:
                rules.append(s)
            if len(rules) >= 3:
                break
    return rules[:3]


def _build_debrief_input(scenario: Scenario, state: CallState) -> dict:
    """Assemble the plain-text input for the debrief model. No invented events."""
    decisions_summary: list[str] = []
    for d in state.decisions_taken:
        decision_id = d.get("decision_id", "?")
        tactic = d.get("tactic", "?")
        outcome = d.get("outcome", "?")
        decisions_summary.append(f"{decision_id}:{tactic}:{outcome}")
    return {
        "scenario_id": scenario.id,
        "scenario_title": scenario.title,
        "persona_name": scenario.persona.name,
        "language": state.language,
        "decisions_summary": chr(10).join(decisions_summary) if decisions_summary else "None",
    }


def _static_debrief(scenario: Scenario, state: CallState) -> Debrief:
    """Build a debrief purely from scenario feedback strings (no model)."""
    moments: list[dict] = []
    rules: list[str] = [
        "Hang up and call back using the number on your card or statement.",
        "Never share one-time codes or passwords with anyone who calls you.",
        "Never install software or send money because a caller pressures you to.",
    ]
    for i, d in enumerate(state.decisions_taken):
        decision_id = d.get("decision_id", f"dec_{i}")
        what = f"On {decision_id}, you chose the unsafe option."
        say = "Verify through an official channel before acting."
        moments.append({
            "decision_id": decision_id,
            "what_happened": what,
            "say_ininstead": say,
        })
    if not moments:
        moments.append({
            "decision_id": "none",
            "what_happened": "No decisions were recorded during the call.",
            "say_ininstead": "If you ever get a real suspicious call, hang up and call the official number.",
        })
    summary = f"Debrief for {scenario.title}. You made {len(state.decisions_taken)} decision(s). Review each moment and what to say instead next time."
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