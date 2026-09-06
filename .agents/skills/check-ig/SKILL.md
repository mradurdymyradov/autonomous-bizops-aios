---
name: check-ig
description: Use when Operator asks how the Instagram profile itself is doing organically — "how's my IG", "check the page", "how many saw the post", "is the profile working", "how did that post do", "сколько охват", "как профиль", "статистика инстаграма" — or when a content decision needs real per-post numbers. Organic only, read-only. For ad spend use /check-ads.
---

## What this does

Reads organic performance for **@voronka.tm** via the Instagram Graph API — account reach, views,
profile visits, link taps, and per-post numbers. Posts nothing, changes nothing.

## Run this

```bash
cd "D:/ai projects/vaios/automations/ig-insights" && PYTHONIOENCODING=utf-8 python report.py --days 28
```

`--days N` window, clamped at Meta's 30-day cap. `--posts N` how deep into post history (default 12).
`--competitor U` runs business_discovery on a public account. `--snapshot` writes `history/<ts>.json`.
`--no-demographics` skips 12 calls that stay empty until ~100 followers. `--json` machine-readable.
Today: !`date +%Y-%m-%d`

The `PYTHONIOENCODING=utf-8` prefix is not optional on his machine — the console is cp1251 and Cyrillic
captions crash the print without it.

Credentials come from `automations/meta-ads/.env` (never-expiring system-user token). There is no
separate `.env` here on purpose. If auth breaks, `cd ../meta-ads && python verify.py` fails loudly on
the exact broken line.

For anything the script doesn't print, reuse its helpers:

```bash
python -c "import report as R,json; t,ig,v=R.load_env(); print(json.dumps(R.get(f'{ig}/<edge>',t,v,{'fields':'...'}),indent=2,ensure_ascii=False))"
```

## Read the output in this order

**1. Read the PAID vs ORGANIC block first, and never quote an account total without it.** The report
splits reach by `media_product_type`, so `AD` is separated from `POST`/`STORY`/`CAROUSEL_CONTAINER`.
As of 2026-07-26 that's ~5,939 ad reach against ~156 organic. Quoting the combined number reports the
$5.87 ad as if the content earned it, which is a growth story that does not exist.

Per-post numbers are also clean — the ad creatives were never published as feed posts, so they never
touch the post lines.

**2. Then read per-post.** With 3 posts live, reach 44–52 and eng/reach 7–10% is the real baseline.
Ranking posts against each other is the useful output — which hook earned saves and profile visits,
not which got likes.

**3. Then the funnel-shaped metrics.** `profile_views`, `profile_links_taps`, `website_clicks`, and
per-post `profile_visits`/`follows` are the only organic numbers that touch revenue. Reach without
profile visits means the content got seen and ignored.

## Context you need to interpret it

- **Empty is usually "too small", not "broken".** All three demographic sets and
  `follows_and_unfollows` come back empty until roughly 100 followers; the account has 29. Report it as
  a threshold, never as an error, and never as a thing to go fix.
- **Stories are the one irreversible data loss here.** Story insights die with the story at 24h and
  there is no historical endpoint. If Operator posted stories today, run `--snapshot` before saying anything
  else — analysis can wait, the data cannot.
- **`--competitor <username>` reads any public business/creator account** — followers, post cadence,
  likes, comments, and `view_count` (which Meta blocks on our own media). That's prospect research for
  the SMB pipeline, not just vanity comparison.
- **Nothing here is a lead.** The Telegram bot and the Sheet CRM are truth for real заявки. Reach,
  views, and even link taps are upstream vanity until they land there.
- **29 followers means small numbers are noise.** One person saving a post moves eng/reach by points.
  Don't build strategy off a swing of 3.
- **This is the third leg.** Paid = `/check-ads`, site = `/check-ga4`, organic = here. When a question
  spans them, run both and reconcile — IG link taps vs GA4 sessions — instead of two separate stories.
- Full technical detail and the traps already hit: `automations/ig-insights/README.md`.

## Report it like this

Lead with the one-line verdict — working / not being seen / that was paid, not organic — then the
numbers, then what it changes for content. Tie it back to the open loops in
[STATE.md](../../STATE.md): the case-study hero post and the batch 02 highlights are the content bets
these numbers are supposed to judge. If a post clearly out- or under-performed, say what to write more
of, and suggest a decision-log entry.

Don't dress up 29 followers as traction. He knows the number.
