# Feedback on Nebius Token Factory, Tavily, NVIDIA Nemotron and NVIDIA OpenShell

Written from building Jaga between 16 and 30 October 2026, solo, on a $25 Token Factory balance.
Every item below happened in this build; commands and symptoms are exact. Numbers come from
`eval/results/RESULTS.md`.

---

## 1. Nebius Token Factory

**What we used.** All inference: Nemotron 3.5 Lightning (triage, thinking off), Nemotron 3 Super
(planning + verdict, thinking on with a client-side budget), Nemotron 3 Ultra (escalation), Nemotron
3.5 Super VL (screenshots). JSON-schema structured output on every call. `/v1/models` as a startup
health check. ~1,800 evaluation cases over the build.

**Zero to first Nemotron call: ~4 minutes.** Google sign-in → organisation auto-created → billing
already active with a $25 balance plus a $1 / 6-day trial → *Get API key* → OpenAI SDK with
`base_url=https://api.tokenfactory.nebius.com/v1/`. Smoothest onboarding of any provider we used.

**What worked**
- Price/performance: the full three-tier pipeline costs **$[fill]/1,000 messages**; the Malay smoke
  test (20 messages × 2 models) cost **$0.0044**.
- `chat_template_kwargs: {"enable_thinking": false}` passes through and works on Lightning/Super;
  Super returns its reasoning separately in `reasoning_content`, so content stays clean JSON.
- Bahasa Malaysia: although Malay is not in Nemotron's documented languages, Lightning and Super each
  classified **18/20** Malay/Manglish scam and legit messages correctly on day one.
- Nemotron 3.5 Super VL transcribed a WhatsApp scam screenshot near-verbatim and spontaneously
  flagged "display name 'Maybank Customer Care' on a personal +60 11 number" as a red flag.

**What needs work (most valuable first)**
1. **Guided decoding silently drops optional fields.** With `response_format: json_schema`, any
   property that has a default (i.e. is not in `required`) was omitted by Lightning on almost every
   call: our `entities` lists came back empty, so nothing was ever verified. Root cause took ~40 min.
   Fix on our side: rewrite every schema so all properties are `required` (`jaga/llm.py:strict_schema`).
   *Ask:* document this prominently, or emit a warning when a schema has optional properties.
2. **Repetition loops inside list fields.** Lightning sometimes emits `"persons": ["u", "u", "u", …]`
   until `max_tokens`, producing invalid JSON (~1 in 12 calls in our first sweep). `maxItems` in the
   schema plus `frequency_penalty=0.3` removed it (0 failures in 48 calls after). *Ask:* enforce
   `maxItems`/`maxLength` in the guided decoder, and mention the failure mode in the model card.
3. **Inconsistent model-ID casing in one family.** `nvidia/nemotron-3-super-120b-a12b` (lowercase) vs
   `nvidia/Nemotron-3-Ultra-550b-a55b` vs `nvidia/Nemotron-3_5-Lightning` (underscore) vs
   `nvidia/Nemotron-3.5-Super-VL` (dot) vs `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. We guessed the
   Ultra ID wrong and our fallback silently routed escalations to Super until `/v1/models` showed it.
   *Ask:* case-insensitive model lookup, or aliases.
4. **Vision + `json_object` mode returns the schema shape.** With `response_format: json_object` and
   the schema pasted into the prompt, Super VL returned `{"description": …, "properties": {…answer…}}`.
   `json_schema` mode fixed it.
5. **No spend cap or low-balance alert.** HTTP 402 arrives mid-request; we built a "paused" state.
   A soft cap + email/webhook would help every hackathon entrant keep demos alive to Dec 15.
6. **Deprecations.** Nemotron 3 Nano Omni and Cosmos3-Super-Reasoner left serverless on 31 Aug 2026;
   the Nemotron marketing page still listed Nano Omni when we started. The new Super VL filled the
   vision gap for us, but there is still **no speech model**, and voice notes are how Malaysian seniors
   actually forward things. A `deprecations` field on `/v1/models` would let clients degrade gracefully.
7. **Fine-tuning claim mismatch.** The Nemotron product page advertises serverless fine-tuning;
   the post-training docs' base-model list contains no Nemotron.

**Would we build on it again?** Yes. The three-tier Nemotron routing is only economical because of
Token Factory's prices, and onboarding was effortless.

## 2. Nebius AI Cloud (Serverless / DevPods)

**Not used.** The rules allow Token Factory-only, AI Cloud is billed separately, has no trial and
needs a $25 top-up. For a text/vision agent that calls hosted Nemotron, there was nothing to run on a
GPU. If a one-click Serverless Endpoint template existed for "Hermes Agent + OpenShell gateway" with
per-second CPU pricing, we would have hosted the whole agent on Nebius.

## 3. Tavily

**What we used.** `/search` with `include_domains` (SC, PDRM, BNM, MCMC, NSRC) and
`include_raw_content`; `/search` with `topic=news`; `/extract` to read alert pages; `/map` for the
nightly cache. ~[fill] credits over the build.

**What worked**
- **Freshness is real:** "RRJ Pro" was added to the Securities Commission Investor Alert List on
  15 Oct 2026; one day later Tavily returned that exact announcement page, and Jaga cites it with the
  matching sentence. No model could know this from training data.
- `include_domains` makes "cite an authority, never a blog" a one-line guarantee.
- The hackathon coupon `BBDEVPOST` added **8,000 credits** instantly; onboarding took ~2 minutes.

**What needs work**
- The entity sits deep in SC announcement pages, below site navigation. Snippets rarely contain it,
  so a relevance check needs `raw_content` (we read up to 40k chars). A "highlight the query terms"
  field in each result would save bandwidth and make citations easy.
- Search recall depended on wording: `"RRJ Pro" scam investor alert` found the page in some runs and
  not others. We now always add one canonical query per entity. A country "official sources" preset
  (e.g. `region=MY, source_type=regulator`) would be valuable.
- PDRM Semak Mule is a form-driven lookup that search cannot reach; an Extract mode for simple GET
  forms would close that gap.

## 4. NVIDIA OpenShell / NemoClaw / Hermes Agent

[fill from hermes/OPENSHELL_RUN.md — friction log]

## 5. NVIDIA Nemotron (models)

- Tiering works and the evaluation shows why: Lightning alone recalls [fill]% of scams but flags
  [fill]% of legitimate messages; adding Super planning + Tavily verification brings false positives
  to [fill]% at [fill] cost. Ultra was invoked on [fill]% of cases.
- Super with reasoning on follows rules literally: told "never plan a check for an entity not in the
  triage", it planned *zero* checks when triage had missed the entity. Instructions need to be phrased
  as goals, with code-level floors underneath.
- The reasoning toggle being a chat-template flag rather than an API parameter is fine, but it should
  be on the Token Factory model page, not only the Hugging Face card.
