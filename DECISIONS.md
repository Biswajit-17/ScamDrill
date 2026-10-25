# ScamDrill — Build Decisions

Owner: Biswajit. Updated during build.

## Model selection
- `MODEL_FAST` (caller turns): `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (nano class)
- `MODEL_REASON` (debrief): `nvidia/nemotron-3-super-120b-a12b` (super class)
  - Spec originally suggested Ultra for debrief; we use Super per product decision.
- Both are OpenAI-compatible. Provider selected via `LLM_PROVIDER` (`openrouter` for testing, `nebius` for final/deploy).

## Provider configuration
- Testing: OpenRouter (`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`)
- Final/deploy: Nebius Token Factory (`NEBIUS_API_KEY`, `NEBIUS_BASE_URL`)
- The LLM client reads `LLM_BASE_URL` + `LLM_API_KEY` resolved from `LLM_PROVIDER`; base URLs and model IDs are never hardcoded.

## Nebius Token Factory verification (§13)
1. Base URL: `https://api.tokenfactory.nebius.com/v1` — confirmed (docs introduction page)
2. Auth: `Authorization: Bearer <token>` via `NEBIUS_API_KEY` — confirmed
3. OpenAI-compatible: Yes (`chat.completions.create`, `response_format: {"type": "json_object"}`) — confirmed
4. Nemotron IDs confirmed from public catalog:
   - Nano: `nvidia/Nemotron-3-Nano-30B-A3B`
   - Super: `nvidia/nemotron-3-super-120b-a12b`
   - Ultra: `nvidia/Nemotron-3-Ultra-550b-a55b` (not used)
5. `GET /v1/models` requires `ai_project_id` query param; without it returns 400 "Project ID is missing or invalid" — noted, not blocking.
6. Still to verify with a live key: rate limits, latency, credit balance, Hindi quality.

## Repo layout
- Flattened one level from spec (no `scamdrill/` nesting): `backend/`, `frontend/`, `eval/`, `demo/`, `docs/` at repo root.

## Deferred / out of scope for now
- Hindi language toggle (cut order: first to cut if behind)
- Share/practice links (cut order: second)
- Nebius Serverless Endpoints hosting (optional; any free host with public URL)