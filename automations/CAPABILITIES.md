# Capabilities — what the machine can already do, and what it can't

One page for the question "can we get X?" Reference, not state: **no live numbers here.** Current
results live in [STATE.md](../STATE.md); why past calls were made lives in
[decisions/log.md](../decisions/log.md).

Everything below was tested against the live APIs, not read off documentation. Dates say when.

---

## 1. What we have

| System | We can | Tool | Credential |
|---|---|---|---|
| **Meta Ads — read** | spend, CPC, CTR, reach, actions, per-campaign/adset/ad status, **audience breakdowns** (age, gender, placement, device, region) each ranked by cost per lead | `/check-ads`, `--who` | ads system-user token |
| **Meta Ads — write** | create campaigns, ad sets, upload images. **Cannot create ad creatives → cannot create ads.** | `meta-ads/campaign.py` | same |
| **Instagram — organic read** | profile, 13 account totals, daily reach, 6 breakdown combos incl. **paid vs organic split**, 10 per-post metrics, comment text, live story metrics, publishing quota, **competitor accounts via business_discovery** | `/check-ig` | ads token + page token |
| **Instagram — publish** | feed posts, carousels, stories, 100 posts/24h | `/ig-post` | page token |
| **Site analytics** | totals, day-by-day, hour-of-day, acquisition, events, pages, geo, tech, demographics | `/check-ga4` | Google service account |
| **CRM (truth)** | every lead, phone, ad creative, chat answers, call outcome, speed-to-call | `/check-crm` | same service account |
| **Call history** | every call to and from a lead — who was dialled, when, talk time, callbacks, missed calls, speed-to-lead. Sourced from the phone's own log, **not live** (see §D) | `sheets/calls.py`, read through `/check-crm` | service account (Editor) + a manual XML export |
| **Lead profile lookup** | the lead's own Instagram: followers, posting cadence, days since last post, median likes, **ER**, Reels share, and the **captions + permalinks + `view_count`** of recent posts — written into the «Профили» tab | `sheets/profiles.py` | ads token + service account (Editor) |
| **Site — server side** | edge requests, page views, uniques, status codes, country, content type, and `/api/lead` invocations + errors — **counted before any JavaScript runs**, so it sees what GA4 and the pixel structurally cannot | `/check-cf` | Cloudflare read-only API token |
| **History (all five)** | one stored row per Ashgabat date folding every reader together, plus the end-to-end funnel off it. **The only durable memory in the system** — every API here ages its window out, so unsnapshotted days are gone for good | `/check-full` (`snapshot.py` + `funnel.py`) | all of the above |
| **Image generation** | brand-law-compliant batches → 9:16 fit → publish | `content-batch`, `img-gen/` | Gemini key |
| **Zark media generation** | explicitly requested image/video generation and editing; streams assistant output and generated file IDs | `/zark`, `automations/zark.py` | Zark account API key |

**Only the CRM is truth for заявки.** Meta, GA4 and Cloudflare are estimates of the same reality and
disagree with it and each other. When a question spans two, run both and reconcile out loud instead of
reporting two stories.

**Cloudflare is truth for one narrow thing: did the request arrive.** It sits upstream of every tag,
so when Meta and GA4 disagree about volume it is the only surface that can say which one is wrong.

### Credentials

| Credential | Where | Expiry | Risk |
|---|---|---|---|
| Meta system-user token (`vaios-adsbot`) | `meta-ads/.env` | **never** | **can spend from the Mastercard on file. Treat as a password.** |
| Meta page token | `ig-poster/.env` | **never** | can publish as the brand |
| Google service account | `automations/google-service-account.json` | n/a | read-only on GA4; **Editor on the Sheet since 2026-07-28**. Two scripts take the write scope and each owns one tab — `sheets/profiles.py` → «Профили», `sheets/calls.py` → «Звонки»/«Звонки-архив». Nothing writes «Заявки» or «Чат-лог»; `crm.py` stays `readonly` |
| Cloudflare API token (`voronka-analytics-read`) | `cloudflare/.env` | none set | **read-only by construction** — Analytics/Zone/Pages *Read* only. Cannot edit DNS, deploy, or change a Worker. Never reissue it with Edit. Created 2026-07-28; **the value was pasted into a chat, so rotate it when convenient.** |
| **Cloudflare deploy token** | `D:\ai projects\voronka\.cf-deploy.env` — **outside this repo**, which is why it keeps getting missed | none set | `Account · Cloudflare Pages · Edit`, account-wide. **This is the one that ships a site.** It creates projects and deploys to any of them, not just `voronka` — used for `ngmakeup` on 2026-07-29, `verteratkm` on 2026-07-31. Cannot touch DNS, Workers or analytics. ⚠ **Its value was printed into a chat on 2026-07-31 (a masking regex failed) — ROTATE IT.** Account-wide Pages·Edit means whoever holds it can overwrite `voronka` itself, i.e. the live lead-gen site. Rotate together with `voronka-analytics-read`, which has the same problem, and update the `.env` file after. |
| imgbb, Gemini | `ig-poster/.env` | n/a | low |
| Zark account API key | root `.env` | unknown | can consume generation credits and create files in the Zark workspace; use only on explicit `/zark` requests |

