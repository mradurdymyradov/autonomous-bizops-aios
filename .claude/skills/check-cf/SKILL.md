---
name: check-cf
description: Use when voronkatm.com looks broken rather than slow — submits failing, заявки not arriving, site down, or leads dropping off a cliff with no matching drop in ads or GA4. Server-side health at the Cloudflare edge: /api/lead Worker errors and origin 5xx. Not a traffic tool — use /check-ga4 for visitors. Read-only.
---

## What this is for

Two alarms, and nothing else:

1. **`/api/lead` Worker invocation errors** — a submit that reached the server and may have reached
   neither Telegram nor the Sheet.
2. **Origin failures on `/`** — 5xx, 524, 504: visitors who got nothing.

Both are structurally invisible everywhere else. GA4 fires `generate_lead` client-side *before* it
knows the outcome; the Sheet obviously cannot record a write that never happened; and no tag can
report a page that never loaded. That is the entire reason this leg exists.

**It is not a traffic tool.** See the hard warning on `pageViews` below before quoting any number
from it as visitors.

## Run this

```bash
cd "D:/ai projects/vaios/automations/cloudflare" && python report.py --days 7
```

Pick the window from what Operator actually said. Don't default to 7 if he named one.

| he says | you run |
|---|---|
| "last 3 days" | `--days 3` |
| "this week", nothing | `--days 7` |
| "since the campaign launched" | `--from 2026-07-23` |
| "which pages are erroring", "is /api/lead being hit" | `--paths --days 1` (**1-day max** — see below) |
| "what time did it break" | `--hours` |

Other flags: `--list` (which datasets this plan exposes) · `--gql "<query>"` (arbitrary GraphQL) ·
`--json`.

**If it errors on auth, IDs, or permissions, run `python verify.py`.** Seven checks in order, each
printing the exact fix. Don't debug by hand.

## Read the output in this order

**1. Pages Functions errors. This is the whole job.** A failed `/api/lead` invocation is a submit
that reached the server and may never have reached Telegram *or* the Sheet — an invisible lost
lead. Non-zero here means go count rows in `/check-crm` for the same window and reconcile.
Baseline as of 2026-07-28: **928 invocations, 0 errors.**

**2. Status codes.** 4xx/5xx on `/` or `/api/lead` is a lost visitor, not a statistic. A 5xx spike
during a live campaign is the most urgent thing this tool can say. Baseline: a handful of `524`
and `499` per week — a jump off that is the signal.

**3. Everything else is supporting detail.** Country, content type, hours. Do not lead with it.

## The `pageViews` trap

**`pageViews` is a ceiling, not a count, and it is not bot-filtered.** First real run
(2026-07-22..28): **3,282 `pageViews` against 317 GA4 sessions — roughly 7×.** `--paths` shows the
cause: `/wp-admin/install.php` scanners, and 47.6% of requests exiting from US IPs on a
Turkmen-targeted campaign. The Free plan has no `botManagement` field to filter on.

Use it only to answer *"is the origin serving anything at all"* — a total blackout is visible, a
44% discrepancy is not. **Never quote it as visitors. Never reconcile it against GA4 sessions or
Meta clicks** — the bot floor swamps the signal you'd be looking for.

**And never compare total `requests` to anything.** Requests count every CSS file, image, favicon
and probe; one human page load is many requests.

## Settled — do not re-open

**The "~45% click→page leak" does not exist.** Closed 2026-07-28
([decisions/log.md](../../decisions/log.md)). GA4 logged **271** Paid Social sessions for campaign
`test01` against Meta's **264** link clicks — more sessions than clicks. The clicks arrived and the
pages loaded. What undercounts is Meta's `landing_page_view` pixel, ~44% low, almost certainly the
IG in-app browser dropping the pixel while the GA4 tag survives.

So: **if Meta and GA4 disagree about volume, that is a Meta pixel question, not a Cloudflare
question.** Don't run this tool at it. And never optimise a campaign for `landing_page_view` or
quote an LPV-derived conversion rate — standing rule in
[funnel/02-meta-ad.md](../../funnel/02-meta-ad.md).

## Context you need to interpret it

- **`/api/lead` hits are not lead counts.** The same endpoint takes the phone submit *and* every
  `chat_answer` POST — one lead answering all three chat questions makes four hits. Only the
  Sheet CRM counts leads (`funnel/04-lead-capture.md`).
- **Cloudflare is truth for one narrow thing: did the request arrive, and did the Worker survive
  it.** The Telegram bot and the Sheet CRM are truth for заявки.
- **Cloudflare days are UTC; GA4 and the Meta ad account are Asia/Ashgabat (UTC+5).** Day
  boundaries sit 5 hours apart. For a same-day comparison use `--hours` and shift, or say the
  edge blur out loud rather than reporting a false discrepancy.
- **Geography is VPN-distorted** exactly like GA4 — TM traffic exits as NL/DE/TR. Never report it
  as a targeting failure.
- **Uniques are IP-based**, and VPN exits collapse many people into one. A floor, not a count.
- **Free-plan limits, settled by introspection 2026-07-28** — don't rediscover these:
  daily totals ✅ · Pages Functions ✅ · `--paths` ✅ but **1-day window max** (wider spans are
  refused by Cloudflare) · **referer breakdown ❌** (the field doesn't exist for this zone).
  Check `--list` before claiming Cloudflare can't do something.
- **The Pages worker is not named after the project** — it is `pages-worker--15792751-production`.
  `CF_PAGES_PROJECT` is used only by `verify.py`.
- **Connection is 2–4 Mb/s VPN.** Both scripts retry four times. A failure is usually the tunnel.

Full setup and gotchas: `automations/cloudflare/README.md`.

## Never do these

- Never issue or swap in a token with Edit permission on anything. This leg is read-only by
  design; writes belong in the LP repo with `wrangler`.
- Never widen the token to fix a `verify.py` check — check 4 deliberately tests the account
  *GraphQL* container, not REST `/accounts/{id}`, because that endpoint needs a scope we refuse.
- Never change the LP's tracking code mid-campaign to "fix" a gap found here — a tag change
  mid-flight makes the whole window uncomparable. Log it, fix it between campaigns.
- Never commit `automations/cloudflare/.env`.

## Report it like this

Lead with the alarm state: **submits clean / submits failing / origin erroring**. Give the error
counts and the baseline they're measured against. If either alarm is live, say what it costs in
leads and point at `/check-crm` for the same window.

If both are clean, say so in one line and stop. Do not pad it with `pageViews`, country tables, or
a traffic narrative — that's the failure mode this tool invites, and the numbers won't survive
scrutiny.
