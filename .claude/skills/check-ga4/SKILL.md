---
name: check-ga4
description: Use for site analytics, traffic, or visitor behaviour on voronkatm.com — visitors, sources, on-page behaviour, submits, аналитика сайта — for any period Operator names. Pair with /check-ads when a decision needs both ad delivery and on-site behaviour. Read-only.
---

## What this does

Pulls everything GA4 knows about **voronkatm.com** for a period Operator names, via the GA4 Data API. Read-only — queries only, writes nothing, changes nothing on the site or in Analytics.

Property `voronka.tm`, measurement ID `G-LVK4PKT4C2`, timezone Asia/Ashgabat (same as the Meta ad account, so the two line up day-for-day).

## Run this

```bash
cd "D:/ai projects/vaios/automations/ga4" && python report.py --days 7
```

Pick the window from what Operator actually said. Don't default to 7 if he named a period.

| he says | you run |
|---|---|
| "last 3 days" | `--days 3` |
| "this week", nothing | `--days 7` |
| "this month" | `--days 30` |
| "since the campaign launched" | `--from 2026-07-23` |
| a date range | `--from 2026-07-23 --to 2026-07-27` |
| "right now", "who's on the site" | `--realtime` |

Other flags:

- `--limit N` — more rows per table when a breakdown is truncated.
- `--list` — every dimension and metric **this** property offers, custom ones included. Use it when Operator asks for something the sweep doesn't print, then query it directly.
- `--dims A,B --metrics X,Y` — ad-hoc query for anything at all. Max 9 dims, 10 metrics per call.
- `--json` — machine-readable, for when you need to compute rather than read.

**If it errors on auth, IDs, or permissions, run `python verify.py`.** It checks the five setup steps in order and prints the exact fix for the one that broke. Don't debug by hand — `verify.py` already knows the failure modes.

## What the sweep covers

Totals (volume + engagement) · day-by-day · hour-of-day · every event with counts · acquisition by channel / source / medium / campaign / first-touch / referrer · landing pages · all page paths · page titles · country · region + city · device / OS / browser / resolution / phone model · new vs returning · language · age · gender.

If Operator wants something outside that, `--list` then `--dims/--metrics`. Never tell him GA4 doesn't have it without checking `--list` first.

## Read the output in this order

**1. `generate_lead` in the EVENTS table is the number that matters.** It is the LP's real-submit event — `trackLead()` in `app.js`, two call sites (hero form `app.js:161`, chat `app.js:576`), both gated behind a valid 8-digit phone tail. Same gate as the Meta pixel `Lead` event. Everything else is context for that number.

**2. Then the funnel shape.** Sessions → engaged sessions → `generate_lead`. Where the drop is tells you what to fix. A big sessions-to-lead gap is a page problem; few sessions against known ad clicks is a delivery/load problem.

**3. Then country.** Turkmenistan is VPN-heavy. Traffic showing up as Netherlands, Germany, or Turkey is almost certainly local users behind VPN exits, **not** wasted targeting. Never report scattered geography as a targeting failure without saying this.

**4. Then everything else** — device, hours, pages — as supporting detail only.

## Context you need to interpret it

- **GA4 is not truth either.** The Telegram bot and the Sheet CRM are truth for real заявки. GA4 and Meta are two independent estimates of the same reality; when they disagree, that gap is the finding, not an error to explain away.
- **The cross-check that matters:** Meta `link_click` → GA4 paid `sessions`. On test-01 about 45% of paid link clicks never became a landing page view. GA4 sizes that leak honestly from the site's own side. It is the cheapest available win in the funnel — fixing it multiplies traffic at zero extra ad spend.
- **`generate_lead` vs Meta `Lead` should track closely.** Same trigger, same gate. Divergence means one of the two tags is misfiring — worth chasing, and worth reconciling against the Telegram bot before believing either.
- **Data lags 24–48h.** Today's and yesterday's numbers still move. Don't call a trend off a partial day. `--realtime` is a separate 30-minute surface, unrelated to the reports.
- **Demographics get thresholded.** Age and gender go blank at low traffic because Google suppresses them to protect individuals. Blank is expected here, not broken.
- **`(not set)` / `(direct)` / `(other)` are real GA4 values.** `(other)` means a cardinality limit bucketed the row. Say so rather than reporting it as missing data.
- **Instagram in-app browser** often shows as referral or direct rather than a clean paid source, because UTMs get stripped. Don't conclude "no paid traffic" from the source table alone — cross-check the totals against Meta's click count.
- **Dates are in the property timezone (Asia/Ashgabat, UTC+5)**, not UTC and not this machine's clock. Get real UTC time from the machine before reasoning about "today".

Full setup and gotchas: `automations/ga4/README.md`.

## Never do these

- Never edit the GA4 property, its events, audiences, or data streams. This toolkit is read-only by design and there is no reason to change that.
- Never touch the LP's tracking code as a "fix" during a live campaign — a tag change mid-flight makes the whole window uncomparable.
- Never commit `automations/google-service-account.json` or `.env`. Both are gitignored; keep it that way.

## Report it like this

Lead with the one-line verdict — traffic up / flat / dead, and whether leads came through. Then the numbers that answer what he asked. Then what it means for the funnel.

Cut the tables he didn't ask for. The sweep prints ~20 sections; most sessions need three of them. Do not paste the whole dump back at him.

If he asked about ads too, run `/check-ads` as well and reconcile the two — Meta link clicks vs GA4 sessions, Meta Lead vs GA4 `generate_lead` — rather than reporting them as two separate stories.

If there's a finding worth keeping, log it in `funnel/03-landing-page.md` (site behaviour) or `funnel/02-meta-ad.md` (traffic quality) and suggest a decision-log entry.