**Deploying a client landing page** (2026-07-29, learned the slow way):

```bash
set -a && . "/d/ai projects/voronka/.cf-deploy.env" && set +a && cd "<client folder>" && npx wrangler pages deploy --project-name <name> --branch main --commit-dirty=true
```

**A brand-new client needs the project created first, or the deploy above dies with
`Project not found … [code: 8000007]`** — which reads like a token/permission failure and isn't
(learned on `verteratkm`, 2026-07-31). One command, once per client:

```bash
set -a && . "/d/ai projects/voronka/.cf-deploy.env" && set +a && npx wrangler pages project create <name> --production-branch main
```

`--project-name` is what decides the URL (`<name>.pages.dev`); the `name` field in `wrangler.jsonc`
does not. Keep them identical anyway so the folder can't drift from what's live.

**A fresh Pages project has no env vars, and `/api/lead` fails OPEN** — it answers `{"ok":true}`
with both sinks skipped, so a form on a new deploy looks like it works and silently drops every
lead. Check before demoing anything:

```bash
curl -sS -X POST "https://<name>.pages.dev/api/lead?debug=1" -H 'Content-Type: application/json' -d '{"type":"lead","phone":"+99361000000"}'
```

`"status":"skipped"` on either sink means nothing is being recorded.

`wrangler.jsonc` carries `pages_build_output_dir`, so no path argument — that is also what makes
`functions/` deploy alongside `site/`. **`npx wrangler login` does not work on this connection:**
`dash.cloudflare.com` serves wrangler's OAuth exchange a 403 bot-challenge page through the VPN exit
(Ray IDs `…-FRA`, 3/3 attempts). `api.cloudflare.com` answers fine, so the API token is not a
workaround for a broken login — it is the only route. Don't burn an evening on the login.

All gitignored. `ig-insights` deliberately holds **no** credential of its own — it borrows both Meta
tokens, so there's one less copy of a token that can spend money.

---

## 2. What's blocked, and what actually unlocks it

Sorted by whether anything can be done about it.

### A. One wall, three consequences — Meta business verification

| Blocked | Error | What it costs us |
|---|---|---|
| **Ad creative creation** → `campaign.py` can't finish a campaign | code 100 / subcode 1885183, "app must be public" | every campaign gets built by hand in Ads Manager |
| **Hashtag search** (`ig_hashtag_search`, top/recent media) | code 10, needs "Instagram Public Content Access" App Review | no competitor/market listening, no trend research |
| **Instagram DMs** (`conversations`) | code 3, "Application does not have the capability" | DM leads can't be read or answered programmatically |

All three are the same wall: **the app `automation_1` is unpublished → publishing requires business
verification → verification requires a registered legal business.**

**This is not a token problem.** Proven 2026-07-26: the ads token already carries
`instagram_manage_messages` and the DM call still fails, on both tokens. The permission sits on the
token; the *capability* sits on the app. Issuing a new token with more scopes changes nothing. Don't
spend an evening on it.

**Already ruled out** (full detail in [meta-ads/README.md](meta-ads/README.md), don't re-run this
research): every verification connection method funnels to the same document upload, which accepts only
bank statement / business registration / tax document / articles of incorporation. No passport path, no
national-ID path, no sole-proprietor path. Domain verification doesn't substitute. Trimming use cases
does nothing. The "Standard Access" theory is wrong. Blog posts describing document-free workarounds
are fabricated.

