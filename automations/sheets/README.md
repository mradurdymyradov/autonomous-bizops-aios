# Sheets CRM toolkit — voronka

Structured access to the Google Sheet the landing page writes into. Mirrors
`automations/ga4/` and `automations/meta-ads/` in shape: `.env` next to the
scripts, `verify.py` health-checks, `crm.py` reads.

| file | what it does |
|---|---|
| `crm.py` | folds the event log into one record per lead; summary, tables, or JSON. **Read-only** |
| `profiles.py` | looks up each lead's Instagram account, writes a profile grid into «Профили». **Writes only that tab** |
| `calls.py` | rebuilds «Звонки» from The phone call log. **Writes only «Звонки» + «Звонки-архив»** |
| `notes.py` | parses The hand-written call log into «Заметки», classified. **Writes only that tab** |
| `note-overrides.json` | pins an `L{n}` note to a Lead ID when the positional match is wrong |
| `phone-overrides.json` | phones «Заявки» never captured, confirmed by Operator — read by `calls.py` |
| `verify.py` | fails loudly on the exact broken line of setup |
| `.env` | sheet ID + path to the shared service account key (gitignored) |

## Why this exists

The sheet is an **append-only event log**, not a CRM table. One row per phone
submit, one row per chat answer, one row per call-button tap — all interleaved
in «Заявки» and «Звонки», joined only by `Lead ID`. That shape is correct for a
webhook and useless for reasoning about leads.

`crm.py` reassembles it: one record per lead, carrying phone, ad creative from
the UTM, the three chat answers, call outcome, and speed-to-call. Duplicate
phone submits are marked, not double-counted. Bot-generated «напоминание» rows
are excluded from "did anyone call this person".

The Google Drive MCP connector can also open this sheet, but it returns the
whole file as one text blob — no per-tab targeting, no filtering, and it does
not work from a script or a cron job. That is what this replaces.

## Setup

Already done (2026-07-26). It took one shared Google Cloud service account:

- Project `voronka-data`, Sheets API + Analytics Data API enabled.
- Service account `voronka-reader@voronka-data.iam.gserviceaccount.com`.
- Its JSON key at `automations/google-service-account.json` — **shared with the
  GA4 toolkit**, one credential for both. Gitignored by `*service-account*.json`.
- The sheet shared with that address as **Редактор (Editor)** — widened from
  Читатель on 2026-07-28 so `profiles.py` can write «Профили». `crm.py` and
  `verify.py` still take `spreadsheets.readonly` and cannot write whatever the
  sharing setting says; only `profiles.py` asks for the write scope, and
  `GUARDED_TABS` in it refuses «Заявки», «Звонки» and «Чат-лог» outright.

To rebuild from scratch, or if the key is lost: create a new key under IAM →
Service Accounts → `voronka-reader` → Keys, drop it at the path above, then
re-share the sheet if the account was also deleted. `python verify.py` names
whichever step is broken.

```bash
cd "D:/ai projects/vaios/automations/sheets" && python verify.py
```

## Using it

```bash
python crm.py                       # last 7 days, summary
python crm.py --days 30
python crm.py --from 2026-07-23 --to 2026-07-26
python crm.py --all                 # every row in the sheet
python crm.py --leads               # one line per lead
python crm.py --calls               # every real call + speed-to-call + talk time
python crm.py --notes               # what each lead said, grouped by outcome
python crm.py --chat                # «Чат-лог» session telemetry
python crm.py --json                # machine-readable
python crm.py --raw Заявки          # untouched rows, when you distrust the parse
python crm.py --with-tests          # keep probe rows (hidden by default)
```

## Knowing the lead's Instagram — `profiles.py`

The lead types a handle into the landing chat. `profiles.py` takes it, pulls
the account through Meta's `business_discovery`, derives the numbers that
decide how it gets sold to, and writes a row into a fourth tab, **«Профили»**,
keyed by Lead ID:

