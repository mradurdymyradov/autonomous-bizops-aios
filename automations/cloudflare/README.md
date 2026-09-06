# Cloudflare — the server-side view of voronkatm.com

The fourth measurement leg. GA4 and the Meta pixel both need JavaScript to run before they
count anything. Cloudflare counts the request at the edge, before a single line of JS executes.

**That difference is the entire reason this exists.** On test-01, ~45% of Meta's paid link
clicks never became a GA4 session ([funnel/03-landing-page.md](../../funnel/03-landing-page.md)).
Three explanations fit that gap and GA4 cannot tell them apart:

| Explanation | What Cloudflare shows |
|---|---|
| The click never reached the site | page views ≈ GA4 sessions, both far below Meta clicks |
| The page loaded, the visitor left before the tag fired | page views ≈ Meta clicks, GA4 far below |
| The tag is broken / blocked | page views ≈ Meta clicks, GA4 near zero |

One run of `report.py` picks between them. That is the cheapest unclaimed win in the funnel —
it multiplies traffic at zero extra ad spend.

**Read-only by design.** The token below cannot edit DNS, Pages, Workers, or a deployment.

---

## Setup

**1. Create the API token.** dash.cloudflare.com → My Profile → API Tokens → **Create Token**
→ **Create Custom Token**:

| Scope | Permission | Level |
|---|---|---|
| Zone | Analytics | Read |
| Zone | Zone | Read |
| Account | Account Analytics | Read |
| Account | Pages | Read |

Zone Resources: Include → Specific zone → `voronkatm.com`.
Account Resources: Include → your account.

Do **not** grant Edit on anything. Nothing here writes.

**2. Get the two IDs.** dash.cloudflare.com → `voronkatm.com` → Overview → right-hand column.
**Zone ID** and **Account ID** are two different 32-char hex strings on the same panel — the
most common setup mistake is pasting the same one twice, and `verify.py` checks for exactly that.

**3. Fill `.env`.** `cp .env.example .env`, paste all three values. Gitignored.

**4. Verify.**

```bash
cd "D:/ai projects/vaios/automations/cloudflare" && python verify.py
```

Seven checks in order, each printing the exact fix for the one that broke. Don't debug by hand.

---

## Running it

```bash
cd "D:/ai projects/vaios/automations/cloudflare" && python report.py --days 7
```

| Flag | Does |
|---|---|
| `--days N` | window, default 7 |
| `--from / --to` | explicit `YYYY-MM-DD` range |
| `--paths` | per-URL + referer breakdown (adaptive dataset, may be plan-limited) |
| `--hours` | hour-by-hour, UTC |
| `--list` | **which datasets this plan actually exposes** (schema introspection) |
| `--gql "<query>"` | arbitrary GraphQL, for anything the sweep misses |
| `--json` | machine-readable |

**Every section probes independently.** A dataset the Free plan doesn't expose prints under
`NOT AVAILABLE` with Cloudflare's own error message, and the rest of the run continues.
`--list` is the authoritative answer for what this plan exposes; don't argue with it from
documentation.

**What the first authenticated run (2026-07-28) settled** — this was the open question when the
tool shipped:

| Section | Verdict on Free |
|---|---|
| Daily totals, day-by-day, content type, status, country (`httpRequests1dGroups`) | **works** |
| Pages Functions invocations + errors (`pagesFunctionsInvocationsAdaptiveGroups`) | **works** |
| `--paths` per-URL (`httpRequestsAdaptiveGroups`) | **works, but max 1-day window** — `--days 1` or a 1-day `--from/--to`. Wider spans are refused by Cloudflare, not by us. |
| `--paths` referer breakdown (`clientRequestHTTPHost` → `clientRefererHost`) | **not on Free** — the field doesn't exist for this zone. The "count paid IG traffic without a tag" idea is dead here. |

---

## Reading it