**The unlock:** a TKM-registered business — either Operator registers one, or **someone whose portfolio is
already verified attaches our app `automation_1` to it.** That normally arrives with the first paying
client, but any verified portfolio does it.

**Precision that matters:** partner access to someone's *ad account* unlocks nothing — the creative
block sits on our app, not on any ad account. The app has to be attached to a **verified Business
Portfolio**. When an offer of access appears, run the procedure in
[meta-ads/partner-portfolio.md](meta-ads/partner-portfolio.md) (`partner.py` is the read-only check)
before anyone clicks anything in Business Settings.

### B. Meta policy — no unlock exists

| Blocked | Note |
|---|---|
| `view_count` on **our own** media | code 36104. Readable on *other* accounts through business_discovery. No permission grants it on ours. |
| Shopping / catalog endpoints | We sell a service. Nothing there to want. |
| `impressions` | Deleted by Meta in v22.0. `views` replaces it — already in use. |

### B2. Claude's own sandbox — narrower than this section claimed until 2026-08-07

| Path | What actually happens |
|---|---|
| `curl` / `wget` **in the Bash tool** | **Blocked.** The request is intercepted and a **block page comes back in place of the file** — `curl -o img.png` writes 2 KB of HTML that *looks* like a successful download. Verified 2026-08-02 against a Wikimedia image. |
| **`WebFetch`** | **Never returns bytes.** It converts pages to text and answers a prompt against them. Reading *about* an image ≠ having it. |
| **Python `requests`** (the stack all of `automations/` runs on) | **NOT blocked.** Verified 2026-08-07: pulled a client's avatar and 24 Reel covers off the Instagram CDN as real JPEGs, and later a complete `.ttf` from `raw.githubusercontent.com`. |

**Correction, 2026-08-07.** This section used to read «Claude **cannot** source product photos, logos,
or any asset off the web» — full stop. That was generalised from one `curl` test to *every* fetch
path, and it was wrong. It cost real decisions: SOKL's `spec.md` marked its palette «ждёт файлов от
Operator» and shipped an **invented** plum-and-amber instead, when the palette was sitting in their
avatar the whole time and could have been measured on day one.

**The rule that replaces it:** when something has to come off the internet as bytes, **try Python
before declaring it impossible** — `requests` + `fontTools`/`PIL` reaches CDNs, Google Fonts and
GitHub raw. Downloaded images can then be read with the Read tool, so colour can be *measured*
rather than guessed.

**The trap is still real, and now it matters more:** the `curl` failure is silent — exit 0, file
exists, plausible size, HTML inside. **Any pipeline that downloads assets must sniff the file's
magic bytes, not the exit code.** (`profiles.py` does; the SOKL research script checks `\xff\xd8\xff`
before writing.)

**What still needs Operator:** anything not reachable from a public URL — photographs he has to *choose*
or shoot, stills pulled from the middle of a Reel (the API hands over cover frames only, and those
are 60–80 % covered in graphics), and anything behind a login. Claude selects, specs and writes the
markup; for those it still cannot obtain the file.

### B3. HeyGen — the **API key** cannot spend the subscription, but **OAuth/MCP can.** Verified 2026-08-22

**Solved. Use the MCP server, not the API key.** This section stays because the dead end is one
line away from the working path and the error message does not say which.

| Path | Auth | Sees | Result |
|---|---|---|---|
| `api.heygen.com` REST | `X-Api-Key` (`.env.heygen`) | wallet, $0.00 | **HTTP 402 `insufficient_credit` on every generate** |
| `https://mcp.heygen.com/mcp/v1` | browser OAuth | **subscription, Creator plan** | **works — renders and bills plan credits** |

**Proven end to end 2026-08-22:** a 9:16 720p Avatar IV clip in The cloned voice rendered to a
finished mp4 + `.srt`. **6.84 s cost 3 credits**, ~7 min wall clock. `get_current_user` over OAuth
returns `billing_type: subscription`, `plan: creator`, `premium_credits.remaining: 600` — where the
same account over the API key returns `billing_type: wallet`, `remaining_balance: 0.0`,
`subscription: null`. **Same account, two truths, decided entirely by which credential asks.**

