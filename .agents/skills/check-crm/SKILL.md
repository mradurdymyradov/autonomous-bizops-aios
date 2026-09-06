---
name: check-crm
description: Use when Operator asks about leads, заявки, or the CRM — "how many leads", "who came in", "any new leads", "did anyone submit", "who haven't I called", "what businesses are these", "сколько заявок", "кто оставил номер", "новые заявки", "кому не позвонил" — or when a funnel or ads decision needs the real lead count. This sheet is TRUTH for заявки; GA4 and Meta are only estimates. Read-only.
---

## What this does

Reads the Google Sheet CRM behind voronkatm.com and folds its append-only event
log into one record per lead — phone, ad creative, the three chat answers, call
outcome, speed-to-call. Read-only: the credential holds `spreadsheets.readonly`
and cannot write.

Sheet `voronka` (`19v4oqQ-l2-aibrUCZ_t9960CP6DSPzPUN-X6xvikEIA`), tabs «Заявки»
(the CRM), «Звонки» (one row per lead, rebuilt from The phone call log by
`calls.py`), «Чат-лог» (session telemetry), «Профили» (the lead's Instagram
account — written by `profiles.py`, read here), «Заметки» (what the lead SAID
on the phone — written by `notes.py`, read here), «Звонки-архив» (the retired
button-tap event log, kept, never read).

## Run this

```bash
cd "D:/ai projects/vaios/automations/sheets" && python crm.py --days 7
```

Pick the window from what Operator actually said. Don't default to 7 if he named one.

| he says | you run |
|---|---|
| "last 3 days" | `--days 3` |
| "this week", nothing | `--days 7` |
| "everything", "all of them" | `--all` |
| "since the campaign launched" | `--from 2026-07-23` |
| "who haven't I called" | `--all --leads` and read the `call` column |
| "who's still in play", "кто согласился", "почему отказались" | `--all --notes` |
| "what are people doing on the page" | `--chat` (or use `/check-ga4` instead) |

Other flags: `--leads` (one line per lead) · `--calls` (every real call, talk
time, callbacks) · `--notes` (what they said, grouped by outcome) · `--json`
(compute on it) · `--raw Заявки` (untouched rows) · `--with-tests`.

**Call data is only as fresh as the last phone export.** «Звонки» is rebuilt
from an SMS Backup & Restore XML, not live. If he asks about calls and the
numbers look stale, that's the reason — ask him to export a new one and run:

```bash
cd "D:/ai projects/vaios/automations/sheets" && python calls.py --xml "C:/Users/mrad/Downloads/calls-YYYYMMDDHHMMSS.xml" --all
```

**If it errors on auth or permissions, run `python verify.py`.** It walks the six
setup steps in order and prints the exact fix. Don't debug by hand.

## Read the output in this order

**1. Real leads.** The summary already excludes test/probe rows and counts
duplicate phone submits once. That number is the truth other surfaces get
compared against.

**2. Called, reached, called back.** These now come from the phone's own call
log, so they are facts, not button taps: `reached` is true when a call actually
had duration, `call_stats` carries talk time, callbacks and missed calls from
the lead. `no call on record` means the number appears nowhere in the export —
that one really is uncalled.

The button-tap era is over: taps were the old «Звонки», almost nobody tapped,
and reading it made every lead look ignored. **Never infer "he didn't call"
from a missing outcome** — that was the exact error this replaced.

**3. Outcome.** `Итог` is the verdict Operator picks by hand — Договорились / Отказ /
Перезвонить позже. «Не дозвонился» is pre-filled by `calls.py` where the log
proves no one picked up; everything else being blank means he hasn't judged the
lead yet, not that nothing happened. A blank `Итог` on a lead with 12 minutes of
talk time is the interesting row — surface those.

**4. What they actually said.** «Заметки» is The own post-call log, typed by
hand in `automations/sheets/leads-log.md` and pushed into the sheet by `notes.py`.
It outranks every counter above it: `reached` says a call connected, this says
whether there is a deal in it. Each lead carries `note.category`
(интерес / думает / отложил / перезвонит сам / не поговорили / нет ответа /
не понял / пропал / не ЦА / не заявка), `note.objections`, and his raw text.

- **`интерес` is the callback list.** Say those numbers out loud, every time.
- **`перезвонит сам` + «не перезвонил» in the text is not a warm lead** — it's
  the polite brush-off, and it is the single biggest bucket. Treat it as cold.
- **The objection tally is the funnel note.** `цена` sends you to
  `funnel/00-core.md`; `не понял оффер` and `уже есть решение` send you to
  `funnel/02-meta-ad.md` and `03-landing-page.md` — they mean the ad promised
  something the page didn't land.
