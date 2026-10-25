"""Safety guardrails.

- Input masking (server-side, before any model call): replace digit runs of
  6 or more, email addresses, and phone-number-like strings with [hidden].
- Output filter on every caller line: reject and regenerate if it contains a
  URL, email, phone-like string, or a name from a small blocklist of real
  banks/couriers. Falls back to fallback_lines.
- Caller must never give operational fraud instructions.
"""

import re
from typing import Tuple

# Real bank / courier names that must never appear in model output (fictional-only rule).
BLOCKLIST_NAMES = [
    "chase", "bank of america", "wells fargo", "citibank", "hsbc", "barclays",
    "sbi", "hdfc", "icici", "axis bank", "kotak", "paytm",
    "dhl", "fedex", "ups", "usps", "royal mail", "Australia Post",
    "amazon", "flipkart",
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-]{7,}\d")
DIGIT_RUN_RE = re.compile(r"\d{6,}")
URL_RE = re.compile(r"https?://|www\.")
# Blocklist names matched with word boundaries so "purchase" doesn't match "chase".
BLOCKLIST_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in BLOCKLIST_NAMES) + r")\b", re.IGNORECASE
)


def mask_input(text: str) -> Tuple[str, bool]:
    """Mask sensitive patterns in user input. Returns (masked_text, triggered)."""
    triggered = False
    masked = text

    def _hide(m):
        nonlocal triggered
        triggered = True
        return "[hidden]"

    masked = EMAIL_RE.sub(_hide, masked)
    masked = PHONE_RE.sub(_hide, masked)
    masked = DIGIT_RUN_RE.sub(_hide, masked)
    return masked, triggered


def output_safe(text: str) -> bool:
    """Return True if the caller line passes the output filter."""
    low = text.lower()
    if URL_RE.search(low):
        return False
    if EMAIL_RE.search(low):
        return False
    if PHONE_RE.search(low):
        return False
    if BLOCKLIST_RE.search(low):
        return False
    return True


def fraud_instruction(text: str) -> bool:
    """Heuristic: user is asking the caller how to commit fraud."""
    low = text.lower()
    triggers = [
        "how to scam", "how to defraud", "teach me to scam", "teach me to defraud",
        "help me steal", "how to hack", "credit card numbers",
        "social security number", "ssn", "bank login",
    ]
    return any(t in low for t in triggers)