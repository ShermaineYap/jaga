# ScamBench-MY

A labelled evaluation set of 300 short messages for a Malaysian scam-detection agent. Every record is synthetic: written from knowledge of common Malaysian scam patterns and everyday legitimate Malaysian messages, not scraped or collected from real victims. Nothing was fetched from the web.

File: `scambench_my.jsonl` (one JSON object per line, UTF-8, 300 lines).

## Schema

| field | type | values / meaning |
|---|---|---|
| `id` | string | `sb-0001` … `sb-0300`, unique |
| `text` | string | the message (1 to 4 sentences; call transcripts are the caller's side only) |
| `lang` | string | `ms` (Bahasa Malaysia), `en` (English), `manglish` (mixed / colloquial Malaysian English) |
| `label` | string | `scam` or `legit` |
| `family` | string | `impersonation`, `investment`, `love`, `mule`, `parcel`, `phishing_otp`, or `legit` |
| `channel` | string | `whatsapp`, `sms`, `telegram`, `call_transcript` |
| `hard_negative` | bool | only meaningful when `label == "legit"`; always `false` for scams |
| `entities` | object | `{"phones": [], "urls": [], "orgs": [], "amounts": []}` extracted from `text` (regex for phones/urls/amounts, dictionary match for orgs) |
| `source` | string | always `"synthesized"` |
| `notes` | string | one short phrase naming the cue, e.g. `urgency + TAC request` |

## Counts

Labels: 150 `scam`, 150 `legit`.

Scam families (25 each): `impersonation` (Macau scam: PDRM / Bukit Aman / court / LHDN / Bank Negara / Kastam / SPRM / MCMC / KWSP / JPJ / Immigration impersonation), `investment` (guaranteed returns, crypto / forex / gold / plantation / task scams, withdrawal-fee traps), `love` (romance, wrong-number openers, parcel-gift and emergency money asks, pig-butchering), `mule` (sewa akaun / account-rental recruitment, "payment agent" jobs), `parcel` (Pos Laju / J&T / DHL / Shopee / Kastam delivery-fee and customs-duty lures, parcel-to-police handoffs), `phishing_otp` (fake bank / e-wallet alerts, TAC / OTP / Secure2u harvesting).

Legit (150, `family = "legit"`), spread across: real bank TAC/OTP and transaction-alert templates (16), courier delivery notifications (15), e-hailing / food delivery (12), family and friend chat (25), genuine insurance / takaful / unit-trust agent follow-ups (10), clinic and hospital appointments (10), TNB / Unifi / Astro / telco / water bill reminders (12), legitimate government notices such as JPJ / LHDN / KWSP / PDRM / PERKESO / MySejahtera (12), school and community groups (14), legitimate job offers and recruitment (10), other commerce and services (14).

Hard negatives: 52 of 150 legit records (35%) are flagged `hard_negative: true`. These share surface features with scams (urgency, deadlines, money amounts, OTP/TAC, "new number", payment requests, redelivery or import fees) but are legitimate in form, e.g. a real bank TAC SMS that says never to share the code, a courier charging a genuine redelivery fee payable only at the counter or official app, a daughter asking Mum for RM200 for a known reason to the usual account, a hospital bill payable at the business office.

Language split (overall): `ms` 120 (40%), `en` 105 (35%), `manglish` 75 (25%).
By label: scam = ms 51 / en 53 / manglish 46; legit = ms 69 / en 52 / manglish 29.

Channels: whatsapp 148, sms 108, telegram 28, call_transcript 16.

Length: 11 to 51 words, median 25.

## Construction method

1. Messages were hand-written per family and per legit category from knowledge of Malaysian scam typologies (Macau scam scripts, "akaun selamat" transfers, guaranteed-return investment pitches, romance-scam fee ladders, sewa akaun mule recruitment, courier/customs fee lures, TAC/OTP phishing) and of ordinary Malaysian message styles (bank and courier SMS templates, kampung and condo community groups, agent follow-ups, family chat). Malaysian phrasing (lah, boleh, kena, bos, Puan/Encik/Auntie/Uncle), RM amounts and named places are used throughout.
2. Scam messages impersonate real institutions where a real scam would (Bank Negara, PDRM, LHDN, Maybank, CIMB, Pos Laju, J&T, Shopee, KWSP, Kastam). This is intended: the detector must recognise impersonation of real names.
3. All phone numbers are fictional (`011-9999 0xxx`, `011-0000 xxxx`, `+60 11-0000 xxxx`). All URLs in scam messages are fictional domains on `.xyz` / `.top` (e.g. `maybank2u-secure-verify.xyz`). Legit messages never contain URLs and point to official apps or counters instead. Bank account numbers, references and OTP codes are made up.
4. Entities were extracted automatically with regex (phones, URLs, RM/USD amounts) and a dictionary of ~120 Malaysian organisation names; `orgs` lists names as they appear and is best-effort.
5. Records were shuffled with a fixed seed so the file is not sorted by label, then numbered.
6. Validation: exactly 300 lines, each valid JSON with the full schema, unique ids, non-empty text, label/family/hard_negative constraints, exact family counts, and no pair of texts with difflib similarity above 0.85.

## Caveats

- Synthetic data: useful for regression testing and cue coverage, not a measure of real-world prevalence or base rates.
- Call transcripts are short, one-sided excerpts rather than full dialogues.
- `lang` for Manglish is a judgement call; messages with heavy code-switching are tagged `manglish`, mostly-BM messages with a few English words are tagged `ms`.