**`pageViews` is the number.** It counts HTML documents served — the closest server-side
equivalent to "someone actually opened the landing page."

**But on Free it is not bot-filtered, and the inflation is brutal.** First real run
(2026-07-22..28): 3,282 `pageViews` against 317 GA4 sessions — roughly 7×. `--paths` shows why:
`/wp-admin/install.php` probes, and 47.6% of requests exiting from US IPs on a Turkmen-targeted
campaign. Free has no `botManagement` field to filter on. **So `pageViews` is a ceiling, not a
count.** Use it to answer "did *anything* reach the origin" and to catch a total-blackout failure;
do not read a 2,170-vs-317 gap as 1,853 lost humans. When the two disagree by less than an order
of magnitude, that is when the comparison is telling you something.

**Never compare total `requests` to GA4 sessions.** Requests include every CSS file, image,
favicon, bot, crawler, and uptime probe. One human page load is many requests. `pageViews` is
the comparable figure; `requests` is infrastructure.

**`/api/lead` hits are not lead counts.** The same endpoint receives the phone submit *and* every
`chat_answer` POST ([funnel/04-lead-capture.md](../../funnel/04-lead-capture.md)) — one lead who
answers all three chat questions produces four hits. Only the Sheet CRM counts leads.

**Errors on Pages Functions are the alarming number.** A failed `/api/lead` invocation is a
submit that reached the server and may never have reached Telegram *or* the Sheet. That is an
invisible lost lead — it appears in no other tool, because every other tool measures a stage
either before or after it.

**Geography is VPN-distorted, same as GA4.** Turkmen traffic exits as NL/DE/TR. Not a targeting
failure.

**Uniques are an edge estimate**, IP-based, and VPN exit nodes collapse many people into one.
Treat as a floor.

---

## Gotchas

- **Free plan splits the datasets.** `httpRequests1dGroups` (daily totals, country, status,
  content type) is reliable. The `*AdaptiveGroups` datasets behind `--paths` are capped at a
  1-day window and drop the referer field — see the table above. That is a plan limit, not a
  broken setup.
- **The Pages worker is not named after the project.** It is `pages-worker--<id>-production`
  (`pages-worker--15792751-production` here). Filtering the Functions query on `CF_PAGES_PROJECT`
  returns zero rows and makes the section vanish silently — so `report.py` deliberately does
  *not* filter, and prints the script name it actually found. `CF_PAGES_PROJECT` is used only by
  `verify.py`'s REST check.
- **`verify.py` never calls `/accounts/{id}`.** That REST endpoint needs
  `Account | Account Settings | Read`, which this token deliberately does not carry. Check 4 tests
  the account *GraphQL* container instead, which is the thing the report actually needs. If you
  "fix" a failure there by adding Account Settings, you've widened the token for nothing.
- **`voronka.pages.dev` traffic is not in this zone.** It belongs to a Cloudflare-owned zone.
  Ads point at `voronkatm.com`, so this matters only if someone shares the fallback URL.
- **Daily buckets are UTC**, not Asia/Ashgabat (UTC+5). GA4 and the Meta ad account both report
  in Ashgabat time, so a Cloudflare day boundary sits 5 hours off theirs. For same-day
  comparisons use `--hours` and shift, or accept the edge blur on day boundaries.
- **The orange cloud must be on.** If the DNS record is grey (DNS-only), Cloudflare proxies
  nothing and analytics stay empty regardless of the token. Pages custom domains are proxied by
  default.
- **Connection is 2–4 Mb/s VPN.** Both scripts retry four times with backoff. A failure is
  usually the tunnel — retry before suspecting the code.

## Never

- Never issue this token with Edit on anything. If a task seems to need a write, it belongs in
  the LP repo with `wrangler`, not here.
- Never commit `.env`.
- Never change the LP's tracking code mid-campaign to "fix" a gap this tool finds — a tag change
  mid-flight makes the whole window uncomparable.
