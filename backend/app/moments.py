"""Deterministic debrief content built from the authored scenario data.

Nothing here calls a model, so the debrief always renders and always matches
what the player actually chose."""


def _decision(scenario, decision_id):
    for d in scenario.decisions:
        if d.id == decision_id:
            return d
    return None


def _option(decision, option_id):
    for o in decision.options:
        if o.id == option_id:
            return o
    return None


def _safe_option(decision):
    for o in decision.options:
        if o.outcome == "safe":
            return o
    return None


def build_moments(scenario, state):
    moments = []
    for taken in state.decisions_taken:
        decision = _decision(scenario, taken.get("decision_id"))
        if decision is None:
            continue
        option = _option(decision, taken.get("option_id"))
        if option is None:
            continue
        what = f'{decision.prompt} You chose: "{option.text}" {option.feedback}'.strip()
        if option.outcome == "safe":
            say = "Keep doing this: " + option.text
        else:
            safe = _safe_option(decision)
            if safe is not None:
                say = f'Try this instead: "{safe.text}" {safe.feedback}'.strip()
            else:
                say = "Stop and verify through an official channel before acting."
        moments.append({"decision_id": decision.id, "what_happened": what, "say_instead": say})
    return moments


def build_summary(scenario, state):
    taken = state.decisions_taken
    if not taken:
        return "You ended the call before any decision point. Hanging up on an unexpected call is always a safe option."
    safe = sum(1 for t in taken if t.get("outcome") == "safe")
    total = len(taken)
    return f"You made {total} decision(s) in this call: {safe} safe and {total - safe} risky."

RULES = {
    "bank_call": [
        "Hang up and call back using the number on your card or statement.",
        "Never share one-time codes or passwords with anyone who calls you.",
        "Never install software or send money because a caller pressures you to.",
    ],
    "parcel_fee": [
        "A real courier will not ask for payment or card details on an unexpected call. Check the tracking number yourself in the courier's official app or website.",
        "Never open a payment link or read out a card number or one-time code because a caller or text asks you to.",
        "Pay now or lose the parcel is pressure. Stop, hang up, and check through the official channel.",
    ],
}

GENERIC_RULES = [
    "Hang up and check through an official channel you look up yourself.",
    "Never share codes, passwords or card details with someone who contacts you.",
    "Urgency and secrecy are warning signs. Slow down before you act.",
]


def build_rules(scenario):
    return RULES.get(scenario.id, GENERIC_RULES)
