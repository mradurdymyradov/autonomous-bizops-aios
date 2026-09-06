# Connections

Registry of every system your AIOS can reach. Filled by `/onboard` from Q4-Q7 answers; expanded over time as you wire new tools. `/audit` checks this file for domain coverage and freshness.

| # | Domain | Tool | Mechanism | Auth | Last checked |
|---|---|---|---|---|---|
| 1 | Revenue / Financials | Cash-in-hand ($0). Lead CRM is the Google Sheet, not a revenue ledger. | not yet connected | — | — |
| 1a | Lead CRM | Google Sheet «voronka» — tabs «Заявки», «Звонки», «Чат-лог», «Профили», «Звонки-архив» | script (`automations/sheets/crm.py`, read-only; `profiles.py` writes «Профили»; `calls.py` writes «Звонки») | shared service account (`automations/google-service-account.json`), Editor since 2026-07-28 | 2026-07-28 |
| 1b | Site analytics | GA4 property `voronka.tm` (544092543) | script (`automations/ga4/report.py`, read-only) | same shared service account | 2026-07-26 |
| 1b-1 | Client site analytics — roll-up | GA4 property `TM Market — roll-up` (548455744), Measurement ID **`G-0CTLGJFDG3`** — the cross-client Turkmen behavioural dataset. One web stream per client site; `hostname` separates them. **Mandatory second tag on all LPs.** | script (`automations/ga4/report.py`, read-only) | same shared service account, Viewer | 2026-08-04 |
| 1b-2 | Client site analytics — per client | GA4 properties: `NG Makeup` (`G-MHJV3BGP7N`), `SOKL EVENT` (`G-2E113SKW1C`) — client's, transfers at handover | script (`automations/ga4/report.py`, read-only) | same shared service account, Viewer | 2026-08-04 |
| 1b-3 | Meta Pixel — master dataset | Meta Pixel `1397681815558353` («voronka dataset») — cross-client seed dataset of all converting users. **Mandatory second pixel on all LPs.** | script (`automations/meta-ads/report.py`, read-only) | system user token (`automations/meta-ads/.env`) | 2026-07-22 |
| 1b-4 | Meta Pixel — per client | Client pixels: `NG Makeup` (`1594373485444518`), `SOKL EVENT` (`1701560878641069`) — client's, transfers at handover | script (`automations/meta-ads/report.py`, read-only) | same system user token | 2026-08-04 |
| 1c | Site — server side | Cloudflare zone `voronkatm.com` + Pages project `voronka` | script (`automations/cloudflare/report.py`, read-only) | Cloudflare API token `voronka-analytics-read`, Read-only scopes (`automations/cloudflare/.env`) | 2026-07-28 |
| 1d | Client sites — deploy | Cloudflare Pages, **six projects — five live, one dead**: `ngmakeup`, `himiahouse`, `verteratkm`, `voronka`, `sokl-event-tm`, plus **`skechers-tm` — an abandoned test, not a client** (confirmed by Operator 2026-08-08; it answers 200 and belongs to nothing) | `wrangler` CLI with `CLOUDFLARE_API_TOKEN` in the env — **not** `wrangler login` (see below) | Cloudflare API token, **write** scope. Lives at `clients/ng_makeup_stylist/.env.txt` — outside this repo and misnamed for what it actually reaches. That file holds **only** the token; there is no `CLOUDFLARE_ACCOUNT_ID` in it and none is needed — the token resolves to a single account on its own | 2026-08-08 |
| 2 | Customer interactions | Phone (primary), Instagram DM, Telegram DM | phone call log via manual XML export → `automations/sheets/calls.py` → «Звонки». DMs not connected | — (Android has no call-log API; export is the only path) | 2026-07-28 |
| 3 | Calendar | Google Calendar (inferred from Gmail) | not yet connected | — | — |
| 4 | Communication | Gmail (uncomplexed66@gmail.com), Telegram | not yet connected | — | — |
| 5 | Project / task tracking | File-based (this workspace) — no PM tool by design | not yet connected | — | — |
| 6 | Meeting intelligence | None — calls are direct/solo, no recorder | not yet connected | — | — |
| 7 | Knowledge / files | Local files on D:\ — this workspace, the **voronka LP repo at `D:\ai projects\voronka`** (`site/`, `functions/api/lead.js`, `functions/api/tg.js`), and the client build repos under `D:\ai projects\clients\<slug>\` | direct filesystem access — the paths are the connection | — | 2026-08-08 |
| 8 | Marketing / Publishing | Instagram @voronka.tm (feed, stories, carousels) | script (`automations/ig-poster/post.py`) | `.env` key + ref (`references/instagram-api.md`) | 2026-07-11 |
| 8a | Video generation | HeyGen — avatar video, voice cloning, TTS, translation, templates (`mcp.heygen.com/mcp/v1`) + HyperFrames composition agent (`/mcp/hyperframes`) | `mcp` — two claude.ai connectors, both OAuth. Desktop app only, not available to scripts | HeyGen **creator** plan, OAuth under `uncomplexed66@gmail.com`. See credit note below | 2026-08-08 |
| 8b | Image / video generation | Zark Lab — image and video generation/editing through `POST /v1/complete` | explicit-only `/zark` skill + `automations/zark.py`; reference: `references/zark-api.md` | `ZARK_API_KEY` in root `.env` (gitignored); account-scoped and metered | 2026-08-21 |

| 9 | Agents working this repo | **Claude Code** (desktop + CLI) — the heavy work — and **Hermes** (desktop + Telegram `@palvaios_bot`) on **DeepSeek v4 Flash (free)**, for light work and phone use while Operator is away. **Hermes' use cases are undecided as of 2026-08-08** — «just started, figuring out» | direct filesystem access to `D:\ai projects\vaios`. Each reads its own manual: `CLAUDE.md` / `HERMES.md`, with `AGENTS.md` for what differs for non-Claude agents | — (local, no API between them) | 2026-08-08 |

**Mechanism options:** `mcp` (MCP server), `script` (Python/Bash hitting an API, in `scripts/`), `export` (CSV/JSON dump pipeline), `key+ref` (`.env` key + `references/{tool}-api.md` guide), `not yet connected`.

**Row 9 — the second agent is a copy, not a client.** Hermes reads the same repo but runs its **own
copy** of the skills at `%LOCALAPPDATA%\hermes\skills\vaios\`. Editing a skill in `.claude/skills/`
does **not** reach Hermes; its `hermes-skill-sync` skill reconciles the two, and drift between them
is a real failure mode (`argument-hint` has gone missing from its copies before). `HERMES.md`
supersedes `CLAUDE.md` for that agent by first-match-wins, so a rule that must bind every agent has
to land in both files.

**One Google credential serves rows 1a and 1b.** Service account
`voronka-reader@voronka-data.iam.gserviceaccount.com` (Cloud project `voronka-data`,
Sheets API + Analytics Data API enabled), key at `automations/google-service-account.json`,
gitignored. Granted Viewer on the sheet and Viewer on the GA4 property — read-only on both.
Rebuild instructions: `automations/sheets/README.md`.

**Row 1d — `wrangler login` does not work from here, and that is not a credential problem.**
Cloudflare bot-challenges the VPN exit (Helsinki) on the dashboard OAuth and `/user` endpoints:
`wrangler whoami` dies with a 403 HTML challenge page even when auth is perfectly valid, and the
stored OAuth token in `%APPDATA%\xdg.config\.wrangler\config\default.toml` cannot refresh for the
same reason. The Pages REST API on `api.cloudflare.com` is **not** challenged. So: export
`CLOUDFLARE_API_TOKEN` and every `wrangler pages …` command works.
Never diagnose this as "not logged in" — that is the symptom, not the cause.

Deploy, from the client's build repo:

```bash
npx wrangler pages deploy site --project-name <project> --branch main --commit-dirty=true
```

Expect intermittent `522` on individual assets straight after a deploy — that is the 2–4 Mb/s VPN,
not a broken upload. Retry before touching anything.

⚠ **The write token is homed badly.** It sits in `clients/ng_makeup_stylist/.env.txt`, a file whose
name suggests it belongs to one client while it actually holds the key that can redeploy every site
we run. Worth moving to `automations/cloudflare/.env.deploy` and re-pointing this row — The call,
not done yet.

**Row 8a — HeyGen burns a metered budget, unlike every other row here.** All the other connections
are read-only or cost nothing per call. HeyGen is not: `create_video_agent`, `create_video_from_*`,
`clone_voice`, `create_video_translation` and HyperFrames' `render_video` all spend **premium
credits** from the Creator plan, and the pool resets monthly. Check the balance with
`get_current_user` before generating; at 2026-08-08 it stood at **600, resetting 2026-08-23**.
`list_*` and `get_*` are free. Never generate without Operator asking — and never in a loop.

Both servers are **claude.ai connectors**, so they exist only inside the desktop app. Nothing in
`automations/` can reach HeyGen; don't write a script that assumes it can.

Russian TTS is well covered (Anya, Nadia, Larisa; Dmitry, Oleg, Andrei, Arcadias — all support
`pause` tags for ad-script pacing). Turkmen is not a listed voice language — check before promising
a client Turkmen-language video.

When you wire a new tool, also save `references/{tool}-api.md` capturing endpoints, auth flow, and common queries — researched-once-saved-forever.