Connect it with `claude mcp add --transport http -s user heygen https://mcp.heygen.com/mcp/v1/`
then authenticate via `/mcp` in an interactive terminal. **Check `claude mcp list` first** — a
`claude.ai HeyGen` connector may already be registered and a second entry just duplicates every tool.

Useful ids: photo-avatar look `f7a4ab98ba0c44b98680fab0f72a6d29` ("Casual Hand Gesture Guide",
portrait 768×1364, has a motion-reference preview) with The cloned voice
`cc5f5e000c474477bec211500221293c`. All private looks support `avatar_iii`/`iv`/`v`.

**Credits do not roll over — they reset monthly and unspent ones are lost.** `resets_at` on
`get_current_user` is the real deadline, not the billing date anyone remembers.

Everything below is why the API-key path fails, kept so it isn't re-derived.

**The subscription and the API are two separate wallets, and the key only sees the empty one.**
`GET /v3/users/me` returns `billing_type: wallet`, `remaining_balance: 0.0`, `subscription: null`.
The legacy `GET /v2/user/remaining_quota` returns `remaining_quota: 0` alongside `plan_credit: 600` —
the plan allotment is real but it is **Studio-only credit**, not API credit. API rendering is
usage-based and bills the wallet, which has never been topped up.

**This is not a key problem and not a scope problem.** The same key reads everything fine —
1 264 stock avatars, 7 484 talking photos, the 6 custom avatar groups (`mra` 8 looks, `aimra` 7,
`sezam` 3, plus `M.H`, `vel`, `aimra 2`), voices, and full video history. **Read is open, write is
closed.** Only money on the wallet opens write; nothing about permissions or a reissued key will.

**Confirmed on v3 too, with the documented schema — it is not a schema problem.** `POST /v3/videos`
with the flat body (`type: avatar`, `avatar_id`, `script`, `voice_id`) returns the same 402 across
**all three engines** (`avatar_iii`, `avatar_iv`, `avatar_v`) and for a **stock** avatar as well as
our own. Read stays open throughout. The gate is the wallet, nothing else.

**What actually unlocks it: about $15.** API rendering is pay-as-you-go per second of output —
Avatar IV Photo Avatar **$0.05/sec**, Avatar III Photo Avatar **$0.0433/sec**, Avatar III Digital
Twin / Studio **$0.0167/sec**. A 25-second Reel is therefore **$1.25 on Avatar IV, $0.42 on Avatar
III**; ten of them run **$12.50 / $4.20**. Wallet balance is self-serve, has no monthly commitment,
and **does not expire** — unlike the Studio plan credit, which does.

**The subscription credits are reachable programmatically only over OAuth, not an API key.** HeyGen's
own docs split it: API keys bill API plans (the wallet), OAuth draws on subscription credits and is
scoped to small test generations. OAuth needs an app registration and a browser consent flow, so it
is not a same-day path — noted here only so nobody reads "subscription: null" as a broken key.

**Don't re-derive the endpoint set either.** `v1/user/remaining_quota` is 404. `v2/audio/tts` is 404
— standalone TTS does not exist on this account's API, which is why `automations/heygen_tts.py`
never worked; ElevenLabs (`elevenlabs_tts.py`) is the TTS path. `v2/video/av4/generate` wants an
`image_key`, not a `talking_photo_id`. `v3/videos` takes a different request schema than v2 and the
v2 body is rejected with `Unable to extract tag using discriminator 'type'`. All v1/v2 endpoints
sunset **2026-10-31**; the live spec is `https://developers.heygen.com/llms.txt`.

### C. Unlocks itself with scale — do nothing

| Blocked | Gate |
|---|---|
| Follower / engaged / reached demographics (country, city, age, gender) | ~100 followers. Account has 29. |
| `follows_and_unfollows`, daily `follower_count` | same volume gate |

Empty here means small, **not broken**. There is nothing to debug. And the demographic question has a
side door that already works: **`/check-ads --who` reads audience demographics off the Marketing API,
which ignores follower count entirely.**

> **Standing rule this taught us:** when Instagram won't give something up, check whether the Marketing
> API answers the same question first. Two APIs, different gates, same underlying data.

### E. `business_discovery` quirks — verified 2026-07-28, don't re-derive

- **It is CASE-SENSITIVE**, though Instagram usernames are not. `Lmd_brend_shop_tm` → `Invalid user
  id`; `lmd_brend_shop_tm` → 32,820 followers. Lowercase every handle before asking.
