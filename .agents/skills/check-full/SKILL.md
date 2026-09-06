---
name: check-full
description: Use when Operator wants the whole picture at once rather than one surface — "how are we doing", "full report", "check everything", "where are we", "run all the checks", "как дела с воронкой", "покажи всё", "общая картина" — or at the start of a session that needs current numbers before deciding anything. Runs every reader, stores the result, and prints one end-to-end funnel. Also the weekly capture that stops data expiring.
---

## What this does

Two steps, one picture.

1. **`snapshot.py`** hits all five readers (Meta, GA4, CRM, Instagram, Cloudflare), folds them into
   one row per Ashgabat date, and **writes them to disk**. This is the only script in the repo whose
   value decays if it isn't run — IG insights cap at 30 days, story insights die at 24h, GA4
   backfills ~48h then freezes. Unsnapshotted days are gone permanently.
2. **`funnel.py`** reads those stored rows and prints the funnel end to end. No API, no VPN.

Every API call is read-only. The only writes are the snapshot files.

## Run this

```bash
cd "D:/ai projects/vaios/automations" && python snapshot.py --days 14 && python funnel.py --days 14
```

| he says | you run |
|---|---|
| "how are we doing", nothing | `--days 14` on both |
| "this month" | `--days 30` |
| "since the campaign launched" | `snapshot.py --days 30` then `funnel.py --from 2026-07-23` |
| "which ad is working" | add `--creatives` to `funnel.py` |
| already snapshotted today | **skip `snapshot.py`** — `funnel.py` alone is instant and needs no network |

Other flags: `snapshot.py --dry-run` (print, write nothing) · `--only meta,crm` · `--skip ig` ·
`--force` (rewrite rows already frozen) · `funnel.py --json`.

**A reader that fails does not kill the run.** Its fields become `null`, never `0`, and both scripts
say which one broke. On a 2–4 Mb/s VPN a failure is usually the tunnel — re-run, rows upsert.

## Read the output in this order

**1. The verdict line and `REAL LEADS (truth)`.** The CRM count is the only number that pays.
Everything above it in the funnel is an estimate of something upstream.

**2. The stage that lost the most.** The funnel prints a percentage between each pair. Read where it
collapses, not the absolute numbers.

**3. ALARMS.** `/api/lead` errors are the one thing here that is invisible everywhere else — a
failed invocation is a submit that reached the server and may have reached neither Telegram nor the
Sheet. Non-zero means go count rows in `/check-crm` for the same window.

**4. DATA HEALTH, before quoting anything as a trend.** Rows stay mutable for 3 days because GA4
backfills and Meta insights lag. The moving edge is not a trend.

## Context you need to interpret it

- **Arrival sits near 100%, and that is settled.** Paid sessions ≈ paid link clicks (275 vs 265 over
  the launch window). The old "~45% of clicks never arrive" theory was closed 2026-07-28
  ([decisions/log.md](../../decisions/log.md)). If arrival reads near 100%, say nothing about it. If
  it collapses, *that* is new and worth chasing.
- **Page conversion is computed on ALL sessions, not just paid** — `generate_lead` isn't split by
  channel in the stored row. During a campaign paid dominates so it's close, but say "roughly" and
  don't quote it to a decimal when organic traffic is a meaningful share.
- **The three counts should stay close.** Meta-reported, GA4 `generate_lead`, and CRM real leads
  measure the same reality with different tags. A stable spread is normal; a *widening* one means a
  tag is misfiring. Do not "fix" a divergence by trusting the bigger number.
- **`landing_page_view` and Cloudflare `pageViews` are deliberately absent from this funnel.** The
  first runs ~44% low (IG in-app browser drops the pixel), the second is ~7× bot-inflated on the Free
  plan. Both are stored, neither is ever a denominator. Standing rules in
  [funnel/02-meta-ad.md](../../funnel/02-meta-ad.md) and the `/check-cf` skill.
- **GA4 key events being unconfigured does NOT invalidate these rates.** The funnel computes them
  from raw event counts, which work. It only means GA4's own built-in conversion metrics read 0
  inside the GA4 UI. Don't report the funnel as broken because of it — report the one-minute fix.
- **`ig.followers` is capture-time, not date-time**, stamped onto every row in the window. Instagram
  gates daily `follower_count` until ~100 followers. Never chart it as growth.
- **Cloudflare is UTC; everything else is Ashgabat (UTC+5).** Day boundaries sit 5 hours apart, which
  is why CF contributes alarms rather than funnel stages.

Row shape and where every field comes from: [automations/snapshot-schema.md](../../automations/snapshot-schema.md).

## Never do these

- Never quote numbers from `STATE.md` — run this instead. That is what it's for.
- Never report a null as a zero. "The IG reader timed out" and "reach was zero" are different
  findings, and both scripts already distinguish them.
- Never call a trend off the last three days. They are still moving by design.
- Never `--force` to "clean up" old rows. Frozen rows are the historical record; rewriting them with
  data the APIs have since aged out destroys the series this whole system exists to build.

## Report it like this

Lead with the verdict line and cost per real lead. Then the one stage that lost the most, and what it
implies. Then alarms, only if any are live.

**Do not paste the dump.** It prints five sections; most questions need two. Cut the rest.

Tie it to the open loops in [STATE.md](../../STATE.md) — leads that exist but were never called are
worth more than any number in this report. If the numbers moved the picture, say so and suggest
running `/state-check` rather than editing `STATE.md` mid-conversation.