| Lead ID | @профиль | подписчики | подписки | постов | последний пост | постов/мес | медиана лайков | ER% | доля Reels | имя | био | сайт | статус | обновлено | скрин | url скрина | данные |

```bash
python profiles.py                  # leads of the last 7 days with no profile row yet
python profiles.py --all            # every lead that ever gave a handle
python profiles.py --refresh        # re-fetch rows that already exist
python profiles.py --handle x       # one account, ad hoc, no lead needed
python profiles.py --dry-run        # print the rows, sheet untouched
python profiles.py --grid           # also build + upload the profile-grid image
python profiles.py --json           # stats + captions, structured
```

`crm.py` folds «Профили» back into each lead as `profile: {handle, followers,
posts, stats{…}, recent_posts[…], status}`, so `--leads`, the summary and
`--json` all carry it. The tab is optional — if it doesn't exist, `crm.py`
degrades to printing the raw chat answer and saying "not looked up yet".

## What they said on the phone — `notes.py`

The richest thing anyone knows about these leads was never in the sheet. It is
in `leads-log.md`, beside it: what each person actually said, in Turkmen and
Russian, typed by hand after the call. «Звонки» knows a call lasted four
minutes; only that file knows it ended in «дорого, я подумаю».

`notes.py` parses it, matches each note to a lead, classifies it, and writes a
fifth tab, **«Заметки»**:

| Lead ID | № | телефон | бизнес | категория | возражение | перезвонить | заметка | оригинал | обновлено |

```bash
python notes.py                     # parse the log, rewrite «Заметки»
python notes.py --dry-run           # print the table, sheet untouched
python notes.py --check             # just the L-number → lead match
python notes.py --json              # structured
```

**The tab is derived, so it is rewritten whole every run.** Never fix a cell in
the sheet — fix the log file and re-run, or the next run undoes it.

**The match is positional, and that is the one thing to distrust.** The log
numbers leads `L1..L61`; those are not the sheet's Lead IDs. `L{n}` is the
n-th **real** lead chronologically — test rows and duplicate submits excluded,
the same list `crm.py` calls "real leads". Verified against three independent
anchors before any of this was written:

- `L12` «Наргиля MAKEUP & HAIR» → real lead #12 = `@ng_makeup_stylist`
- `L14` «стоматолог, не взял» → real lead #14 = `@estetic_dental_ag`, no answer
- `L61` «Не взял» → real lead #61, the last one, no answer

and the counts agree: 61 real leads, highest note `L61`, one gap (`L5` was
never written). It drifts only if a lead is inserted **before** an already
numbered one, or a new duplicate is detected inside the old range. Two
defences: every row carries the phone and business so a wrong match is visible
at a glance, and `note-overrides.json` pins any number by hand:

```json
{ "L5": "L1784875363313" }
```

`--check` prints the whole mapping plus every lead with no note yet, which is
the fastest way to see the log fall behind the sheet.

Категории are keyword buckets over the Russian «Смысл» line — a reader for one
file, not an intent model, meant to be extended by pasting in the next real
phrase. One rule in it is worth knowing: **«не взял» only wins when nothing
happened after it.** That single positional check separates L7 («перезвоните
через час» — перезвонил, не взяла → нет ответа) from L27 (не взял сначала,
потом «завтра позвоню» → думает).

`crm.py` folds the tab back in as `note: {category, objections[], follow_up,
text}` and adds `--notes`, a callback list grouped by outcome. Optional like
«Профили»: no tab, no error.

### What the fields buy, and why these ones

- **`последний пост` + `постов/мес` — the strongest qualifier on the row.** A
  shop that hasn't posted in four months is a different sale ("we'll run the
  account") from one posting daily ("we'll bring you traffic"). That fact
  currently surfaces four minutes into a call.
- **`ER%` is a median, never a mean.** One post that took off rewrites a mean
  and invents engagement the account doesn't have. Read against follower count
  it catches bought audiences — the first real lead through it, `@uakeen.tm`,
  came back 6,018 followers / 60 posts a month / **median 2 likes, ER 0.05%**.
  That is the entire reason they get no заявки, and it's the opening line of
  the call.