- **There is no username search.** The Instagram app matches fuzzily; the Graph API only does exact
  lookups, and `ig_hashtag_search` is behind the same App Review wall as everything in §2A. A
  mistyped handle can only be repaired by rule-based candidates or by the lead themselves.
- **`view_count` works here** — blocked on our own media (§2B), readable on any discovered account.
- **Candidate generation multiplies calls.** Up to 8 lookups per lead hits `(#4) Application request
  limit reached`, the app's hourly budget, within a few full runs. That error is a *budget*, not a
  verdict: never write it into a record as "not found" (`sheets/profiles.py` treats it as fatal and
  aborts the run for exactly this reason).

### D. Ours to fix — actually actionable

| Gap | Fix | Cost | Owner |
|---|---|---|---|
| **`generate_lead` isn't a key event in GA4** — the event fires but every conversion-rate metric reads 0 by config | GA4 → Admin → Events → toggle "Mark as key event" | ~1 min, browser | **Operator** |
| **Story insights die at 24h**, no historical endpoint. Uncaptured = gone forever | `ig-insights/report.py --snapshot` on days stories go up | 30 sec | Operator / could be scheduled |
| **Call *outcomes* still aren't logged** — the calls themselves now come off the phone log (`sheets/calls.py`), but whether the lead said yes is only in The head. `Итог` is a dropdown in «Звонки» and survives rebuilds | pick the dropdown after a call | ~3 sec | **Operator** |
| **Call data isn't live** — it's an XML export from the phone, so «Звонки» is as stale as the last export. Android exposes no call log to any API; nothing to fix at the credential layer | re-export from SMS Backup & Restore → Call logs, rerun `calls.py` | ~2 min | Operator, when calls matter |
| ~~**No server-side view of the site**~~ | **closed 2026-07-28** — token `voronka-analytics-read` created, `/check-cf` live and returning real numbers | — | done |
| **API version pin is inert** | none needed — Meta serves v25.0 for every version asked for. Documented so it isn't re-investigated. | — | done |

### F. Looks like a gap, isn't — don't build these

**A Telegram reader (`check-tg`) is not worth a session.** This page previously listed it as
actionable on the grounds that "the bot is half of truth and nothing queries it." That was
overstated, corrected 2026-07-28:

- **Telegram holds no unique data.** `functions/api/lead.js` sends the *same payload* to the
  Telegram bot and to the Apps Script webhook ([funnel/04-lead-capture.md](../funnel/04-lead-capture.md)).
  The Sheet is a persistent copy of what the bot receives, and `/check-crm` already reads it.
- **The Bot API cannot retrieve history anyway.** There is no endpoint for "messages this bot
  sent." `getUpdates` only drains a short-lived queue, and it is disabled outright while a
  webhook is registered — which it is, on @voronka_leadsbot.
- **What Telegram uniquely held was the call-tracking button taps**, and that feature was turned
  off 2026-07-27 for our own funnel ([STATE.md](../STATE.md)). It survives for client builds.

If a Telegram reader ever becomes worth it, the route is logging at write time in the Worker, not
reading back from Telegram. Don't spend an evening discovering the Bot API's shape.

---

## 3. If you only do one thing

**The GA4 key-event toggle.** One minute in a browser, and it turns every conversion-rate number in
`/check-ga4` from a false zero into a real figure. It is the only item on this page that is both free
and immediately wrong-to-leave.

**The Cloudflare token is done and the question it was built for is answered (2026-07-28): there was
never a click→page leak.** GA4 logged 271 Paid Social sessions against Meta's 264 link clicks for
`test01` — Meta's `landing_page_view` pixel undercounts by ~44%, the page was always fine. See
[decisions/log.md](../decisions/log.md). Note that GA4, not Cloudflare, produced the decisive number;
Cloudflare `pageViews` is bot-inflated ~7× on Free and is a ceiling, not a count.

Everything under §2A waits on a registered business and should not be pushed on. Everything under §2C
waits on followers. Neither is a place to spend an evening — **the gate to revenue is traffic and
delivered pilots, not tooling.**

---

*Verified 2026-07-26 against live APIs: token scopes via `debug_token`, every blocked endpoint
re-called, version behaviour confirmed via the `facebook-api-version` response header.*
