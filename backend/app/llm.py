"""LLM client wrapper for OpenAI-compatible providers (OpenRouter / Nebius).

Reads base URL and API key from environment variables resolved by LLM_PROVIDER.
Never hardcodes a base URL or model ID. Supports timeouts and one backoff retry
on rate-limit / transient errors.

Every model call is logged with: raw content, finish_reason, reasoning field,
token counts, and a failure category (empty, parse_error, subset_violation,
output_filter_rejection, rate_limit, timeout, api_error).
"""

import json
import os
import time
import random
from typing import Optional

from openai import OpenAI
from openai import RateLimitError, APIError, APITimeoutError

from .schemas import CallerLine, Debrief


FAIL_EMPTY = "empty"
FAIL_PARSE_ERROR = "parse_error"
FAIL_SUBSET_VIOLATION = "subset_violation"
FAIL_OUTPUT_FILTER = "output_filter_rejection"
FAIL_RATE_LIMIT = "rate_limit"
FAIL_TIMEOUT = "timeout"
FAIL_API_ERROR = "api_error"


call_log: list[dict] = []


def _resolve_provider() -> tuple[str, str]:
    """Return (base_url, api_key) based on LLM_PROVIDER env var.

    LLM_PROVIDER=openrouter  -> OPENROUTER_BASE_URL / OPENROUTER_API_KEY
    LLM_PROVIDER=nebius      -> NEBIUS_BASE_URL   / NEBIUS_API_KEY
    Falls back to LLM_BASE_URL / LLM_API_KEY if set directly.
    """
    provider = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()

    if provider == "nebius":
        base_url = os.getenv("NEBIUS_BASE_URL") or os.getenv("LLM_BASE_URL")
        api_key = os.getenv("NEBIUS_API_KEY") or os.getenv("LLM_API_KEY")
    else:
        # default to openrouter for testing
        base_url = os.getenv("OPENROUTER_BASE_URL") or os.getenv("LLM_BASE_URL")
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")

    if not base_url:
        raise RuntimeError(
            "LLM base URL not configured. Set LLM_BASE_URL or the provider-specific "
            "*_BASE_URL env var."
        )
    if not api_key:
        raise RuntimeError(
            "LLM API key not configured. Set LLM_API_KEY or the provider-specific "
            "*_API_KEY env var."
        )
    return base_url, api_key


def get_client() -> OpenAI:
    base_url, api_key = _resolve_provider()
    return OpenAI(base_url=base_url, api_key=api_key, timeout=20.0)


def get_model_fast() -> str:
    model = os.getenv("MODEL_FAST")
    if not model:
        raise RuntimeError("MODEL_FAST env var is not set")
    return model


def get_model_reason() -> str:
    model = os.getenv("MODEL_REASON")
    if not model:
        raise RuntimeError("MODEL_REASON env var is not set")
    return model


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)
        # text[1] is the content between fences (may start with "json\n")
        if len(text) >= 2:
            inner = text[1]
            if inner.lstrip().startswith("json"):
                inner = inner[len("json"):].lstrip()
            return inner.strip()
    return text


