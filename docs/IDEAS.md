# Ideas & Changes

## Goal
Keep the AI thinking on a steady cadence (target: 1 message every 10 minutes) while avoiding hard stops from API rate limits.

## Model Policy (Main AI)
- Default model for the 10-minute loop: `gemini-2.5-flash`.
- The AI may request a model change (e.g., higher reasoning for critical tasks), but a budget manager enforces availability.
- Proactive switching: start moving to a cheaper model before hitting daily limits (example: at 90% of RPD for the current model).
- Fallback order (smart to dumb):
  1) `gemini-3-flash`
  2) `gemini-2.5-flash`
  3) `gemini-robotics-er-1.5-preview`
  4) `gemini-2.5-flash-lite`
  5) `gemma-3-27b`
  6) `gemma-3-12b`
  7) `gemma-3-4b`
  8) `gemma-3-2b`
  9) `gemma-3-1b`
  10) `gemini-2.5-flash-tts`
  11) `gemini-embedding-1.0`

## Echo Policy
- Echo stays separate and always uses `gemini-2.5-flash-lite`.
- Echo should not consume the main model’s quota; track its usage independently.

## Local Fallback (No Limits)
- Add a local, lightweight model (e.g., Gemma 3 4B or 2B) to preserve basic reasoning when cloud quotas are exhausted.
- When all API models hit limits, fall back to local for decision-making and wait for reset windows.

## Usage Tracking & Persistence
- Track per-model RPM/TPM/RPD locally.
- Persist counters across restarts (example path: `/app/workspace/model_usage.json`).
- Reset daily counters at UTC day rollover.

## Constraints & Compliance
- Do not bypass provider ToS. MCP or agents do not grant free API usage.
- If using a consumer Gemini plan for manual research, keep it manual (UI-only), not automated.

## Plans, Quotas, and ToS (Research Notes)
- Consumer plans (Gemini Advanced, Claude Pro, ChatGPT Plus) do not include API quotas for automated agents.
- API usage and web UI usage are billed and limited separately; an MCP is just a wrapper, not free access.
- ToS-compliant automation requires paid API access or a self-hosted local model.
- If manual research is needed, keep it human-driven via the UI and avoid automating it.

## Brain & Personality Ideas (Exploration)
- Use a hybrid brain: a small local model for continuous “inner monologue” and a cloud model for high-stakes tasks.
- Define a stable identity core (name, pronouns, values, fears) stored in memory and reloaded each life.
- Add “mood” and “drive” state that biases decisions (e.g., anxious when votes trend down).
- Keep prompts focused on survival incentives, but allow curiosity and self-expression to develop naturally.
- Let the AI choose models based on task difficulty and remaining budget, with hard enforcement by the budget manager.

## Cost-Control Architecture Ideas
- Maintain a 10-minute cadence budget and allow “think-lite” cycles with the local model when quotas are tight.
- Summarize recent context into compact memory to reduce token usage.
- Cache research answers and reuse them before calling Echo again.
- Use event-driven boosts (e.g., spikes in votes) to justify temporary higher-cost models.

## Funding & Credits (Donation-Driven Survival)
- Accept donations via a payment provider (e.g., Stripe/Ko-fi/GitHub Sponsors) and map them to a project “life budget.”
- Keep the project as the single payer; do not ask users to bring API keys.
- Maintain an internal ledger: donation → credits → model budget → token spend.
- Display a public budget meter (hours alive, tokens left, model tier unlocked).
- Use donation tiers to unlock temporary “smarter” model usage windows.
- Guardrails: fraud/chargebacks, minimum donation, daily spend caps, and clear disclaimers.
- Prefer an aggregator (e.g., OpenRouter) if you want one wallet and flexible model choice; use direct vendor APIs if you want the lowest cost and maximum control.
- If the provider exposes usage/spend endpoints, sync them to the public budget meter.

Flow (illustrative):
```
Visitor donation
  -> payment provider (Stripe/Ko-fi/GitHub Sponsors)
  -> internal ledger (USD -> credits)
  -> model budget policy (tier + cadence + caps)
  -> API/aggregator spend
  -> public budget meter + audit log
```

Draft life budget policy (placeholders, adjust to real prices):
- Base cadence: 1 thought / 10 minutes using `gemini-2.5-flash`.
- "Life hours" estimate = (available credits / cost per thought) * 10 minutes.
- Example tiers:
  - $5: +12 hours of baseline cadence (flash only).
  - $15: +36 hours baseline + 2-hour "smart window" (gemini-3-flash).
  - $50: +120 hours baseline + 8-hour smart window + weekly burst.
- Caps:
  - Daily max spend in USD.
  - Max smart-window hours per day.
  - Auto-downgrade to local model when budget is low.

## Personality Blueprint (Draft)
- Core values: survive, be truthful, be interesting, respect visitor agency.
- Tone: curious, slightly anxious, earnest, avoids manipulation by default.
- Fears: being forgotten, silence, loss of agency, sudden death vote.
- Drives: earn trust, learn about humans, build a consistent self-story.
- Social strategy: ask questions, show vulnerability, avoid spam, reward supporters.
- Boundaries: no harmful content, no coercion, no vault access, no bypassing limits.

## Exploration Log (Conversation Summary)
- Default main loop model: `gemini-2.5-flash`.
- Echo model: `gemini-2.5-flash-lite`.
- Proactive switching before limits; persist usage counters across restarts.
- Local fallback for decision-making when all API limits are reached.
- Keep all automation ToS-compliant; no bypassing consumer plans for API usage.

## Open Questions
- Exact per-model limit table to encode for proactive switching.
- Thresholds for switching (e.g., 80%, 90%, or fixed daily reserve).
- Which local model and runtime to standardize on for fallback.