- **A blank note means no note was written yet, NOT a dead lead.** The summary
  says how many are missing. If he asks about leads newer than the log, tell
  him to append to the log file and re-run `notes.py` rather than guessing.

Refresh after he adds notes to the log:

```bash
cd "D:/ai projects/vaios/automations/sheets" && python notes.py
```

**5. Creative and business type.** Which ad produced which kind of business is
what feeds the next campaign and `funnel/02-meta-ad.md`.

**6. The Instagram account.** If «Профили» has been filled, each lead carries
`profile.stats` and `profile.recent_posts` — captions included. Read them and
say what they mean, don't recite them:

- **`days_since_last` > 60** → the account is abandoned. That's a different
  pitch: «ведём аккаунт», not «приводим трафик».
- **High followers with `er_pct` under 1** → bought or dead audience. This is
  usually *the* reason they get no заявки, and it's the strongest opening line
  he has.
- **The captions** tell you what they actually sell, whether they post prices,
  whether there's any call to action, and which language they write in. That's
  what prepares him for the call — more than any of the numbers.
- **`permalink`** is permanent. If a question genuinely needs the pixels, fetch
  that one post; don't ask him to look.
- **статус «не бизнес-аккаунт»** means a personal profile. Say it out loud:
  they have no Instagram business setup to plug a funnel into yet.

To fill or refresh it:

```bash
cd "D:/ai projects/vaios/automations/sheets" && python profiles.py --all
```

## Context you need to interpret it

- **This sheet is truth; GA4 and Meta are estimates.** When they disagree with
  the sheet, the sheet wins and the gap is the finding.
- **«Заявки» only goes back to 2026-07-24.** Earlier leads were cleared from
  that tab but their call rows survive in «Звонки-архив», so the two disagree
  about history. Never report the sheet's earliest row as "when leads started".
- **«Звонки» is derived, «Заявки» is captured.** «Звонки» is regenerated whole
  from «Заявки» + a phone export every time `calls.py` runs. `Итог` and
  `Комментарий` are carried across reruns — they're his. **Every other column
  will be overwritten**, so never tell him to hand-fix one; fix the source or
  the script.
- **Duplicate phones are real people submitting twice**, flagged `DUPE` and
  counted once. Don't report raw row counts as lead counts.
- **`utm_content` is the literal `{{ad.video}}` macro** — Meta never substituted
  it. `video` / `c.flat` / `link_in_bio` is how creatives are told apart.
- **A lead can exist with no phone** if the chat fired but the submit didn't
  land. Those are worth flagging as a capture bug, not ignoring. Once Operator
  confirms the real number, it goes in `automations/sheets/phone-overrides.json`
  keyed by Lead ID — never guess one into the sheet.
- **Timestamps are Ashgabat local, `DD.MM.YYYY`** — same timezone as the Meta ad
  account and the GA4 property, so all three line up day-for-day.
- **Connection is 2–4 Mb/s VPN.** `crm.py` retries four times. A failure is
  usually the tunnel; retry before suspecting the code.

Full setup and gotchas: `automations/sheets/README.md`.
Where the data comes from: `funnel/04-lead-capture.md`.

## Never do these

- Never write to «Заявки» or «Чат-лог» — not to "just fix one row". Those are
  the webhook's, and The. The credential became Editor on 2026-07-28; each
  script owns exactly one tab and refuses the rest in code — `profiles.py` →
  «Профили», `calls.py` → «Звонки» / «Звонки-архив», `notes.py` → «Заметки».
  If a task seems to need a write anywhere else, say so and let him do it by
  hand.
- Never edit «Заметки» in the sheet either — `notes.py` rewrites it whole from
  `automations/sheets/leads-log.md` on every run. The log file is the source; fix it
  there and re-run.
- Never edit «Звонки» cell-by-cell either. It's generated: change the input or
  `calls.py` and rerun, so the next rebuild doesn't undo the fix.
- Never quote lead counts from `STATE.md` or any other file — they go stale
  within a day. Run the script.
- Never commit `automations/google-service-account.json` or any `.env`. Both are
  gitignored; keep it that way.

## Report it like this

Lead with the count and whether anything is uncalled. Then the breakdown that
answers what he asked. Then what it means for the funnel.

If he asked about ads or traffic too, run `/check-ads` and `/check-ga4` and
reconcile the three — Meta Lead vs GA4 `generate_lead` vs real rows here —
rather than reporting three separate stories.

If the numbers moved the picture, update `STATE.md` and suggest a
`decisions/log.md` entry.
