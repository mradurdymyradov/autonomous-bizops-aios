# 02 — Meta ad

**Stage:** paid traffic — the engine that fills the funnel. Drives cold local traffic → LP. Must match [00-core.md](00-core.md).

**Status: LIVE and delivering.** Campaign `voronka-test-01` launched 2026-07-23 23:00 UTC. First real spend and first reported leads — see [Test-01 live results](#test-01--live-results-2026-07-24) below.

---

## Decided

- **Platform:** Meta Ads Manager, our own **master ad account** (clients later prepay budget in cash → our cards).
- **Budget for the first test:** ~$25 (borrowable). Low CPMs in TKM make this go far.
- **Destination:** our own LP (voronkatm.com), CTA = free 10-min audit. Driving to our own page filters low-intent leads and doubles as a live demo.
- **Goal of the test:** book **one** free audit call — first real proof the funnel converts.

## Blockers before it can run

- [x] **Meta Pixel** on the LP — DONE. Pixel `1397681815558353` ("voronka dataset"), verified firing 2026-07-21.
- [ ] IG profile ad-ready (case-study post + highlights). See [01-instagram](01-instagram.md).
- [x] The ad creative itself — **DONE 2026-07-23.** Lineup for test-01: `ad-video.mp4` (hero — The AI video, 9:16 720×1280, hook «Инстаграм есть, а клиентов нет?» → system pitch → CTA «Подробнее») + statics `ad-b-proof.png`, `ad-c-flat.png` (batch-03, approved). `ad-a-pain.png` benched — its hook lives inside the video. Video vs static doubles as the B2B creative-format test for round 2. **Remaining gates: Lead pixel event on LP + IG profile ad-ready + hitting Publish.**

## API automation status (2026-07-22)

Auth is done: system user token (never expires), ad account ACTIVE with card on file,
Page + IG + pixel all reachable. Tooling built at `automations/meta-ads/`.

**But the API cannot create ad creatives yet** — app `automation_1` is unpublished,
and Meta blocks creative creation from a Development-mode app. Publishing needs
business verification, which needs legal documents.

**Do not wait on this.** Build the first $25 test by hand in Ads Manager. The gate
to revenue is traffic, not tooling. See `automations/meta-ads/README.md`.

## TBD (not yet decided — don't block, decide when building)

- ~~Creative format~~ — DECIDED 2026-07-23: **static images, 3 variants**, one ad set, Meta picks the winner.
  Video rejected at this budget: $23 can't test multiple video hooks, Veo 3.1 can't render Cyrillic,
  and character consistency drifts in video gen. Veo credits reserved for round 2: image-to-video
  the winning static. Prompts + Ads Manager copy: `funnel/batches/03-ad-creatives.md`
  (Antigravity generates, Operator uploads by hand).
- ~~Ad copy~~ — DECIDED: written in batch-03 §5 (Russian, «мы», hook = LP hero «Инстаграм есть, а клиентов нет?»).
- Targeting (geo = TKM local; broad, no interest stacking on this budget — per batch-03 §5).
- ~~Objective~~ — RE-DECIDED 2026-07-23 (The call, overrides the earlier traffic decision):
  **Leads objective, website conversion, optimize for the Lead pixel event.** Targeting:
  **Ahal region only, age 23–43.** Accepted tradeoff: cold pixel → ad set will stay
  learning-limited on $23; fine, Ahal CPMs are low and leads-goal points spend at
  converters even while learning. **Prerequisite:** LP must fire `fbq('track','Lead')`
  on phone submit (was PageView-only). Setup plan: `automations/meta-ads/campaign-setup-test-01.md`.

## Test-01 — live results (2026-07-24)

Pulled from the Marketing API at **2026-07-24 14:00 UTC**, ~15h into delivery. Read-only, nothing touched.

Campaign `voronka-test-01` (`120249782138050338`) — OUTCOME_LEADS, $6.00/day, ad set `ahal-broad-ig`
(Ahal region, 18–65 w/ age_range 23–43, Instagram placements only, OFFSITE_CONVERSIONS goal).
Schedule: 2026-07-23 23:00 → 2026-07-27 18:59 UTC. Account ACTIVE, Mastercard *6962 on file.

| ad | spend | impr | reach | freq | clicks | CPC | CTR | LPV | leads (Meta) | $/lead |
|---|---|---|---|---|---|---|---|---|---|---|
| ad-video | $4.37 | 3594 | 2860 | 1.26 | 109 | $0.040 | 3.03% | 26 | 16 | $0.27 |
| ad-c-flat | $1.50 | 1136 | 969 | 1.17 | 37 | $0.041 | 3.26% | 15 | 4 | $0.38 |
| ad-b-proof | PAUSED — never delivered | | | | | | | | | |
| **total** | **$5.87** | **4730** | **3502** | | **146** | **$0.040** | **3.09%** | **41** | **20** | **$0.29** |

Video depth (ad-video): 865 views, 521 hit 25%, 122 watched to 100%. Outbound clicks 54 (47 unique)
vs 30 (26 unique) for ad-c-flat.

**Reading it:**
- Ads passed review — both live ads `ACTIVE`, no `issues_info`, no `ad_review_feedback`.
- Spending the full $6/day cap. CTR ~3% and CPC $0.04 are strong; Ahal CPMs are as cheap as assumed.
- **ad-video is the winner so far** — 4× the leads of the flat static at ~the same CPC, and it holds
  attention (14% of viewers watch to 100%). The round-2 "image-to-video the winning static" plan is
  already answered: video won on the first try.
- The learning-limited worry from the objective decision did **not** block delivery.

**The pixel is not misfiring.** Checked the LP source: `trackLead()` (`app.js:39`) has exactly two
call sites — `app.js:161` (hero form) and `app.js:576` (chat), both gated behind a valid 8-digit
phone tail and both POSTing `type:'lead'` to the backend. So every `Lead` event should equal one real
phone number in Telegram **and** one row in the Sheet. Raw pixel events: 2026-07-23 → 57 PageView /
4 Lead; 2026-07-24 → 60 PageView / 18 Lead.

**VERIFIED AGAINST TRUTH (2026-07-24).** Operator had **18 real phone contacts** on his phone — a couple
of duplicate submits, a couple his own test leads, so **~16 genuine заявки**. The pixel count (18)
matched reality almost exactly, which retires the "is the pixel lying" question: **for this LP, the
Meta lead count is trustworthy.** Capture chain (LP → `api/lead.js` → Telegram → Sheet) confirmed
working under real load, not just smoke tests.

**He called all of them. Result: 2 clients signed for the free pilot test.**

Real economics of test-01: **$5.87 → ~16 заявки → 2 closed pilots.** ≈ **$0.37 per real заявка**,
≈ **$2.94 of ad spend per closed client.** The $2-CAC proof point from a previous life now has a
local, first-party replacement.

**Test-01 verdict: goal was "book one audit call." It booked ~16 and closed 2. Objective cleared.**

**Tooling bug found:** `report.py --days N` uses backward date presets (`last_7d` etc.) which **exclude
today**. The campaign's entire life is "today" in Asia/Ashgabat, so the default run printed
`no delivery in window` while $5.87 had actually been spent. Fix `report.py` to use `maximum` or to
add today's partial day before trusting it again.

## Test-01 — Day 1 final + Day 2 open (2026-07-25)

Pulled from the Marketing API at **2026-07-24 22:29 UTC** (= 2026-07-25 03:29 Asia/Ashgabat), ~28.5h
into delivery. Read-only, nothing touched. The 14:00-UTC table above was a mid-day snapshot; these
are the **closed Day-1 totals**.

**Day 1 complete — 2026-07-24 local day (the full first 24h):**

| ad | spend | impr | clicks | CPC | LPV | leads (Meta) | $/lead |
|---|---|---|---|---|---|---|---|
| ad-video | $5.48 | 4314 | 139 | $0.039 | 33 | 17 | $0.32 |
| ad-c-flat | $1.50 | 1137 | 38 | $0.039 | 15 | 4 | $0.38 |
| ad-b-proof | PAUSED — never delivered | | | | | | |
| **total** | **$6.98** | **5451** | **177** | **$0.039** | **48** | **21** | **$0.33** |

Reach 3948, frequency 1.38, CTR 3.25%, link clicks 97.

**Day 2 partial (2026-07-25, first ~3.5h):** $1.50 · 1133 impr · 28 clicks · 8 LPV · 1 lead.
Lifetime spend **$8.48**. (Account `amount_spent` still reports $6.98 — that field lags.)

**Reading it:**
- Both live ads remain `ACTIVE`. No `issues_info`, no `ad_review_feedback`. Nothing broken.
- **Meta has consolidated the budget into ad-video.** On Day 2 `ad-c-flat` received $0.01 and one
  impression. Delivery itself has now picked the winner — the "round 2 = video" call is confirmed
  by spend allocation, not just by lead ratio.
- $6.98 against a $6.00/day cap is standard Meta overdelivery (balances across the week), not a leak.
- ~~**Biggest leak is link click → landing page view: 97 → 48, ~50% loss.**~~ **Wrong — corrected
  2026-07-28. There is no traffic leak.** GA4 recorded **271** Paid Social sessions for campaign
  `test01` against Meta's **264** link clicks over the same window: *more* sessions than clicks.
  The clicks arrived and the pages loaded. What undercounts is Meta's `landing_page_view` pixel
  event, ~44% low, almost certainly the IG in-app browser dropping the pixel while the GA4 tag
  survives. See [decisions/log.md](../decisions/log.md) 2026-07-28. Nothing to fix on the LP.
- LPV → lead is 21/48 = 44%, unusually high. Day-1 pixel-vs-phone reconciliation held up before, but
  re-verify against Telegram + the Sheet before treating 21 as 21 real заявки.

**Standing rule in force:** launched 2026-07-23 23:00 UTC → **do not touch until 2026-07-26 23:00 UTC**.
Campaign self-terminates 2026-07-27 18:59 UTC regardless.

**Tooling note:** `report.py --days 1` is not supported — it silently falls back to `last_30d`. The
`--days N` preset bug logged on 2026-07-24 is still unfixed. Use `date_preset=maximum` with
`time_increment=1` via a direct Graph call for day-by-day truth until it's patched.

## Test-01 — Day 2 final (2026-07-26)

Pulled from the Marketing API at **2026-07-25 22:32 UTC** (= 2026-07-26 03:32 Asia/Ashgabat), ~47.5h
into delivery. Read-only, nothing touched. Day 2 (2026-07-25 local) is now closed; Day 3 is ~3.5h old
with no data yet.

**Day 2 complete — 2026-07-25 local day:**

| ad | spend | impr | clicks | CPC | CTR | link clicks | LPV | leads (Meta) | $/lead |
|---|---|---|---|---|---|---|---|---|---|
| ad-video | $2.79 | 2097 | 61 | $0.046 | 2.91% | 43 | 28 | 9 | $0.31 |
| ad-c-flat | $1.01 | 735 | 19 | $0.053 | 2.59% | 10 | 6 | 2 | $0.51 |
| ad-b-proof | PAUSED — never delivered | | | | | | | | |
| **total** | **$3.80** | **2832** | **80** | **$0.048** | **2.82%** | **53** | **34** | **11** | **$0.35** |

**Lifetime (2 days):** $10.79 · 8286 impr · 5203 reach · 257 clicks · CPC $0.042 · CTR 3.10% ·
150 link clicks · 82 LPV · **32 Meta leads** · $0.34/lead. ad-video $8.28 / 26 leads,
ad-c-flat $2.51 / 6 leads.

**Reading it:**
- Both live ads still `ACTIVE`. No `issues_info`, no review flags. Nothing broken.
- **Efficiency held, volume dropped.** $/lead barely moved ($0.33 → $0.35). Leads halved (21 → 11)
  because *spend* halved ($6.99 → $3.80) — Meta delivered well under the $6/day cap on Day 2.
  On an Ahal-only, IG-only, 23–43 audience that reads as the pool thinning, not a broken ad.
- **The click→page leak improved on its own:** 53 link clicks → 34 LPV = 64% on Day 2, vs ~50% on
  Day 1. Lifetime 150 → 82 = 55%. Still the single biggest free win in the funnel.
- ad-video is still the winner but the gap narrowed on cost/lead ($0.31 vs $0.51). Meta did **not**
  fully consolidate into video the way the Day-2-partial snapshot suggested — c-flat took $1.01.
- **11 Day-2 Meta leads are unverified.** Day 1 reconciled almost exactly (18 pixel → ~16 real).
  Check Telegram + the Sheet before treating 11 as 11 real заявки.

**Standing rule still in force:** no-touch until 2026-07-26 23:00 UTC. Campaign self-terminates
2026-07-27 18:59 UTC — roughly 20h later. Leaving it alone is now the same as letting it finish.

## Consistency notes

- Ad hook should echo the LP hero pain-first angle so the click→page feels continuous.
- No price in the ad. No banned jargon. Russian, agency voice.
- **`landing_page_view` is not a usable metric on this account.** It reads ~44% low against GA4
  (2026-07-28 reconciliation). Never optimise a campaign for LPV, never quote an LPV-derived
  conversion rate, and never read a click→LPV drop as a leak. Meta's `link_click` is the honest
  Meta-side number; GA4 sessions are the honest page-side one.
- **The `Lead` event, by contrast, is sound — 60 Meta vs 61 in the Sheet for test-01.** The same
  pixel drops ~44% of LPV and ~0% of Lead, because LPV fires on load (before the IG in-app browser
  has the pixel up) and Lead fires after the visitor has stayed and interacted. Keep
  `OFFSITE_CONVERSIONS` as the optimisation goal; it was never the broken part.

## Next action

1. **Lock pilot terms with both clients before Day 1 of either build** — $50 cash, agreed N, $500 same day on hit. Terms in [00-core](00-core.md) §Terms. Nothing else matters until this is done.
2. **Triage the other ~14 leads** — they're not dead, they're pilot slot 3 and the standard-tier ($250/$250) pipeline. Log outcomes in «Звонки» before they go cold.
3. **Leave the campaign alone.** It self-terminates 2026-07-27 18:59 UTC. Let it run out rather than editing.
4. **Round 2 is already decided by the data:** video beat static 4:1. Build the next creative batch as video.
