# GA4 toolkit — voronka.tm

Read-only access to everything Google Analytics 4 knows about the landing page.
Mirrors `automations/meta-ads/` in shape: `.env` next to the scripts,
`verify.py` health-checks, `report.py` reads.

| file | what it does |
|---|---|
| `report.py` | the full sweep — totals, day-by-day, hour-of-day, acquisition, events, pages, geo, tech, audience, demographics |
| `verify.py` | fails loudly on the exact broken line of setup |
| `.env` | property ID + path to the service account key (gitignored) |

The key itself lives one level up at `automations/google-service-account.json` — **shared with the
sheets toolkit**, one credential for both. Gitignored.

## What's already true

- GA4 is **live on the LP**. Measurement ID `G-LVK4PKT4C2`, added to
  `site/index.html` as a lazy loader (gtag/js downloads on first interaction,
  so it costs nothing on page load).
- `trackLead()` in `site/app.js` fires `gtag('event','generate_lead')` on every
  real submit — same two call sites as the Meta pixel Lead event
  (`app.js:161` hero form, `app.js:576` chat), both gated behind a valid
  8-digit phone tail.
- So **`generate_lead` in GA4 and `Lead` in the Meta pixel should track each
  other.** When they diverge, one of them is lying, and that gap is the signal.

## Setup — DONE 2026-07-26

Already wired. Cloud project `voronka-data`, Analytics Data API + Sheets API
enabled, service account `voronka-reader@voronka-data.iam.gserviceaccount.com`
granted **Читатель (Viewer)** on property **544092543**. Key at
`automations/google-service-account.json`.

```bash
cd "D:/ai projects/vaios/automations/ga4" && python verify.py
```

Passes as of 2026-07-26. **The steps below are the rebuild recipe** — only needed
if the key or the service account is deleted.

<details>
<summary>Rebuild from scratch (five steps, ~4 minutes, logged-in browser)</summary>

Steps 1–3 are Google Cloud Console, steps 4–5 are GA4.

**1. Pick or create a Cloud project.**
https://console.cloud.google.com/projectcreate — name it `voronka-analytics`.
Any existing project works too; the project only hosts the credential.

**2. Enable the Analytics Data API** on that project.
https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com
→ **Enable**. (This is the API, not "Google Analytics API" — that one is the
old Universal Analytics surface and will not work.)

**3. Create a service account and download its key.**
https://console.cloud.google.com/iam-admin/serviceaccounts → **Create service
account** → name `ga4-reader` → **Done** (skip the optional role grants; the
permission that matters is granted inside GA4, not here).
Then click the account → **Keys** → **Add key** → **Create new key** → **JSON**
→ it downloads.
Save that file as:

```
d:\ai projects\vaios\automations\google-service-account.json
```

One level up, not in this folder — the sheets toolkit reads the same key.

Copy the `client_email` out of it — it looks like
`voronka-reader@voronka-data.iam.gserviceaccount.com`. You need it in step 5,
and to re-share the sheet (`automations/sheets/README.md`).

**4. Get the numeric property ID.**
https://analytics.google.com → **Admin** → **Property Settings**. The
**PROPERTY ID** is a 9–10 digit number in the top right.
It is **not** `G-LVK4PKT4C2` — that is the measurement ID and the API rejects it.
Copy `.env.example` to `.env` and paste the number into `GA4_PROPERTY_ID`.

**5. Give the service account read access to the property.**
GA4 → **Admin** → **Property Access Management** → **+** → **Add users** →
paste the `client_email` from step 3 → role **Viewer** → uncheck "Notify by
email" → **Add**.

This is the step everyone forgets. Without it every call returns
`PERMISSION_DENIED` no matter how correct the key is.

**Then:**

```bash
cd "D:/ai projects/vaios/automations/ga4" && python verify.py
```

It prints `OK` or `FAIL` per line with the exact fix. Once it passes, the
`/check-ga4` skill works.

</details>

## Using it

```bash
python report.py                          # last 7 days, full sweep
python report.py --days 30
python report.py --from 2026-07-23 --to 2026-07-27
python report.py --realtime               # active users, last 30 min
python report.py --list                   # every dimension + metric available
python report.py --dims city,deviceCategory --metrics sessions,keyEvents
python report.py --days 3 --json          # machine-readable
```

## Things that will bite you

- **Dates are in the property's timezone**, not UTC and not this machine's.
  The GA4 property and the Meta ad account are both Asia/Ashgabat (UTC+5), so
  they line up — but "today" in a report is not "today" in UTC.
- **Data lags.** GA4 standard properties finalise ~24–48h back. Today's numbers
  and even yesterday's move. Realtime is separate and only covers 30 minutes.
- **Demographics are thresholded.** Age and gender go blank on low traffic —
  Google suppresses them to prevent identifying individuals. Blank is normal
  at this volume, not a broken setup.
- **`(not set)` and `(other)`** are real GA4 values, not errors. `(other)`
  means the row hit a cardinality limit and got bucketed.
- **`keyEvents` replaced `conversions`** in the API. `report.py` prunes any
  metric a property rejects and retries, so an older property still works.
- **Quota.** Standard properties get 25,000 tokens/day. A full sweep costs a
  few dozen. Not a concern.
- **The connection is 2–4 Mb/s VPN.** `report.py` retries with backoff, same
  as the Meta toolkit.

## Cross-checking against Meta

Both numbers are estimates of the same reality and neither is truth. Truth is
the Telegram bot and the Sheet CRM.

| question | GA4 | Meta |
|---|---|---|
| did the click reach the page | `sessions` from paid | `landing_page_view` |
| did they submit | `generate_lead` | `offsite_conversion.fb_pixel_lead` |
| where were they really | `country` / `city` | `reach` only |

GA4 counts the **click→page leak** honestly — Meta's `link_click` minus
`landing_page_view` gap (~45% on test-01) should show up as the same shortfall
between Meta link clicks and GA4 paid sessions. That is the cheapest win in
the funnel and GA4 is how you size it.
