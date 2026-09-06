# meta-ads — Meta Marketing API toolkit

**What's blocked across every system, and what unlocks it: [../CAPABILITIES.md](../CAPABILITIES.md).**

Reads live campaigns and builds new ones for voronka.tm from the CLI. Sister to `../ig-poster/`.

**Current campaign state is not in this file** — it's in [STATE.md](../../STATE.md), and live numbers
come from `/check-ads`. This file is the technical reference: what exists, what works, what's blocked,
and every dead end already walked so nobody walks it twice.

## Files

- `.env` — token and all IDs. Gitignored. **The token never expires and can spend from the Mastercard
  on file. Treat it like a password.**
- `verify.py` — health check. Run this first when anything breaks. Fails loudly.
- `report.py` — live campaign read. This is what `/check-ads` calls. Read-only.
  `--who` adds audience breakdowns (age, gender, age×gender, placement, device, region), each ranked by
  cost per reported lead. **This is the only source of audience demographics we have** — the organic IG
  endpoints withhold them below ~100 followers, the Marketing API ignores follower count entirely.
  Verified working 2026-07-26. Detail on what organic does and doesn't give: `../ig-insights/README.md`.
- `campaign.py` — campaign builder. Dry-run by default, creates everything PAUSED. Blocked at the
  creative step (see below).
- `scopes.py` — token scope dump.
- `partner.py` + `partner-portfolio.md` — is someone else's Business Portfolio verified, and does it
  actually unblock us? Read-only. Run this the moment anyone offers access to their portfolio; the
  markdown carries the procedure and the order of operations that keeps the ads token alive.
- `campaign-setup-test-01.md` — the manual Ads Manager build plan that produced the first real traffic.
- `creatives/` — the ad assets that shipped.

## Assets (verified live 2026-07-22, re-check with `python verify.py`)

| Asset | ID / value | State |
|---|---|---|
| Ad account | `act_1063017219626646` "voronka.tm" | **ACTIVE**, USD, Asia/Ashgabat |
| Payment method | Mastercard *6962 | on file |
| Facebook Page | `1180291058506773` "voronka.tm" | reachable |
| Instagram | `17841480213410482` @voronka.tm | linked to Page |
| Pixel | `1397681815558353` "voronka dataset" | **live** |
| Domain | voronkatm.com | verified in Meta |
| Business portfolio | `833919419654873` | **UNVERIFIED** |
| App | `4473106283009964` automation_1 | **UNPUBLISHED (dev mode)** |
| API token | system user `vaios-adsbot` (`61592202033039`) | valid, **never expires** |

Scopes: `ads_management`, `ads_read`, `business_management`, `pages_read_engagement`,
`pages_manage_ads`, `pages_manage_posts`, `pages_manage_engagement`, `pages_manage_metadata`,
`instagram_basic`, `instagram_manage_comments`, `instagram_manage_contents`,
`instagram_manage_insights`, `instagram_manage_messages`, `read_insights`, `threads_business_basic`,
`public_profile`.

## What the API can and cannot do

| Operation | Works? |
|---|---|
| Read ad account, page, pixel, insights | **yes** |
| Create campaign / ad set / upload image | **yes** (validated) |
| **Create ad creative** | **NO — hard blocked** |
| Create ad | blocked (needs a creative) |

```
Ad creative was created by an app in development mode.
The app must be public to create this ad.   (code 100, subcode 1885183)
```

`../ig-poster/` posts fine from the same unpublished app — publishing to an Instagram account you own
is permitted in dev mode, creating ad creatives is not. Same app, different rule.

## The block, and everything already ruled out

**Verdict 2026-07-23: publishing is hard-gated on business verification. Tested, not inferred.**
Clicked Publish with privacy URL, data-deletion URL, app icon and category all green. Meta returned
*"Unable to publish this app because not all requirements are complete."* Business verification was the
only outstanding item.