- **`view_count` is in there** — Meta blocks it on *our* media (§2B in
  `../CAPABILITIES.md`) and hands it over through `business_discovery`. We can
  see a prospect's real Reels reach when we can't see our own.
- **`данные` (column R) is the machine payload**: stats plus one entry per
  recent post — `{permalink, type, ts, likes, comments, views, caption}`.
  Captions are the richest signal in the row: what they sell, whether prices
  and a CTA are there, which language they write in. No number holds that. The
  visible columns are a rendering of the same thing for Operator.
- **`permalink`, not a screenshot.** An earlier version composited the profile
  grid into an image on imgbb. Pixels buy an agent nothing a counter doesn't
  say better, and the grid cost twelve image downloads per lead on a 2–4 Mb/s
  VPN. A permalink never expires (`media_url` does), so one specific post can
  be pulled on demand instead of twelve up front. `--grid` still builds the
  image when the visual actually matters; `скрин` holds `=IMAGE("…")` and
  `url скрина` the same URL as text, because **an image pasted over the sheet,
  or inserted "in cell", is invisible to the values API** — those cells come
  back empty, and a floating image anchors to pixels rather than to a row.
- **A separate tab.** «Заявки» is an append-only event log written by a
  webhook. Per-lead enrichment does not belong on an event row. «Профили» is
  keyed by Lead ID, exactly the way `crm.py` already joins «Звонки».

## Knowing what actually happened on the phone — `calls.py`

«Звонки» was built to be fed by outcome buttons in the Telegram bot. Operator almost
never tapped them, so the tab filled with «напоминание» rows the Apps Script
timer wrote itself plus a few probes on his own number, and every real lead read
as uncalled. He had in fact dialled 59 of 60 — the record was on his phone.

So the phone's call log is the source, and `calls.py` is the importer. Export on
the phone with **SMS Backup & Restore → Set up a backup → Call logs**, copy the
XML to the PC, then:

```bash
python calls.py --xml ~/Downloads/calls-20260728004034.xml --days 5
python calls.py --xml FILE --all          # every lead in the sheet
python calls.py --xml FILE --dry-run      # print the table, write nothing
```

It rewrites «Звонки» as **one row per lead**: first call, minutes from заявка to
that call, attempts, whether they talked, how long, whether the lead rang back,
missed calls from them, and a readable chain of the whole thing in `Хронология`.
`Итог` is a dropdown for Operator — only «Не дозвонился» is pre-filled, because that
one the call log proves and the rest it can't.

- **It is a rebuild, not an append.** Rerun it after each export; the tab is
  fully regenerated from «Заявки» + the XML, so there is nothing to reconcile.
  **`Итог` and `Комментарий` are read back and carried across** — they are the
  two columns a human owns, and regenerating them would delete his work. Every
  other column is derived and will be overwritten.
- **The old event rows went to «Звонки-архив»** on the first run, in their
  original shape, and are never touched again. Nothing was deleted.
- **Matching is on the last 8 digits** — the subscriber part. The sheet writes
  `+993 61 59 42 38`, the phone writes `+99361594238`.
- **Duplicate phones get their calls on the earliest submit**, matching how
  `crm.py` dedups, and giving the honest speed-to-lead — from the first time
  they raised their hand, not the second.
- **Column `№` is The own contact label** (`L1`, `L2`, …), because that is how
  he refers to a lead out loud. A number he saved as a lead but that isn't in
  «Заявки» is reported, never guessed into a row.
- **`phone-overrides.json` fills phones the form never captured.** A заявка can
  arrive with no number when the chat fires but the submit doesn't land. The
  script will not infer the missing phone from a contact label that happens to
  fit a gap in the numbering — that is a guess, and a guessed phone in a CRM is
  worse than a blank one. Confirmed answers go in the file, keyed by Lead ID,
  with a `why` recording how it was confirmed. It only ever fills a blank; a
  phone already in «Заявки» is left alone and the disagreement is logged.
