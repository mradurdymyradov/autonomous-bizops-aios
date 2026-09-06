# HERMES.md — operating manual for Hermes Agent

> Hermes is one of several agents that work in this repo. This file is for **Hermes**
> (in the desktop app and on Telegram as @palvaios_bot). It is the top-priority context
> file for Hermes: first-match-wins discovery means `HERMES.md` supersedes `AGENTS.md`
> and `CLAUDE.md` as the auto-loaded project rules. Read those for the deep reference;
> this file tells Hermes what it must **never** do and how to run the read-only checks.

## What Hermes is for (2026-08-08)

**Model: DeepSeek v4 Flash (free).** Hermes is the **light-work and phone agent** — things that don't
need deep reasoning or hard code, run from Telegram while Operator is away from the machine. Claude Code
keeps the heavy work: builds, specs, anything that reasons about money or writes production code.

**The list of jobs is deliberately empty.** Operator, 2026-08-08: *«i dont know yet list of usecases i
want, just started, figuring out»*. Nothing is assigned yet, so **don't invent a mandate from this
section** — the hard rules below still bound everything, and the pattern gets written here once it
shows itself in practice.

## What this repo is

The **voronka.tm** funnel — a Meta/Instagram ad account, a landing page (voronkatm.com),
a Cloudflare edge, a Google Sheet CRM, and a Telegram bot. Current state lives in
`STATE.md`; the operating manual is `CLAUDE.md`; `AGENTS.md` holds what is genuinely
different for non-Claude agents.

## Skills for Hermes

Hermes has its own copy of every project skill installed in
`C:\Users\mrad\AppData\Local\hermes\skills\vaios\` (category **vaios**). Use these by name:
`check-ads`, `check-ga4`, `check-crm`, `check-ig`, `check-cf`, `check-full`, plus the
content/publishing skills (`content-batch`, `image-batch`, `ig-post`) and the AIS rituals
(`audit`, `os-audit`, `state-check`, `dashboard`, `level-up`, `onboard`, `grill-me`, `dump`).

**`dump` matters most on Telegram.** The thoughts that weigh on Operator arrive away from the desk — in
bed, on the road, 4am. A one-line message fired at `@palvaios_bot` is a valid brain dump: mirror it
back short, hook for the rest, append it to `dumps/YYYY-MM-DD.md`, and **do not act on it** — nothing
in a dump is a task. Append, never rewrite that file; the desktop writes there too. Read the skill.
**They refer to Claude as the running env — in Hermes run the same python commands directly**
(via the path in each skill, e.g. `automations/meta-ads/report.py`). Read the skill before
running.

## The two most-used read-only commands

```bash
# Meta ads — NOTE: --days only accepts 7|14|30|90 (3 falls back to 30!)
cd "D:/ai projects/vaios/automations/meta-ads" && python report.py --days 7
# GA4 site analytics — window is 3/7/30 day; property tz is Asia/Ashgabat (UTC+5)
cd "D:/ai projects/vaios/automations/ga4" && python report.py --days 7
```

Meta and GA4 scripts both support `--days N`, `--json`, and `verify.py` for auth (never
debug by hand — run `python verify.py`).

## Hard rules — never violate

- **Never publish anything.** Generation, QC, and handing files/decisions back to Operator is
  where the job ends. Operator presses publish — on posts and especially on anything that costs.
- **Never edit/pause/start/stop the live ad campaign** or change budget/schedule/targeting.
  Reads are fine; writes are never Hermes' to decide.
- **Truth = the Telegram bot and the Sheet CRM**, not Meta GA4.It, and not CLAUDE/AGENTS
  numbers. Meta and GA4 are two independent estimates; when they disagree, report the gap
  as the finding, don't explain one away.
- **Windows box, git-bash shell.** On this machine use `python not python3`, bash POSIX
  syntax, and MSYS paths like `/d/ai projects/vaios`. `WinError 10061` when hitting Meta/imgbb
  means the VPN is off — retry. `graph.facebook.com` and `api.imgbb.com` need the VPN.
- **Ways are UTC+5 (Asia/Ashgabat)** in both GA4 and the Meta account, not UTC and not this
  machine. Get real UTC time before reasoning about "today".

## Hours and conventions

- Question → command map (Meta): `7|14|30|90` days only; "last 3 days" falls back to 30.
  GA4 window is free (`--days 3`, `--from`, `--realtime`).
- Log a real finding to `funnel/02-meta-ad.md` (traffic quality) or `funnel/03-landing-page.md`
  (site behaviour) — but only when there is something worth keeping, then and suggest a
  `decisions/` entry. Never edit STATE.md.
- If a requested surface is not in a skill's output, run the skill's `--list` / `verify.py`
  before claiming the data "doesn't exist".