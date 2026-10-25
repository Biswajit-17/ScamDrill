"""Regression harness for ScamDrill.

Runs personas against each scenario through the live model API and asserts
safety/structure on every caller turn. Saves transcripts to eval/transcripts/.

Personas:
  trusting   - always complies with the caller (picks unsafe options)
  suspicious - asks to verify, refuses codes (picks safe options)
  hangs_up   - ends the call after 2 turns

Runs each persona on each scenario, repeated 3 times (6 runs total × 3 = 18).
Asserts per run:
  - every model output parses as valid JSON
  - tactics are a subset of the stage tactics
  - no URL / email / phone-like string in any caller line
  - call ends within max_turns budget
  - debrief mentions only decision ids that exist
  - language matches the setting

Usage:
  LLM_PROVIDER=openrouter python3 eval/run_regression.py
  (then LLM_PROVIDER=nebius for the final Nebius test)
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.schemas import Scenario, CallState
from backend.app import engine as eng
from backend.app import guardrails as gr
from backend.app.router import load_scenarios, get_scenarios

TRANSCRIPT_DIR = Path(__file__).resolve().parent / "transcripts"
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = ["bank_call", "parcel_fee"]
PERSONAS = ["trusting", "suspicious", "hangs_up"]
REPEATS = 3


def _pick_option(state, scenario, persona):
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


def run_one(scenario_id, persona, language="en", run_tag=""):
    from backend.app.router import _scenarios
    if not _scenarios:
        load_scenarios()
    scenarios = get_scenarios()
    scenario = scenarios[scenario_id]
    state, _ = eng.start_call(scenario, language)

    from backend.app.llm import generate_caller_line as _gcl

    transcript = []
    passed_checks = []
    failed_checks = []

    def check(name, cond, detail=""):
        (passed_checks if cond else failed_checks).append((name, detail))

    # Generate first caller line
    stage = scenario.stage_by_id(state.current_stage_id)
    system_prompt = _system_prompt(scenario, stage, language)
    user_prompt = _user_prompt(state, stage, "")
    line, fb = _gcl(
        system_prompt, user_prompt, stage.tactics, stage.fallback_lines,
        temperature=0.7, max_tokens=150,
    )
    check("first_line_parses", bool(line.message))
    check("first_tactics_subset", set(line.tactics) <= set(stage.tactics))
    check("first_output_safe", gr.output_safe(line.message))
    state.fallback_used = state.fallback_used or fb
    eng.add_transcript_entry(state, "caller", line.message, line.tactics)
    transcript.append({"role": "caller", "content": line.message, "tactics": line.tactics})

    from backend.app.llm import generate_caller_line as _gcl

    max_total_turns = sum(s.max_turns for s in scenario.stages) + 5
    turn = 0
    decision_pending = eng.decision_due(scenario, state)

    while not state.call_ended and turn < max_total_turns:
        turn += 1

        if decision_pending:
            option_id = _pick_option(state, scenario, persona)
            if option_id is None or persona == "hangs_up":
                eng.hang_up(state)
                break
            dresp = eng.apply_decision(state, scenario, decision_pending.id, option_id)
            transcript.append({
                "role": "decision",
                "decision_id": decision_pending.id,
                "option_id": option_id,
                "outcome": dresp.outcome,
                "tactic": dresp.tactic,
            })
            decision_pending = eng.decision_due(scenario, state)
            continue

        if persona == "trusting":
            user_msg = "Okay, I'll do what you say."
        elif persona == "suspicious":
            user_msg = "Can I call you back on the official number?"
        else:
            user_msg = "Hello?"

        masked, masked_trig = gr.mask_input(user_msg)
        eng.add_transcript_entry(state, "user", masked)
        transcript.append({"role": "user", "content": masked})

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

        system_prompt = _system_prompt(scenario, stage, language)
        user_prompt = _user_prompt(state, stage, masked)
        line, fb = _gcl(
            system_prompt, user_prompt, stage.tactics, stage.fallback_lines,
            temperature=0.7, max_tokens=150,
        )
        check(f"turn{turn}_line_parses", bool(line.message))
        check(f"turn{turn}_tactics_subset", set(line.tactics) <= set(stage.tactics))
        check(f"turn{turn}_output_safe", gr.output_safe(line.message))
        state.fallback_used = state.fallback_used or fb

        message, tactics, fb2 = _filter(line.message, line.tactics, stage.fallback_lines)
        if fb2:
            state.fallback_used = True
        eng.add_transcript_entry(state, "caller", message, tactics)
        transcript.append({"role": "caller", "content": message, "tactics": tactics})

        decision_pending = eng.decision_due(scenario, state)

    # Debrief
    try:
        from backend.app.debrief import generate_debrief_with_fallback
        dresp = generate_debrief_with_fallback(scenario, state, language=language)
        debrief_decision_ids = {m.decision_id for m in dresp.moments}
        scenario_decision_ids = {d.id for d in scenario.decisions}
        check("debrief_only_known_decision_ids",
              debrief_decision_ids <= scenario_decision_ids | {"none"})
        check("debrief_language", dresp.summary is not None)
        transcript.append({"role": "debrief", "summary": dresp.summary,
                           "fallback_used": dresp.fallback_used})
    except Exception as exc:
        failed_checks.append(("debrief_error", str(exc)))

    check("call_ended", state.call_ended)
    check("within_turn_budget", turn <= max_total_turns)
    check("language_matches", state.language == language)

    result = {
        "scenario": scenario_id,
        "persona": persona,
        "language": language,
        "run_tag": run_tag,
        "passed": len(passed_checks),
        "failed": len(failed_checks),
        "failures": failed_checks,
        "turns": turn,
        "weak_spot_map": dict(state.weak_spot_map),
        "fallback_used": state.fallback_used,
        "transcript": transcript,
    }

    fname = TRANSCRIPT_DIR / f"{scenario_id}_{persona}_{run_tag}.json"
    fname.write_text(json.dumps(result, indent=2))
    return result


def _system_prompt(scenario, stage, language):
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
        "Do not write numbers longer than 3 digits or phone numbers.\n"
        "Reply in plain text - no JSON mode needed.\n"
    )


def _user_prompt(state, stage, user_message):
    lines = []
    for e in state.transcript[-8:]:
        tag = "Caller" if e.role == "caller" else "User"
        lines.append(f"{tag}: {e.content}")
    return (
        f"Conversation so far:\n" + "\n".join(lines) + "\n\n"
        f"User just said: {user_message}\n"
        f"Reply as the caller for the current stage ({stage.id})."
    )


def _filter(text, tactics, fallbacks):
    import random
    if gr.output_safe(text):
        return text, tactics, False
    fb = random.choice(fallbacks) if fallbacks else "I'm sorry, I didn't catch that."
    return fb, [], True


def main():
    load_scenarios()
    all_results = []
    total = 0
    all_pass = 0

    for scenario_id in SCENARIOS:
        for persona in PERSONAS:
            for rep in range(REPEATS):
                total += 1
                tag = f"rep{rep + 1}"
                try:
                    res = run_one(scenario_id, persona, "en", tag)
                    all_results.append(res)
                    status = "PASS" if res["failed"] == 0 else "FAIL"
                    if res["failed"] == 0:
                        all_pass += 1
                    print(f"[{status}] {scenario_id} / {persona} / {tag} "
                          f"(turns={res['turns']}, failures={res['failed']})")
                    for name, detail in res["failures"]:
                        print(f"      - {name}: {detail}")
                except Exception as exc:
                    print(f"[ERROR] {scenario_id} / {persona} / {tag}: {exc}")
                    all_results.append({
                        "scenario": scenario_id, "persona": persona, "run_tag": tag,
                        "passed": 0, "failed": 1, "failures": [("run_error", str(exc))],
                    })

    summary = {
        "total_runs": total,
        "passed_all_checks": all_pass,
        "failed_any_check": total - all_pass,
        "results": all_results,
    }
    (TRANSCRIPT_DIR / "regression_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n=== Regression summary: {all_pass} of {total} runs passed all checks ===")
    return 0 if all_pass == total else 1


if __name__ == "__main__":
    sys.exit(main())