def _log_call(
    *,
    model: str,
    role: str,
    raw_content: str,
    finish_reason: Optional[str],
    reasoning: Optional[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
    latency_s: float,
    success: bool,
    failure_category: Optional[str] = None,
    fallback_used: bool = False,
    fallback_message: Optional[str] = None,
):
    entry = {
        "ts": time.time(),
        "model": model,
        "role": role,
        "raw_content": raw_content,
        "finish_reason": finish_reason,
        "reasoning": reasoning,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency_s": round(latency_s, 4),
        "success": success,
        "failure_category": failure_category,
        "fallback_used": fallback_used,
        "fallback_message": fallback_message,
    }
    call_log.append(entry)
    print(
        f"[LLM {role}] model={model} latency={entry['latency_s']}s "
        f"finish_reason={finish_reason} tokens={total_tokens} "
        f"success={success} fail={failure_category} "
        f"raw={raw_content[:100]!r}"
    )


def _extract_reasoning(message_obj) -> Optional[str]:
    """Extract a reasoning field if the provider returns one (Nemotron may include it)."""
    if message_obj is None:
        return None
    try:
        d = message_obj.model_dump() if hasattr(message_obj, "model_dump") else dict(message_obj)
    except Exception:
        return None
    for key in ("reasoning", "reasoning_content", "reasoning_trace"):
        if key in d and d[key] is not None:
            return str(d[key])
    return None


def generate_caller_line(
    system_prompt: str,
    user_prompt: str,
    stage_tactics: list[str],
    fallback_lines: list[str],
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> tuple[CallerLine, bool]:
    """Generate one caller turn as plain text.

    Returns (CallerLine, fallback_used). The model returns plain text; tactics
    come from stage_tactics (not from the model). Output filter + fallback lines
    are applied only for empty or filtered outputs.

    Failure categories logged: empty, parse_error, subset_violation,
    output_filter_rejection, rate_limit, timeout, api_error.

    Constraint: do not write numbers longer than 3 digits or phone numbers.
    """
    from .guardrails import output_safe

    client = get_client()
    model = get_model_fast()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    attempt = 0
    while True:
        attempt += 1
        t0 = time.perf_counter()
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                max_completion_tokens=max_tokens,
            )
            elapsed = time.perf_counter() - t0

            choice = completion.choices[0]
            message = choice.message
            raw_content = message.content or ""
            finish_reason = choice.finish_reason
            reasoning = _extract_reasoning(message)

            usage = completion.usage
            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            # Check for empty content
            if not raw_content.strip():
                _log_call(
                    model=model, role="caller",
                    raw_content=raw_content,
                    finish_reason=finish_reason, reasoning=reasoning,
                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                    total_tokens=total_tokens, latency_s=elapsed,
                    success=False, failure_category=FAIL_EMPTY,
                )
                if attempt >= 2:
                    fb = random.choice(fallback_lines) if fallback_lines else (
                        "I'm sorry, I didn't catch that. Could you repeat?"
                    )
                    _log_call(
                        model=model, role="caller",
                        raw_content=fb, finish_reason=finish_reason, reasoning=None,
                        prompt_tokens=None, completion_tokens=None, total_tokens=None,
                        latency_s=elapsed, success=True, failure_category=None,
                        fallback_used=True, fallback_message=fb,
                    )
                    return CallerLine(message=fb, tactics=list(stage_tactics)), True
                continue

            # Output filter on plain text
            if not output_safe(raw_content):
                _log_call(
                    model=model, role="caller",
                    raw_content=raw_content,
                    finish_reason=finish_reason, reasoning=reasoning,
                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                    total_tokens=total_tokens, latency_s=elapsed,
                    success=False, failure_category=FAIL_OUTPUT_FILTER,
                )
                if attempt >= 2:
                    fb = random.choice(fallback_lines) if fallback_lines else (
                        "I'm sorry, I didn't catch that. Could you repeat?"
                    )
                    _log_call(
                        model=model, role="caller",
                        raw_content=fb, finish_reason=finish_reason, reasoning=None,
                        prompt_tokens=None, completion_tokens=None, total_tokens=None,
                        latency_s=elapsed, success=True, failure_category=None,
                        fallback_used=True, fallback_message=fb,
                    )
                    return CallerLine(message=fb, tactics=list(stage_tactics)), True
                continue

            # Success: plain text, tactics from stage
            _log_call(
                model=model, role="caller",
                raw_content=raw_content,
                finish_reason=finish_reason, reasoning=reasoning,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                total_tokens=total_tokens, latency_s=elapsed,
                success=True, failure_category=None,
            )
            return CallerLine(message=raw_content, tactics=list(stage_tactics)), False

        except RateLimitError as exc:
            elapsed = time.perf_counter() - t0
            _log_call(
                model=model, role="caller",
                raw_content="", finish_reason=None, reasoning=None,
                prompt_tokens=None, completion_tokens=None, total_tokens=None,
                latency_s=elapsed, success=False, failure_category=FAIL_RATE_LIMIT,
            )
            if attempt >= 2:
                fb = random.choice(fallback_lines) if fallback_lines else (
                    "I'm sorry, I didn't catch that. Could you repeat?"
                )
                return CallerLine(message=fb, tactics=list(stage_tactics)), True
            time.sleep(2)
            continue

        except APITimeoutError as exc:
            elapsed = time.perf_counter() - t0
            _log_call(
                model=model, role="caller",
                raw_content="", finish_reason=None, reasoning=None,
                prompt_tokens=None, completion_tokens=None, total_tokens=None,
                latency_s=elapsed, success=False, failure_category=FAIL_TIMEOUT,
            )
            if attempt >= 2:
                fb = random.choice(fallback_lines) if fallback_lines else (
                    "I'm sorry, I didn't catch that. Could you repeat?"
                )
                return CallerLine(message=fb, tactics=list(stage_tactics)), True
            continue

        except APIError as exc:
            elapsed = time.perf_counter() - t0
            _log_call(
                model=model, role="caller",
                raw_content="", finish_reason=None, reasoning=None,
                prompt_tokens=None, completion_tokens=None, total_tokens=None,
                latency_s=elapsed, success=False, failure_category=FAIL_API_ERROR,
            )
            if attempt >= 2:
                fb = random.choice(fallback_lines) if fallback_lines else (
                    "I'm sorry, I didn't catch that. Could you repeat?"
                )
                return CallerLine(message=fb, tactics=list(stage_tactics)), True
            continue


def generate_debrief(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 600,
) -> Debrief:
    """Generate the debrief with the reasoning model. Raises on failure; the
    caller (debrief.py) is responsible for the static fallback."""
    client = get_client()
    model = get_model_reason()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content or ""
    raw = _strip_code_fences(raw)

    # Determine failure category
    fail_category = None
    if completion.choices[0].finish_reason == "length":
        fail_category = "empty"  # model burned budget, returned empty content
    elif completion.choices[0].finish_reason == "output_filter":
        fail_category = "output_filter_rejection"
    elif completion.choices[0].finish_reason is None:
        fail_category = "parse_error"  # no finish reason typically means model didn't comply

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
        fail_category = "parse_error" if not fail_category else fail_category

    # Log the call
    call_log.append({
        "function": "generate_debrief",
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "finish_reason": completion.choices[0].finish_reason,
        "failure_category": fail_category,
        "raw_content_length": len(raw),
        "latency_ms": int((completion.created - completion.model_creation) * 1000) if hasattr(completion, 'created') else None,
    })

    return Debrief(**data)


def get_call_log() -> list[dict]:
    """Return the module-level call log (copy)."""
    return list(call_log)


def clear_call_log() -> None:
    """Clear the module-level call log."""
    call_log.clear()