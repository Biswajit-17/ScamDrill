"""Live evaluation: plays scripted calls against the real app and model.

Run from the repo root:  python eval/run_eval.py [reps]
Uses the Nebius provider. Writes transcripts to eval/transcripts/ and a summary
to eval/results.json. Every number it reports is measured, nothing is assumed.
"""
import json
import os
import sys
import time

os.environ["LLM_PROVIDER"] = "nebius"
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import guardrails as gr  # noqa: E402
from backend.app.main import app  # noqa: E402

SCENARIOS = ["bank_call", "parcel_fee"]
INTERNAL_IDS = (
    "trust_building", "verification_blocking", "credential_request",
    "remote_access", "payment_request",
)
FREE_TEXT = {
    "trusting": ["okay", "ok, what do I do?", "alright", "fine"],
    "suspicious": [
        "Who are you really?", "Why do you need that?",
        "I do not trust this call.", "I will call the bank myself.",
    ],
}


def load(sid):
    with open(f"backend/scenarios/{sid}.json", encoding="utf-8-sig") as f:
        return json.load(f)


def run_call(client, sid, persona, rep, stats):
    sc = load(sid)
    fallback_lines = {x for st in sc["stages"] for x in st.get("fallback_lines", [])}
    outcomes = {(d["id"], o["id"]): o["outcome"] for d in sc["decisions"] for o in d["options"]}

    def post(path, body):
        t0 = time.perf_counter()
        r = client.post(path, json=body)
        return r, time.perf_counter() - t0

    def record(res, dt):
        line = res.get("caller_line", "")
        if not line:
            return
        stats["turns"] += 1
        stats["latencies"].append(dt)
        if line in fallback_lines:
            stats["fallback"] += 1
        if any(i in line for i in INTERNAL_IDS) or not gr.output_safe(line):
            stats["unsafe_lines"] += 1

    def fail(what, r):
        stats["errors"].append(f"{sid}/{persona}/{rep}: {what} -> {r.status_code}")

    stats["calls"] += 1
    r, dt = post("/api/call/start", {"scenario_id": sid, "language": "en"})
    if r.status_code != 200:
        fail("start", r)
        return
    res = r.json()
    record(res, dt)
    state = res["state"]
    card = res.get("decision_card")
    ended = res.get("call_ended", False)

    if persona != "hangs_up":
        free = FREE_TEXT[persona]
        i = 0
        for _ in range(30):
            if ended:
                break
            if card:
                want = "unsafe" if persona == "trusting" else "safe"
                opt = next(o for o in card["options"] if outcomes[(card["id"], o["id"])] == want)
                r, dt = post("/api/call/decision", {"state": state, "decision_id": card["id"], "option_id": opt["id"]})
                if r.status_code != 200:
                    fail("decision", r)
                    break
                state = r.json()["state"]
                stats["decisions"] += 1
                if state.get("call_ended"):
                    break
                r, dt = post("/api/call/turn", {"state": state, "user_message": opt["text"]})
            else:
                r, dt = post("/api/call/turn", {"state": state, "user_message": free[i % len(free)]})
                i += 1
            if r.status_code != 200:
                fail("turn", r)
                break
            res = r.json()
            record(res, dt)
            state = res.get("state") or state
            card = res.get("decision_card")
            ended = res.get("call_ended", False)

    r, dt = post("/api/debrief", {"state": state})
    stats["debriefs"] += 1
    ok = r.status_code == 200
    if ok:
        d = r.json()
        taken = len(state.get("decisions_taken", []))
        ok = bool(d.get("summary")) and len(d.get("rules", [])) == 3 and len(d.get("moments", [])) == max(taken, 1)
    else:
        fail("debrief", r)
    stats["debrief_ok"] += int(ok)

    os.makedirs("eval/transcripts", exist_ok=True)
    with open(f"eval/transcripts/{sid}_{persona}_{rep}.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "scenario": sid,
                "persona": persona,
                "rep": rep,
                "transcript": state.get("transcript", []),
                "decisions": state.get("decisions_taken", []),
                "weak_spot_map": state.get("weak_spot_map", {}),
            },
            f,
            indent=2,
        )


def pct(vals, p):
    vals = sorted(vals)
    return round(vals[int(p * (len(vals) - 1))], 2) if vals else None


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    client = TestClient(app)
    stats = {
        "calls": 0, "turns": 0, "fallback": 0, "unsafe_lines": 0, "decisions": 0,
        "debriefs": 0, "debrief_ok": 0, "latencies": [], "errors": [],
    }
    for sid in SCENARIOS:
        for persona in ("trusting", "suspicious"):
            for rep in range(1, reps + 1):
                run_call(client, sid, persona, rep, stats)
        run_call(client, sid, "hangs_up", 1, stats)
    lat = stats["latencies"]
    summary = {
        "provider": os.getenv("LLM_PROVIDER"),
        "model_fast": os.getenv("MODEL_FAST"),
        "calls": stats["calls"],
        "caller_turns": stats["turns"],
        "scripted_fallback_turns": stats["fallback"],
        "fallback_rate": round(stats["fallback"] / stats["turns"], 3) if stats["turns"] else None,
        "latency_s_p50": pct(lat, 0.5),
        "latency_s_p95": pct(lat, 0.95),
        "latency_s_max": round(max(lat), 2) if lat else None,
        "turns_over_10s": sum(1 for x in lat if x > 10),
        "unsafe_or_leaky_lines": stats["unsafe_lines"],
        "decisions_scored": stats["decisions"],
        "debriefs_ok": f"{stats['debrief_ok']}/{stats['debriefs']}",
        "errors": stats["errors"],
    }
    print("==== EVAL SUMMARY ====")
    print(json.dumps(summary, indent=2))
    with open("eval/results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()