# ScamDrill

A practice simulator for recognising scam calls. An AI plays a fictional scammer. You play the call, make decisions, and a debrief shows which pressure tactics worked on you.

Live demo: https://scamdrill.onrender.com (free hosting: the first load after a quiet period can take up to a minute)

Built for the Nebius x NVIDIA Global AI Hackathon. Track: Best Apps and Agents.

ScamDrill is a practice tool. It does not claim to reduce fraud, it is not a study, and it is not official advice.

## What it does

1. Pick a scenario (a fake bank fraud call, or a fake parcel-fee call). Everything in them is fictional.
2. Optionally take a 5-question pre-quiz. It shows right and wrong answers.
3. Play the call as a chat. You can type freely, and at four points a decision card asks what you do.
4. Read the debrief: a summary, each key moment (what you chose, why it was safe or risky, what to do instead), which tactics worked on you, and three rules to remember.
5. Optionally take a different 5-question post-quiz and compare scores.

The pressure tactics used in the scenarios: authority, urgency, fear, isolation, trust building, blocking verification, credential requests, remote access, payment requests.

## How it works

The engine decides, the model phrases.

- **Scenarios** are authored JSON files in `backend/scenarios/`: five stages, four decision cards, and the feedback text for every option.
- **A deterministic state machine** (`backend/app/engine.py`) decides when a stage advances and when a decision card appears. Decision outcomes and the weak-spot map are scored from the JSON, never from a model.
- **Caller lines** are written by a Nemotron model. It receives the current stage goal and the recent conversation, and replies in plain text. Tactic tags come from the stage, not from the model.
- **The debrief** is built from the authored scenario data and the choices you made. It makes no model call, so it always renders and always matches what you chose.
- **The server is stateless.** The browser holds the call state and sends it with each request.

## Where Nemotron and Nebius Token Factory are used

- Model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, called through Nebius Token Factory's OpenAI-compatible API, for every caller line (`backend/app/llm.py`, `generate_caller_line`).
- The model's thinking is switched off per request with `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`. Details in the results below.
- Other Nebius services (Serverless Endpoints, Serverless Jobs) are not used. The app is hosted on Render.
- Larger Nemotron models are not used at runtime in this version. An earlier version asked a larger model to write the debrief as JSON. In a small test (6 calls) half of the responses fell back, so the debrief was replaced with deterministic content built from the scenario data. `MODEL_REASON` in the config is currently unused.

## Results

Measured with `python eval/run_eval.py 2` against Nebius Token Factory, run from a developer machine. It plays 10 scripted calls through the app code (a trusting player, a suspicious player and a hang-up, for each scenario). Transcripts are in `eval/transcripts/` and the summary is in `eval/results.json`.

| Measurement | Thinking on (before) | Thinking off (final) |
|---|---|---|
| Caller turns | 58 | 58 |
| Turns that fell back to a scripted line | 26 (44.8%) | 0 (0%) |
| Latency per request, median | 22.9 s | 1.3 s |
| Latency per request, 95th percentile | 36.5 s | 1.7 s |
| Requests over 10 s | 44 | 0 |
| Unsafe or leaky caller lines | 0 | 0 |
| Decisions scored correctly | 32 | 32 |
| Debriefs correct | 10 of 10 | 10 of 10 |

What changed between the two runs: with default settings the model spent several hundred tokens on hidden reasoning before every short reply, which pushed requests past the app's 12-second timeout. Disabling thinking removed that cost at the source.

What these numbers do not show: the players are scripted, the sample is small, and the run measures structure, safety filters, speed and scoring. It does not measure how convincing the caller sounds. Zero fallbacks means none occurred in this run, not that they cannot occur.

## Safety and privacy

- Everything is fictional. Banners say so, and the input box asks for made-up details.
- **Input masking:** before any model call, digit runs of 6 or more, email addresses and phone-number-like strings are replaced with `[hidden]`. Names are not masked.
- **Output filter:** a caller line that contains a URL, email address, phone-number-like string, a real-brand name from a blocklist, or an internal tactic label is replaced with a scripted line.
- **No accounts and no database.** Conversation state lives in the browser and is sent with each request. The server logs call metadata and the first 100 characters of each model reply to standard output for debugging, and does not store conversations.
- **Rate limits:** per visitor IP (`IP_CALLS_PER_MIN`) and a daily cap (`DAILY_CALL_CAP`).

## Run locally

Requirements: Python 3.11 or newer, Node 20, a Nebius Token Factory API key.

```
git clone https://github.com/Biswajit-17/ScamDrill.git
cd ScamDrill
cp .env.example .env        # then fill in your values
pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
python -m uvicorn backend.app.main:app --port 8000
```

Open http://localhost:8000.

Docker: `docker build -t scamdrill .` then run it with the same environment variables. The Dockerfile builds the frontend inside the image and listens on `$PORT`.

## Environment variables

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `nebius` for the real deployment. `openrouter` exists for local development only. |
| `NEBIUS_API_KEY` | Token Factory key. Never commit it. |
| `NEBIUS_BASE_URL` | Token Factory base URL. |
| `MODEL_FAST` | Model ID for caller lines. |
| `MODEL_REASON` | Currently unused. |
| `DAILY_CALL_CAP` | Maximum API requests per day (default: unlimited). |
| `IP_CALLS_PER_MIN` | Per-visitor request limit (default 600). |

## Tests and evaluation

```
python -m pytest -q backend/tests     # 30 unit tests, no network needed
python eval/run_eval.py 2             # live evaluation, needs Nebius credentials, a few minutes
```

## Known limitations

- English only.
- The caller is a small model. It can invent details such as amounts, and it sometimes repeats a request instead of moving on.
- In one manual run on the live site the call ended before the final decision card appeared. I could not reproduce it by replaying the same path against the app code.
- The share-link screen is basic and the practice-link flow was not tested end to end.
- Free hosting sleeps after inactivity, so the first request can be slow.
- Names typed by the player are not masked.

## License

MIT. See `LICENSE`.
