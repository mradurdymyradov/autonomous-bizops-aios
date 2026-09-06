# Snapshot schema — the one row every surface folds into

**Law for `check-full`, `snapshot.py`, and the dashboard.** All three are the same design done
once: check-full *computes* the row and prints it, snapshot.py *stores* it, the dashboard *draws*
it. If they ever disagree about a field, this file wins.

Written 2026-07-28. Reference, not state — no live numbers here.

---

## Why this exists before the dashboard

Every reader is a point-in-time query against an API with a hard window: Instagram insights cap at
30 days, story insights die at 24h with no historical endpoint, GA4 backfills for ~48h then
freezes, Meta presets only go back so far. **Nothing accumulates today.** Every day that passes
unsnapshotted is permanently gone, and a dashboard cannot draw a line through data that was never
kept.

So the storage comes first and the dashboard comes later. The local JSON files this schema defines
are a valid backfill source for the cloud version, which is the whole point of writing the schema
before either exists.

---

## The funnel line

The single artifact `check-full` prints. Seven stages, five sources, one row.

```
impressions -> link_clicks -> ga4_sessions -> generate_lead -> leads_real -> dialled -> answered
    Meta         Meta            GA4             GA4            SHEET       phone log  phone log
```

**Only `leads_real` is truth.** Everything left of it is an estimate; everything right of it is as
fresh as the last manual phone export.

### Two stages are deliberately NOT in this line

| Excluded | Why |
|---|---|
| Meta `landing_page_view` | ~44% low against GA4 — the IG in-app browser drops the pixel while the GA4 tag survives. Standing rule in [funnel/02-meta-ad.md](../funnel/02-meta-ad.md): never optimise for it, never derive a rate from it. Stored, never divided by. |
| Cloudflare `pageViews` | ~7× bot-inflated on the Free plan (3,282 vs 317 GA4 sessions, 2026-07-22..28), and Free has no `botManagement` field to filter on. It is a ceiling, not a count. |

Cloudflare contributes **health flags, not funnel stages** — see `cf` below. This is settled: the
"~45% click→page leak" was closed 2026-07-28 ([decisions/log.md](../decisions/log.md)) when GA4
showed 271 paid sessions against Meta's 264 link clicks. Don't rebuild a reconciliation around it.

---

## The row

One object per **Ashgabat date**. `snapshots/daily/<YYYY-MM-DD>.json`.

```jsonc
{
  "date": "2026-08-03",              // Asia/Ashgabat. The join key for everything.
  "captured_at": "2026-08-03T23:41:07Z",
  "final": false,                    // true once date < today-3. See "Late data" below.
  "sources_ok": ["meta","ga4","crm","ig","cf"],   // which readers answered
  "sources_failed": {"ig": "network failed after 4 tries"},

  "meta": {                          // meta-ads/report.py --json
    "spend_usd": 6.64,
    "impressions": 4495,
    "reach": 3766,
    "clicks": 100,                   // ALL clicks, not link clicks
    "link_clicks": 63,               // actions[].link_click  <- the funnel stage
    "landing_page_views": 36,        // stored, NEVER a denominator (see above)
    "meta_leads": 14,                // actions[].lead — an estimate, undercounts ~18%
    "cpc": 0.0664,
    "ctr": 2.2247
  },

  "ga4": {                           // ga4/report.py --json
    "sessions": 0,
    "paid_sessions": 0,              // Paid Social channel only
    "engaged_sessions": 0,
    "generate_lead": 0,              // the LP's real-submit event <- the funnel stage
    "key_events": 0                  // READS 0 BY CONFIG until the GA4 toggle is flipped
  },

  "crm": {                           // sheets/crm.py --json — TRUTH
    "leads_real": 0,                 // deduped, test rows excluded <- the funnel stage
    "leads_raw_rows": 0,
    "by_creative":  {"video": 0, "c.flat": 0, "link_in_bio": 0},
    "by_business":  {"Услуги": 0, "Магазин": 0},
    "by_language":  {"ru": 0, "tm": 0},
    "no_phone": 0                    // chat fired, submit never landed — a capture bug
  },

  "calls": {                         // sheets/calls.py — phone XML export, NOT live
    "dialled": 0,
    "answered": 0,
    "talk_seconds": 0,
    "callbacks_in": 0,
    "outcomes": {"Договорились": 0, "Отказ": 0},
    "export_through": "2026-07-25T21:50:00+05:00"   // REQUIRED. The staleness bound.
  },

  "ig": {                            // ig-insights/report.py --json — organic only
    "followers": 29,
    "organic_reach": 0,              // media_product_type split — never the raw total
    "ad_reach": 0,
    "profile_views": 0,
    "website_clicks": 0,
    "posts_live": 3
  },

  "cf": {                            // cloudflare/report.py --json — ALARMS, not volume
    "tz": "UTC",                     // the one source not on Ashgabat time
    "function_invocations": 0,
    "function_errors": 0,            // >0 = submits that may have reached neither TG nor Sheet
    "origin_5xx": 0,
    "page_views_bot_inflated": 0     // name carries the warning. Do not chart this.
  },

  "money": {
    "spend_usd": 6.64,               // mirrors meta.spend_usd
    "revenue_usd": 0                 // manual. Stays 0 until a pilot pays.
  }
}
```

