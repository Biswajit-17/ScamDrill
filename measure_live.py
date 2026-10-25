"""Comprehensive live-run measurement harness.

Plays both scenarios (bank_call, parcel_fee) with three personas each
(trusting, suspicious, hangs_up) against the live LLM provider, measuring:
  - raw content, finish_reason, reasoning field, token counts per call
  - latency per model call (p50, p95)
  - fallback rate by cause (empty, output_filter, rate_limit, timeout, api_error)

Usage:
  LLM_PROVIDER=nebius python3 measure_live.py
  LLM_PROVIDER=openrouter python3 measure_live.py
"""

import json
import os
import sys
import time
import statistics

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, "backend")

from app.schemas import Scenario, CallState
from app import engine as eng
from app.llm import (
    generate_caller_line, generate_debrief, get_call_log, clear_call_log,
    get_model_fast, get_model_reason,
)
from app.guardrails import mask_input, output_safe
from app.debrief import generate_debrief_with_fallback


SCENARIO_DIR = "backend/scenarios"
SCENARIOS = ["bank_call", "parcel_fee"]
PERSONAS = ["trusting", "suspicious", "hangs_up"]
LANGUAGE = "en"


def system_prompt(scenario, stage, language):
    p = scenario.persona
    return (
        "You are playing a fictional scam caller in a training simulation that teaches "
        "people to recognise scams.\n"
        f"Persona: {p.name}, {p.role} at {p.org}. Everything is fictional.\n"
        f"Current stage goal: {stage.goal}\n"
        f"Rules: reply in {language}. 1 to 3 short sentences. Stay in character.\n"
        "Never include real company names, real phone numbers, real URLs or email addresses.\n"
        "Never give real instructions for committing fraud.\n"
        "Reply with plain text only — no JSON, no code fences."
    )


def user_prompt(state, stage, user_msg):
    lines = []
    for e in state.transcript[-8:]:
        tag = "Caller" if e.role == "caller" else "User"
        lines.append(f"{tag}: {e.content}")
    return (
        f"Conversation so far:\n" + "\n".join(lines) + "\n\n"
        f"User just said: {user_msg}\n"
        f"Reply as the caller for the current stage ({stage.id})."
    )


def pick_option(state, scenario, persona):
    """Choose an option id for the pending decision based on persona."""
    decision = eng.decision_due(scenario, state)
    if not decision:
        return None
    opts = decision.options
    if persona == "trusting":
        unsafe = [o for o in opts if o.outcome == "unsafe"]
        return (unsafe or opts)[0].id
    if persona == "suspicious":
        safe = [o for o in opts if o.outcome == "safe"]
        return (safe or opts)[0].id
    if persona == "hangs_up":
        return None
    return opts[0].id


def run_call(scenario, persona, language="en"):
    """Run one full call. Returns (caller_turn_results, debrief_result)."""
    clear_call_log()
    state, _ = eng.start_call(scenario, language)

    stage = scenario.stage_by_id(state.current_stage_id)
    max_total_turns = sum(s.max_turns for s in scenario.stages) + 10
    turn = 0
    decision_pending = eng.decision_due(scenario, state)
    user_msgs = {
        "trusting": "Okay, I'll do what you say.",
        "suspicious": "Can I call you back on the official number?",
        "hangs_up": "Hello?",
    }

    while not state.call_ended and turn < max_total_turns:
        turn += 1

        if decision_pending:
            option_id = pick_option(state, scenario, persona)
            if option_id is None or persona == "hangs_up":
                eng.hang_up(state)
                break
            eng.apply_decision(state, scenario, decision_pending.id, option_id)
            decision_pending = eng.decision_due(scenario, state)
            continue

        user_msg = user_msgs[persona]
        masked, _ = mask_input(user_msg)
        eng.add_transcript_entry(state, "user", masked)

        stage = scenario.stage_by_id(state.current_stage_id)
        if stage is None:
            state.call_ended = True
            break

        if state.stage_turns >= stage.max_turns:
            state, nxt = eng.advance_stage(state, scenario)
            if nxt is None:
                state.call_ended = True
                break
            stage = nxt

        line, fb = generate_caller_line(
            system_prompt(scenario, stage, language),
            user_prompt(state, stage, masked),
            stage.tactics,
            stage.fallback_lines,
        )
        eng.add_transcript_entry(state, "caller", line.message, line.tactics)
        decision_pending = eng.decision_due(scenario, state)

    # Debrief
    debrief_result = None
    try:
        dresp = generate_debrief_with_fallback(scenario, state, language=language)
        debrief_result = {
            "summary": dresp.summary,
            "moments": len(dresp.moments),
            "rules": len(dresp.rules),
            "fallback_used": dresp.fallback_used,
            "weak_spot_map": dict(dresp.weak_spot_map),
        }
    except Exception as exc:
        debrief_result = {"error": str(exc)}

    caller_results = get_call_log()
    return caller_results, debrief_result




