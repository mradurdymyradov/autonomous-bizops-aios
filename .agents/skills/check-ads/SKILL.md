---
name: check-ads
description: Use when Operator asks about the live Meta/Instagram ad campaign — "how's the campaign", "check my ads", "did it spend anything", "any leads yet", "what's the CPC", "как реклама", "сколько потратили" — or when any funnel decision needs current ad numbers. Read-only.
---

## What this does

Reads the live state of the **voronka.tm** Meta ad account via the Marketing API and reports it in plain terms. Creates nothing, edits nothing, never starts or stops spend.

## Run this

```bash
cd "D:/ai projects/vaios/automations/meta-ads" && python report.py --days 7
```

`--days 7|14|30|90` sets the insights window. `--all` includes archived/deleted objects.
`--who` adds audience breakdowns — age, gender, age×gender, placement, device, region — each ranked by
cost per reported lead. Today: !`date +%Y-%m-%d`

**`--who` is the only route to audience demographics we have.** The organic Instagram endpoints
withhold them until ~100 followers (the account has 29); the Marketing API doesn't care about follower
count. Run it whenever the question is *who* rather than *how much*. Meta's `lead` count isn't truth —
the bot and the Sheet are — but every slice is miscounted the same way, so the **ranking between
slices** holds even when the absolute numbers don't.

Auth is a never-expiring system-user token in `automations/meta-ads/.env`. If the script errors on auth or IDs, run `python verify.py` — it fails loudly on the exact broken line.

For anything `report.py` doesn't print, call the Graph API directly by importing its helpers:

```bash
python -c "import report as R,json; e=R.load_env(R.ENV); print(json.dumps(R.get('<id-or-edge>', e['META_ADS_ACCESS_TOKEN'], e['GRAPH_VERSION'], {'fields':'...'}),indent=2))"
```

## Read the output in this order

**1. Compare `schedule` start_time against the clock before saying anything about spend.** Campaigns are scheduled with future start times. `$0.00 spend, no delivery` on a campaign that hasn't started is not a problem — it's a campaign that hasn't started. Get real UTC time from the machine, don't assume.

**2. Then check `effective_status` on ads.** `ACTIVE` = passed review. `PENDING_REVIEW`, `DISAPPROVED`, or `WITH_ISSUES` on any ad is the actual story — pull `issues_info` and `ad_review_feedback` for that ad id.

**3. Then read the numbers.** Insights lag several hours, and `amount_spent` lags further. Zeros a couple hours after launch mean nothing.

## Context you need to interpret it

- **Ads Manager is not truth.** The Telegram bot and the Sheet CRM are truth for real заявки. Meta over- and under-counts. Winner = cheapest *real* заявка, not cheapest reported lead.
- **The pixel has almost no Lead history** (2 events, both 2026-07-21). Any campaign optimizing OFFSITE_CONVERSIONS for LEAD will sit learning-limited on a small budget. That's expected, not a bug — don't report it as a failure.
- **The campaign was built by hand in Ads Manager, not by `campaign.py`.** The app is in Development mode, so the API can't create ad creatives (subcode 1885183). Don't try to "fix" a live campaign with `campaign.py` — it builds new ones only.
- **Raw Graph budget fields are in cents.** `daily_budget: "600"` is $6.00/day. `report.py` already divides; a hand-rolled Graph call does not.
- Full background: `automations/meta-ads/README.md`, plan of record: `automations/meta-ads/campaign-setup-test-01.md`.

## Never do these without Operator saying so explicitly

- Pause, unpause, edit, or duplicate anything live. **Edits reset the learning phase.** The standing rule after launch is: don't touch for 72h.
- Change budget, schedule, targeting, or creative.
- Run `campaign.py --create`.

Reading is always fine. Writing is never yours to decide.

## Report it like this

Lead with the one-line verdict — spending / not started / not delivering / has numbers — then the table, then what it means for the funnel. If there's real spend, log the result in `funnel/02-meta-ad.md` and suggest a decision-log entry.