- **`Комментарий` is shared between script and human**, so the hidden JSON
  carries `auto_note` — what the last run wrote there. A note matching it is
  regenerated; anything else is The and is preserved. Without that, a stale
  generated note outlives the condition it described and reads as his.
- **Column `JSON` is hidden and machine-readable**, same trick as «Профили»:
  the per-call chain plus derived stats, which is what `crm.py` reads back.

## Things that will bite you

- **Timestamps are `DD.MM.YYYY`, Ashgabat local.** Not ISO, not UTC. `parse_dt`
  handles it; anything reading `--raw` must not assume month-first.
- **«Заявки» starts 2026-07-24.** Leads from 22–23.07 were cleared out of that
  tab but **their call rows still sit in «Звонки»**, so the two tabs disagree on
  history. `crm.py` only reports leads that exist in «Заявки»; orphan call rows
  are ignored rather than invented into leads.
- **A lead with no phone row is possible.** If the chat fired but the submit
  didn't land, only `chat_answer` rows exist. Those records show `phone: ""`.
- **«напоминание» and «повтор» are the bot, not Operator.** The Apps Script timer
  writes them at 30 min and 2 h. Counting them as calls would make every
  ignored lead look contacted. `BOT_CALL_EVENTS` in `crm.py` filters them.
  **The timer was switched off 2026-07-27**, so no new ones appear — the filter
  stays for the historical rows and for client sheets, where it's still running.
- **«Звонки» has had two shapes, and `crm.py` reads both.** Until 2026-07-28 it
  was the event log; `calls.py` replaced it with one row per lead. `fold_calls()`
  dispatches on the header, not on a date — «Звонки-архив» and client sheets
  still carry the old shape and must keep parsing.
- **In the old shape the outcome lived in the `итог` event, not `дозвонился`**
  — `дозвонился` only meant the phone was answered. In the new shape `Дозвонился`
  is computed from call duration and `Итог` is the verdict Operator picks by hand.
- **Duplicate phones are real.** People submit twice. `is_duplicate_phone`
  flags the later ones; the summary counts unique people.
- **`utm_content` arrives as `{{ad.video}}`** — Meta never substituted the macro,
  so the literal template string is what identifies the creative. `parse_utm`
  extracts `video` / `c.flat` from it.
- **The connection is 2–4 Mb/s VPN.** `fetch()` retries four times with backoff.
  A failure is usually the tunnel, not the code.
- **`crm.py` is read-only by design.** Its scope is `spreadsheets.readonly`;
  it cannot write even if a future edit tries. Keep it that way — the split is
  what makes "the reader can't corrupt truth" a fact rather than a promise.
- **Each writer owns exactly one tab.** The credential is Editor, so the refusal
  lives in code, not in a habit: `guard()` in `profiles.py` writes only
  «Профили», `guard()` in `calls.py` writes only «Звонки»/«Звонки-архив», and
  **nothing writes «Заявки» or «Чат-лог»** — those are the webhook's, and The.
  Don't route a new write through an existing script; give it its own guard.
- **`business_discovery` only sees Business/Creator accounts.** A personal or
  private account returns an error, and that lands in `статус` as
  «не бизнес-аккаунт». That's a fact about the lead, not a bug — and it is
  itself a qualifying signal.
- **Half the chat answers are not handles.** Real values include «нет
  Instagram», an email address, and business names in Turkmen. `norm_handle`
  repairs stray spaces and a trailing `@`, then the regex throws out the rest
  so they never become API calls. As of 2026-07-28: 34 usable, 13 not.

## Truth ordering

The Telegram bot and this sheet are **truth** for заявки. GA4 and Meta are two
independent estimates of the same reality. When the sheet and GA4 disagree on
lead count, the sheet wins and the gap is the finding.