### Story snapshots are a separate, append-only file

`snapshots/stories/<YYYY-MM-DDTHHMM>.json`. Stories die at 24h with no historical endpoint, so
these are captured on posting days and **never upserted** — a story snapshot is a point observation,
not a daily aggregate. This is the only data in the system that is unrecoverable if missed.

---

## Rules that are easy to get wrong

**1. Rows are mutable for three days, then frozen.** GA4 backfills ~48h, Meta insights lag hours,
the CRM is immediate. A row for date D is not final until D+3. Upsert by `date`; set `final: true`
once the window passes; after that, never rewrite. A snapshot runner that writes each day once and
never revisits will permanently understate the last three days of every metric.

**2. `date` is Asia/Ashgabat.** Meta's ad account, the GA4 property and the Sheet all report in it,
so they line up day-for-day. Cloudflare is UTC and sits 5 hours off — that is why `cf.tz` is stored
explicitly and why nothing from `cf` enters the funnel line. Do not silently coerce it.

**3. A failed source is `null`, never `0`.** "The IG reader timed out on the VPN" and "reach was
zero" must not collapse into the same value. `sources_failed` carries the reason. A chart that
plots a tunnel drop as a traffic collapse is worse than a gap in the line.

**4. `calls.export_through` is required whenever `calls` is present.** The call data comes from a
manual XML export off the phone; Android exposes no call log to any API. Without that bound, stale
call numbers look current, which is exactly how the «Звонки» tab misled once already.

**5. Store raw responses too.** `snapshots/raw/<date>/<source>.json`. When a field turns out to be
wrong or a new one is needed, the row can be recomputed instead of the history being lost. Cheap
now, impossible later. Raw is gitignored (~40× the size of the rows); `snapshots/daily/` is not —
those rows cannot be re-fetched once the APIs age them out.

**6. `ig.followers` and `ig.posts_live` are capture-time, not date-time.** They are stamped onto
every row in the window from the profile as it looks *now*, because Instagram's daily
`follower_count` metric is gated until ~100 followers. So a backfilled row says what the follower
count is today, not what it was on that date. Don't chart it as growth until the gate lifts.

---

## Where each field actually comes from

Verified against live reader output 2026-07-28. The readers do **not** share a shape — each one's
`--json` is its own surface, and `snapshot.py` is the thing that normalizes them into the row above.
These paths are the contract; don't re-derive them by trial and error.

| Row field | Reader | Path in its `--json` |
|---|---|---|
| `meta.*` scalars | `meta-ads/report.py --json` | `insights.{spend,impressions,reach,clicks,cpc,ctr}` — **all strings**, cast them |
| `meta.link_clicks` | same | `insights.actions[]` where `action_type == "link_click"` |
| `meta.meta_leads` | same | same array, `action_type == "lead"` |
| `meta.landing_page_views` | same | same array, `"landing_page_view"` — store, never divide by |
| `ga4.sessions` | `ga4/report.py --json` | `sections.totals_volume.records[0].sessions` — use **`records`** (keyed), never `rows` (positional). Added 2026-07-28 for exactly this reason |
| `ga4.generate_lead` | same | `sections["EVENTS - every event GA4 recorded"].records[]` where `eventName == "generate_lead"` → `eventCount` |
| `ga4.key_events` | same | `totals_volume.records[0].keyEvents` |
| `ga4.key_events_configured` | same | **top-level tri-state**, added 2026-07-28. `false` = `generate_lead` fired but `keyEvents` is 0, so every conversion rate is a false zero **by config**. When this is `false`, suppress conversion-rate output rather than printing 0%. `null` = no leads in window, unanswerable. Confirmed `false` on 2026-07-28 |
| `ga4.paid_sessions` | same | `sections["ACQUISITION - default channel group"].records[]`, row `"Paid Social"` |
| `crm.leads_real` | `sheets/crm.py --json` | **`summary.leads_real`** — computed in the reader since 2026-07-28, so no consumer reimplements the flag logic |
| `crm.leads_raw_rows` | same | `summary.rows` (== `count`). `count` is **raw rows, not leads** — 65 rows vs 61 real on the 30d window. Never report it as a lead count |
| `crm.by_creative` | same | `summary.by_creative`, already normalized to `video` / `c.flat` / `link_in_bio`. Do **not** parse `utm.content`, it is the literal unsubstituted `{{ad.video}}` macro |
| `crm.by_business` / `by_language` | same | `leads[].chat` |
| `crm.no_phone` | same | `summary.no_phone` |
| `calls.*` | `sheets/calls.py` | `leads[].call_stats` / `leads[].calls` on the same CRM payload |
| `ig.*` | `ig-insights/report.py --json` | account totals split by `media_product_type` — take the organic split, never the raw total |
| `cf.*` | `cloudflare/report.py --json` | `functions` (invocations/errors), `daily[].sum.responseStatusMap` for 5xx |

