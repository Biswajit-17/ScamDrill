# ScamDrill — Nebius Token Factory / NVIDIA Tool Feedback

All observations below are from live testing with real API keys. No speculation.

## Token Factory API compatibility

- **Base URL**: `https://api.tokenfactory.nebius.com/v1` (configured via `NEBIUS_BASE_URL` env var, never hardcoded)
- **Auth**: `Authorization: Bearer <token>` via `NEBIUS_API_KEY` env var
- **OpenAI-compatible**: YES. The official `openai` Python SDK works with
  `base_url="https://api.tokenfactory.nebius.com/v1/"` and the standard
  `chat.completions.create()` interface.
- **Chat endpoint**: `POST /v1/chat/completions` with standard fields
  (`model`, `messages`, `temperature`, `max_tokens`, `response_format`).
- **JSON mode**: `response_format: {"type": "json_object"}` is supported.
- **`GET /v1/models`**: returns 400 "Project ID is missing or invalid" unless the
  `ai_project_id` query parameter is supplied. The public docs introduction page's
  curl example does not show this parameter. Not blocking for our use since we
  source model IDs from the catalog via env vars.

## Model selection (Nemotron)

- `MODEL_FAST` (caller turns): `nvidia/Nemotron-3-Nano-30B-A3B` (nano class)
- `MODEL_REASON` (debrief): `nvidia/nemotron-3-super-120b-a12b` (super class)
  - Spec originally suggested Ultra; we use Super per product decision.
- Both IDs confirmed from the public Nebius model catalog.

## Live testing: OpenRouter (initial testing)

Ran `measure_live.py` against OpenRouter with `MODEL_FAST=nvidia/Nemotron-3-Nano-30B-A3B`,
playing S1 (bank_call) end-to-end:

| Metric | Value |
|--------|-------|
| Total model calls | 5 |
| Fallback used (model returned invalid JSON/tactics) | 4/5 = 80.0% |
| Exceptions (generate_caller_line threw) | 0/5 = 0.0% |
| Avg latency per call | 2.843s |
| Max latency per call | 3.68s |

Observation: The nano model on OpenRouter returns invalid JSON or out-of-subset
tactics ~80% of the time. The parse-validate-fallback path (spec §4) works
correctly — the app never shows a broken turn, falling back to static
`fallback_lines`.

## Live testing: Nebius Token Factory (final test)

Ran `measure_live.py` against Nebius with the same model and scenario:

| Metric | Value |
|--------|-------|
| Total model calls | 5 |
| Fallback used | 5/5 = 100.0% |
| Exceptions | 0/5 = 0.0% |
| Avg latency per call | 1.109s |
| Max latency per call | 1.224s |

Observation: Nebius is ~2.6x faster than OpenRouter (1.11s vs 2.84s avg), but
JSON reliability is worse — 100% fallback rate vs 80% on OpenRouter. The nano
model on Nebius consistently returns output that fails either JSON parsing or
tactic-subset validation. The static fallback guarantees the call always renders.

## Timeout decision

- Current hardcoded timeout: 20.0s (in `llm.py get_client()`)
- Measured max latency: 3.68s (OpenRouter), 1.224s (Nebius)
- With one backoff retry (2s sleep), worst-case observed: ~9.4s
- The 20s timeout provides ~5x headroom over observed max. Per spec §4
  ("about 20 s"), this is appropriate. No change needed.

## JSON reliability

- The nano model (Nemotron-3-Nano-30B-A3B) does not reliably produce valid JSON
  with tactic subsets on either provider. Fallback rates: 80% (OpenRouter),
  100% (Nebius).
- The parse-validate-fallback path in `llm.py` handles this gracefully: on
  invalid JSON, wrong tactics, or exceptions, it retries once, then falls back to
  a random `fallback_line` from the stage with `fallback_used=True` logged.
- `output_safe()` filter in `guardrails.py` provides a second line of defense:
  if the model output passes JSON validation but contains a URL/email/phone/
  blocklisted name, it is replaced with a fallback line.

## NVIDIA tools used

- Nemotron 3 Nano (`nvidia/Nemotron-3-Nano-30B-A3B`) for caller turns via Token Factory.
- Nemotron 3 Super (`nvidia/nemotron-3-super-120b-a12b`) configured for debrief (not yet
  live-tested; debrief has static fallback).
- No NVIDIA NIM, Triton, or other tooling beyond the Nemotron models via Token Factory.

## Docs gaps

- `GET /v1/models` requires `ai_project_id` query param; docs introduction page
  doesn't mention this. Worth documenting clearly.
- The model catalog Markdown is human-readable; `/api/public/models_info` is the
  authoritative machine-readable source.
