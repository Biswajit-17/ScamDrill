# Feedback on Nebius Token Factory and NVIDIA Nemotron

Written from building ScamDrill. Every number below comes from my own runs (see `eval/results.json` and the README). Sample sizes are small.

## What worked well

- **OpenAI-compatible API.** The standard OpenAI Python client worked against `https://api.tokenfactory.nebius.com/v1` with only a base URL and key change. Setup took minutes.
- **Model availability.** `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` was available by ID and returned clean plain-text replies once configured.
- **Speed once configured.** With thinking disabled, median latency per request was 1.3 s and 95th percentile 1.7 s (58 caller turns, no failures, no timeouts).
- **Stable under repeated use.** Across the evaluation runs there were no API errors from the service itself.

## Problems I hit

1. **Hidden reasoning dominates latency and cost for short replies.** With default settings, a 25-word caller line used roughly 500 to 1,000 completion tokens, most of it reasoning. In my first full evaluation, median latency per request was 22.9 s, 95th percentile 36.5 s, and 44.8% of turns hit my 12 s timeout and fell back to a scripted line.
2. **Empty replies when `max_tokens` is low.** With a 150-token limit, the response came back with an empty `content` and `finish_reason=length`, because the reasoning used the whole budget. Nothing in the response made it obvious that reasoning was the cause. I only found it by logging the raw response.
3. **The thinking switch was hard to find.** I turned reasoning off with `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`. I did not find this in the chat completions API reference pages my coding agent checked. A `/no_think` prefix in the system prompt was unreliable: one of two test calls still used about 1,860 tokens.
4. **JSON output was unreliable on the Nano model in my early tests.** Asking for JSON with a tactic list failed validation or came back empty in most of 5 test calls per provider. I switched to plain text and took the structured fields from my own state machine. Sample size was tiny.
5. **Console encoding on Windows.** Replies sometimes contain non-breaking hyphens and spaces (for example U+2011 and U+202F), which crashed my logging on a Windows console. This was my bug, but the characters are easy to miss.

## Suggestions

- Document the thinking on/off control prominently on each reasoning model's page and in the chat completions reference, with an example request body.
- Return the reasoning token count separately in `usage`, or flag in the response when `finish_reason=length` was caused by reasoning, so empty replies are easier to diagnose.
- State the default reasoning behavior of each Nemotron model clearly, since it changes latency and cost by an order of magnitude for short outputs.
- Show example latency ranges for short prompts per model, with and without reasoning.

## NVIDIA Nemotron notes

- For a role-play task with a short, in-character reply, Nano was good enough once thinking was off. Replies stayed in character, reacted to what the player said, and did not need a larger model.
- I did not rely on a larger Nemotron model at runtime. In a small early test (6 calls), a larger model asked to write a structured debrief as JSON fell back half the time, so I replaced that step with deterministic content from authored scenario data.
