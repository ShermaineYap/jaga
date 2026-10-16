# Feedback on Nebius Token Factory, Nebius AI Cloud, Tavily and NVIDIA tools

> Required part of the submission (and eligible for the "Most Valuable Feedback" prize). Items
> marked **[verify]** are expectations from the docs — replace them with what actually happened
> on your machine as you build. Be specific: command, error text, minutes lost, workaround.

## Nebius Token Factory

**What we used it for.** All inference: Nemotron 3.5 Lightning (triage, thinking off, JSON schema),
Nemotron 3 Super (plan + verdict, thinking on, budgeted), Nemotron 3 Ultra (escalation). Batch API
for the 300-message evaluation sweep. `/v1/models` for a startup health check.

**What worked.**
- OpenAI-compatible API meant the whole client is ~150 lines; structured output with a Pydantic
  JSON schema returned valid objects on **[verify: n/300]** of triage calls.
- Pricing: at Lightning's $0.06/$0.24 per 1M tokens the per-message cost is effectively zero; the
  full three-tier pipeline measured **$[fill] per 1,000 messages**.
- **[verify]** `chat_template_kwargs: {"enable_thinking": false}` passed through the API as documented.

**What needs work.**
- **No spend cap or balance alert.** HTTP 402 arrives mid-request. We had to build a "paused"
  state and a cached-verdict fallback. A soft limit + webhook would remove that whole code path.
- **Model ID stability.** We could not find a guarantee that Nemotron 3 IDs stay stable through
  the judging window, so IDs live in `.env` with fallback chains. A deprecation header or a
  `/v1/models?include=deprecations` field would let clients degrade gracefully.
- **Multimodal gap.** Nemotron 3 Nano Omni and Cosmos3-Super-Reasoner were removed from serverless
  on 31 Aug 2026 with no replacement NVIDIA vision/audio model, and there is no speech product. For a
  Personal AI assistant that is the single biggest missing piece — voice notes are how seniors
  actually forward things.
- **Fine-tuning.** The marketing page says Nemotron can be fine-tuned serverlessly; the post-training
  docs' base-model list has no Nemotron. One or the other should change.
- **Credits.** Promo credit expires **[verify: date]**; the Builders credit expires 90 days after
  issue, which is before the Dec 1–15 judging window. A hackathon-specific expiry aligned to the
  judging window would help every entrant.
- Malay: Nemotron's documented languages exclude Malay. On a 500-question MalayMMLU subset we
  measured Lightning **[fill]%** / Super **[fill]%**; on ScamBench-MY the BM-language F1 was
  **[fill]** vs English **[fill]**. **[verify and describe]**

**Zero to hello-world:** **[fill]** minutes (sign-up → card → promo code → first Nemotron call).
**Would we build with it again?** Yes — for text. We would need a speech/vision path on serverless
to ship Jaga's next version on it.

## Nebius AI Cloud (Serverless Jobs / Endpoints / Devlabs)

**What we used it for.** **[fill: "A CPU VM to host the OpenShell/Hermes box" / "Not used — the
rules allow Token Factory-only, and AI Cloud needs a separate $25 top-up with no free trial"]**.
**Feedback.** Separate billing from Token Factory and no trial made it hard to justify for a
text-only agent. If Cosmos Reason 2 were a one-click Serverless Endpoint with a documented cold-start
time and per-request pricing, we would have used it for screenshots.

## Tavily

**What we used it for.** Search with `include_domains` restricted to SC / PDRM / BNM / MCMC / NSRC;
`topic=news` with `days` for recent scam reports; Extract to pull the alert page as evidence; Map +
Extract on a nightly cron into a local cache.
**What worked.** `include_domains` + `include_raw_content` made "cite the authority page" trivial.
Free tier (1,000 credits/month) covered development.
**What needs work.** **[verify]** Coverage of Malaysian government pages (SC investor alert list is a
long paginated table; Semak Mule is a form-driven lookup) — describe what Search/Extract returned
and whether Map found the pages. A first-class "official sources" domain pack per country would help.

## NVIDIA OpenShell / NemoClaw / Hermes Agent

**What we used it for.** Hermes Agent as the always-on agent (Telegram gateway, cron, skills),
onboarded into an OpenShell sandbox via `nemohermes`, inference routed to Token Factory, default-deny
network policy, OCSF audit.
**What worked / needs work.** **[fill from your run of hermes/setup_nemohermes.sh: install time,
sudo/CDI prompts, egress blocks for pip, policy schema mismatches, port-forward drops]**. The idea
that credentials never enter the sandbox is exactly right for a personal agent that reads private
messages; the docs should show one end-to-end example with a non-NVIDIA inference URL.

## NVIDIA Nemotron (models)

- Lightning's structured-output reliability and speed made it the right "every message" tier.
- Super's planning was **[verify: good / over-planned / under-planned]** at a 2.5k budget.
- Ultra was invoked on **[fill]%** of cases; it changed the verdict on **[fill]** of them.
- The reasoning toggle being a chat-template flag rather than a first-class API parameter is fine
  but should be documented on the Token Factory model page, not only on the HF card.