**Business verification is unobtainable.** Walked the full flow 2026-07-22. Every connection method
(email, phone, SMS, WhatsApp, domain) funnels into the same Upload-documents step, which offers exactly
four document types — bank statement, business registration/license, business tax document, articles of
incorporation. All four require a **registered legal business**. No passport path, no national-ID path,
no sole-proprietor path. Meta's own in-platform AI assistant claimed a passport works; it was wrong,
checked against the live flow. Domain verification still demands documents — having voronkatm.com
already verified does not substitute.

Also checked and ruled out:

- **Trimming use cases does nothing.** All 14 are "added" to the app but nearly every permission inside
  them is un-added (status `Add`, not requested). Inert shells. The Publish requirement isn't from them.
- **The App Review submission was a stale draft** (`manage_fundraisers`, `public_profile`,
  `Marketing API Access Tier`), never submitted. Cleared; `scopes.py` confirmed both tokens unchanged
  (16 and 6 scopes, all live checks passing). That list governs *future* permission requests, not
  existing access.
- **The "Standard Access" theory is wrong.** Meta's Feb 2023 dev blog says verification gates *Advanced
  Access* only, and the creative error says *public*, not *verified* — so Standard Access should have
  covered an ad account Operator owns outright. It did not. Publish still hard-blocked. Recorded here only so
  the same research doesn't get re-run.
- **Source-quality warning:** SEO blogs claiming verification without documents via "Signal Hardening",
  "Andromeda AI", or a "Developer Bypass" (personal ID + video selfie) are fabricated. None of that
  terminology is real and it contradicts the live flow.
- **Do NOT press "Remove"** next to the business portfolio on the Publish tab. The system user token
  lives inside that portfolio; detaching it risks killing the ads token to chase a publish that still
  won't work.

**Standing conclusion:** build campaigns manually in Ads Manager. Do not let API purity hold up traffic
— the gate to revenue is traffic, not tooling. `campaign.py` stays blocked until either a business is
registered in TKM, or **this app gets attached to somebody's already-verified Business Portfolio.**
Note the correction: *partner access to their ad account is not the unlock* — the block is on the app,
so the app itself has to sit under a verified portfolio. Procedure: [partner-portfolio.md](partner-portfolio.md).

## Usage

Dry run first. Nothing is created without `--create`, and everything created is **PAUSED** — this
script never starts spend.

```bash
python campaign.py \
  --image ../ig-poster/p2.png \
  --headline "Инстаграм есть, а клиентов нет?" \
  --primary-text "<body copy, Russian, agency мы, no price>" \
  --budget 5
```

Read the printed payloads, then re-run with `--create`. It prints an Ads Manager link at the end. A
human turns the campaign on.

Options that matter:

- `--budget 5 --budget-type daily` (default) or `--budget 25 --budget-type lifetime --end-date 2026-08-01`
- `--countries TM` — geo, comma-separated
- `--cta LEARN_MORE|SIGN_UP|GET_QUOTE|CONTACT_US`
- `--no-ig` — drop the Instagram identity, Facebook placements only

## API gotchas found the hard way

- **`is_adset_budget_sharing_enabled=false`** is required on the campaign whenever budget lives on the
  ad set. Meta rejects the call without it. Found via `validate_only`, documented nowhere obvious.
- **`instagram_user_id`, not `instagram_actor_id`.** The latter is rejected with "must be a valid
  Instagram account id". The former passes field validation, but isn't fully confirmed — the app-mode
  error masks that check until the app is Live.
- **`OUTCOME_TRAFFIC`, not `OUTCOME_LEADS`, on a cold pixel.** Meta needs ~50 conversions/week to leave
  the learning phase; at the $2 CAC benchmark that's $100/week minimum. A $25 test optimized for
  conversions underdelivers and teaches nothing. Switch once conversion volume is steady.
- **`LANDING_PAGE_VIEWS`, not `LINK_CLICKS`.** Pays for people who actually loaded the page; filters
  accidental and bounce clicks. Uses the pixel's PageView.
- **Everything PAUSED.** The script builds structure. A human starts the spend.