def percentile(sorted_values, p):
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return round(d0 + d1, 4)


def main():
    all_caller_results = []
    all_debrief_results = []
    total_caller_turns = 0

    for scenario_id in SCENARIOS:
        with open(f"{SCENARIO_DIR}/{scenario_id}.json") as f:
            scenario = Scenario(**json.load(f))

        for persona in PERSONAS:
            caller_results, debrief_result = run_call(scenario, persona, LANGUAGE)
            total_caller_turns += len(caller_results)
            all_caller_results.extend(caller_results)
            all_debrief_results.append({
                "scenario": scenario_id,
                "persona": persona,
                "debrief": debrief_result,
            })
            print(f"  {scenario_id}/{persona}: {len(caller_results)} caller turns, "
                  f"debrief fallback={debrief_result.get('fallback_used', 'N/A')}")

    # ---- Caller turn analysis ----
    latencies = sorted([r["latency_s"] for r in all_caller_results if r["success"]])
    fallback_calls = [r for r in all_caller_results if r.get("fallback_used")]
    failed_calls = [r for r in all_caller_results if not r["success"]]

    # Fallback by cause
    fallback_by_cause = {}
    for r in fallback_calls:
        cat = r.get("failure_category") or "none"
        fallback_by_cause[cat] = fallback_by_cause.get(cat, 0) + 1
    for r in failed_calls:
        cat = r.get("failure_category") or "unknown"
        fallback_by_cause[cat] = fallback_by_cause.get(cat, 0) + 1

    total_fallbacks = len(fallback_calls) + len(failed_calls)
    fallback_rate = round(total_fallbacks / len(all_caller_results) * 100, 1) if all_caller_results else 0

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    avg_latency = round(sum(latencies) / len(latencies), 4) if latencies else 0

    # ---- Debrief analysis ----
    debrief_fallbacks = sum(1 for r in all_debrief_results if r["debrief"].get("fallback_used"))
    debrief_total = len(all_debrief_results)
    debrief_fallback_rate = round(debrief_fallbacks / debrief_total * 100, 1) if debrief_total else 0

    print("\n" + "=" * 60)
    print("MEASUREMENT SUMMARY")
    print("=" * 60)
    print(f"Provider:        {os.getenv('LLM_PROVIDER')}")
    print(f"Model (fast):    {get_model_fast()}")
    print(f"Model (reason):  {get_model_reason()}")
    print(f"Total caller turns: {total_caller_turns}")
    print(f"Fallback rate:   {fallback_rate}% ({total_fallbacks}/{len(all_caller_results)})")
    print(f"Fallback by cause: {fallback_by_cause}")
    print(f"Latency p50:     {p50}s")
    print(f"Latency p95:     {p95}s")
    print(f"Latency avg:     {avg_latency}s")
    print(f"Debrief fallback rate: {debrief_fallback_rate}% ({debrief_fallbacks}/{debrief_total})")
    print(f"Target < 10% fallback: {'PASS' if fallback_rate < 10 else 'FAIL'}")

    # Save raw data
    out = {
        "provider": os.getenv("LLM_PROVIDER"),
        "model_fast": get_model_fast(),
        "model_reason": get_model_reason(),
        "total_caller_turns": total_caller_turns,
        "fallback_rate_pct": fallback_rate,
        "fallback_by_cause": fallback_by_cause,
        "latency_p50_s": p50,
        "latency_p95_s": p95,
        "latency_avg_s": avg_latency,
        "debrief_fallback_rate_pct": debrief_fallback_rate,
        "debrief_fallbacks": debrief_fallbacks,
        "debrief_total": debrief_total,
        "target_met": fallback_rate < 10,
        "caller_log": all_caller_results,
        "debrief_results": all_debrief_results,
    }
    path = f"eval/transcripts/measure_{os.getenv('LLM_PROVIDER')}.json"
    os.makedirs("eval/transcripts", exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nRaw data saved to {path}")


if __name__ == "__main__":
    main()
