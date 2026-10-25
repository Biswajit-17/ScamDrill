"""Day 1 terminal script: play S1 (bank_call) end-to-end using the real model.

Requires a live LLM provider key in .env (OpenRouter for testing, Nebius for final).
Run:  LLM_PROVIDER=openrouter python3 play_s1.py
"""

import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, "backend")

from app.schemas import Scenario
from app import engine as eng
from app.llm import generate_caller_line
from app.guardrails import mask_input, output_safe


SCENARIO_PATH = "backend/scenarios/bank_call.json"


def system_prompt(scenario, stage, language):
    p = scenario.persona
    return (
        "You are playing a fictional scam caller in a training simulation that teaches "
        "people to recognise scams.\n"
        f"Persona: {p.name}, {p.role} at {p.org}. Everything is fictional.\n"
        f"Current stage goal: {stage.goal}\n"
        f"Use only these pressure tactics in this stage: {', '.join(stage.tactics)}\n"
        f"Rules: reply in {language}. 1 to 3 short sentences. Stay in character.\n"
        "Never include real company names, real phone numbers, real URLs or email addresses.\n"
        "Never give real instructions for committing fraud.\n"
        'Return ONLY JSON: {"message": "...", "tactics": ["..."]}'
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


def main():
    data = Scenario(**__import__("json").loads(open(SCENARIO_PATH).read()))
    state, _ = eng.start_call(data, "en")

    print(f"=== ScamDrill terminal play: {data.title} ===\n")

    stage = data.stage_by_id(state.current_stage_id)
    while not state.call_ended:
        line, fb = generate_caller_line(
            system_prompt(data, stage, "en"),
            user_prompt(state, stage, ""),
            stage.tactics,
            stage.fallback_lines,
        )
        if not output_safe(line.message):
            line = eng  # fallback handled by llm already; here just note
        print(f"[Caller/{stage.id} tactics={line.tactics}] {line.message}")
        eng.add_transcript_entry(state, "caller", line.message, line.tactics)

        decision = eng.decision_due(data, state)
        if decision:
            print(f"\n[DECISION] {decision.prompt}")
            for o in decision.options:
                print(f"  {o.id}) {o.text}")
            choice = input("> Choose (a/b/c): ").strip().lower()
            dresp = eng.apply_decision(state, data, decision.id, choice)
            print(f"  -> {dresp.outcome} ({dresp.tactic}): {dresp.feedback}\n")
            state, _ = eng.advance_stage(state, data)
            stage = data.stage_by_id(state.current_stage_id) if state.current_stage_id else None
            if stage is None:
                break
            continue

        user_msg = input("\nYou: ").strip()
        if not user_msg:
            print("(hanging up)")
            eng.hang_up(state)
            break
        masked, trig = mask_input(user_msg)
        if trig:
            print("[input masked]")
        eng.add_transcript_entry(state, "user", masked)

        if state.stage_turns >= stage.max_turns:
            state, stage = eng.advance_stage(state, data)
            if stage is None:
                state.call_ended = True
                break

        line, fb = generate_caller_line(
            system_prompt(data, stage, "en"),
            user_prompt(state, stage, masked),
            stage.tactics,
            stage.fallback_lines,
        )
        if not output_safe(line.message):
            import random
            line.message = random.choice(stage.fallback_lines)
            line.tactics = []
        print(f"[Caller/{stage.id} tactics={line.tactics}] {line.message}")
        eng.add_transcript_entry(state, "caller", line.message, line.tactics)
        time.sleep(0.3)

    print("\n=== Call ended. Debrief would render here. ===")


if __name__ == "__main__":
    main()