One shape trap remains: **Meta returns every numeric as a string** (`"spend": "6.64"`). Cast on
read. That is a silent-wrong-answer bug, not a crash — string concatenation instead of addition.

GA4's positional-row trap and the `crm.count` trap were both **fixed at the source on 2026-07-28**
rather than documented as hazards: `records` and `summary` now exist so a consumer cannot get them
wrong by default. If you find yourself reading `rows[].vals[]` or `count`, you're on the old path.

---

## Storage: local now, D1 later, same shape

```
automations/snapshots/
  daily/2026-08-03.json          one row per Ashgabat date, upserted for 3 days
  stories/2026-08-03T2340.json   append-only, never revisited
  raw/2026-08-03/meta.json       verbatim reader output, for recompute
```

The cloud version reads the same JSON into D1 — the local files backfill it, so nothing captured
now is wasted:

```sql
CREATE TABLE daily (
  date            TEXT PRIMARY KEY,     -- Asia/Ashgabat YYYY-MM-DD
  captured_at     TEXT NOT NULL,
  final           INTEGER NOT NULL DEFAULT 0,
  spend_usd       REAL,
  impressions     INTEGER,
  link_clicks     INTEGER,
  meta_leads      INTEGER,
  ga4_sessions    INTEGER,
  generate_lead   INTEGER,
  leads_real      INTEGER,              -- truth
  dialled         INTEGER,
  answered        INTEGER,
  revenue_usd     REAL DEFAULT 0,
  cf_fn_errors    INTEGER,
  cf_origin_5xx   INTEGER,
  payload         TEXT NOT NULL         -- the full row above, verbatim
);
CREATE TABLE stories (
  captured_at TEXT PRIMARY KEY,
  payload     TEXT NOT NULL
);
```

Flat columns are what the dashboard charts; `payload` keeps everything else so a new chart never
needs a migration or a backfill.

**If it moves to Cloudflare Workers + D1 + a cron trigger, the collector gets its own credentials.**
Never the ads system-user token — it can spend from the Mastercard on file. Issue a second Meta
system user with `ads_read` only, and a second Google key that is read-only everywhere. The
collector writes nothing anywhere and needs no scope that could.

---

## Building order

1. `snapshot.py` — runs the five readers' `--json`, writes `daily/` + `raw/`. Starts the series.
2. `check-full` — reads today's row, prints the funnel line. No new API work; it consumes step 1.
3. Dashboard — reads the folder. Still no new API work.
4. Workers + D1 + cron — only worth it once the local version has proven the schema.

Steps 1–3 need no new credential and no cloud account. **Step 1 is the only one that is
time-sensitive**, because it is the only one that stops losing data.

**Steps 1–3 are done (2026-08-03).** The dashboard lives at `automations/dashboard/` and is built by
`/dashboard`. One correction to the plan above: the row defined by this file turned out to be the
*funnel*, not the *business*. Revenue, the client pipeline, the callback debt and the open loops are
not in any API, so the dashboard reads a **second** input alongside these rows —
`automations/dashboard/business.json`, a generated projection of `STATE.md` / `TODO.md` / the client
folders, carrying a hash of every source so a stale projection announces itself on the page. This
file stays law for the row; it was never law for the whole screen.

**The dashboard was rebuilt on 2026-08-05** — same two inputs, same three tiers, different surface.
The first version rendered as one long scroll and Operator read it as a PDF report he opened once. It is
now an operations console: six hash-routed sections, a ranked morning queue, drill-down drawers.
Nothing in this file changed for that; the row is still the row. What did change is that the page
now *acts* on the row — `build_queue()` and `build_insights()` in `build.py` turn it into things to
do — so a null that quietly becomes a zero no longer just draws wrong, it tells him to make a call
that isn't owed. Rule 3 got sharper teeth, not a rewrite.
