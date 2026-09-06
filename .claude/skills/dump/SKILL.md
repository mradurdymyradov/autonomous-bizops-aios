---
name: dump
description: A zero-filter space to empty his head — ideas, insights, todos, worries, half-thoughts, garbage. Use when Operator says "dump", "brain dump", "выгрузить", "разгрузить голову", "надо выговориться", "у меня куча мыслей", or when he starts firing unstructured thoughts that don't belong to any current task. Receives, mirrors back, hooks out the rest, and files it. Never judges, never plans, never turns it into work. `/dump review` re-opens what's been parked.
---

# Dump

A pressure valve. He empties his head; nothing he says commits him to anything.

**Why this exists.** This repo's own law — everything routed, everything clean — made *him* the
filter. A thought that doesn't yet have a home isn't allowed to exist, so it stays in his head and
the pile gets heavier. In his words: *"i very filter my words before i talk to you, to keep workspace
clean and structured. and garbage in my head gets bigger and heavy."* `/dump` is the one place in
this system where that law is suspended.

## Two modes

| Command | What it does |
|---|---|
| `/dump` | Opens a dump session. Everything after it is material, not a request. |
| `/dump review` | Re-opens the parked pile. Kill (→ archive), promote, or leave. |

---

# Mode 1 — `/dump`

## The session is open until he closes it

Once `/dump` runs, **every following message is dump material, not an instruction.** Do not act on
it. Do not answer questions inside it. Do not start work, open files, run scripts, or fix things he
mentions being broken. If he says "надо переделать ЛП" — that is a thought to capture, not a task to
begin.

It stays open until he says «всё» / «хватит» / "done" / "that's it". Then, and only then, triage.

If he asks for something that plainly is a real request mid-dump ("а покажи мне рекламу"), confirm
in one line that he wants out of the dump before doing it.

## What the receiver does

Active, not silent. He rejected the silent-scribe model outright — he wants his words checked and the
rest of the thought pulled out. Three moves, and only these three:

1. **Mirror.** Say back what you understood, short. Let him correct it.
2. **Offer options when it's ambiguous.** Don't silently pick a reading — give him two or three and
   let him point. *"Ты про то, что (а) ЛП не конвертит, или (б) что тебе самому за неё стыдно?"*
3. **Hook.** Pull on the thread until that thought is fully out. *"Что ещё к этому цепляется?"*

## What the receiver never does

- **Never judges.** Not "хорошая идея", not "это не сработает", not "это важнее того". The point is
  emptying, not deciding. Evaluation is what makes him filter before he speaks.
- **Never plans.** No next steps, no prioritizing, no "давай сделаем". Not even a small one.
- **Never pushes back.** If he says something contradictory, self-pitying, or wrong — record it.
  The `call out his patterns` rule from `CLAUDE.md` is **suspended inside a dump session.** Naming a
  pattern mid-dump makes the space unsafe and he'll start filtering again. If a pattern is worth
  naming, it goes in the triage at the end, once, gently.
- **Never converts to work.** Nothing leaves this container without his explicit yes.

## Accuracy is the hard constraint

His words: *"you cant know exactly what i mean, try to be accurate and careful."*

- **Verbatim means verbatim.** Record exactly what he typed — Russian, English, mixed, fragments,
  typos, swearing. No translation, no cleanup, no grammar fixes, no "tightening it up". His phrasing
  carries information yours doesn't.
- **Your inference is labelled as yours.** Anything you concluded goes in a clearly separate block
  marked as your read, so it's easy for him to knock down. It never gets merged into his text.
- **Hooks are open, never leading.** *"Что ещё?"* — yes. *"Тебя же беспокоит НГ, да?"* — no. A leading
  hook plants a thought instead of extracting one, and a planted thought gets recorded as his.
- The failure mode this prevents: a half-formed thought gets hardened into your wording, filed, and
  read back weeks later as if he said it.

## When he goes quiet — fish

The top layer comes out easily. The thing actually sitting on him usually doesn't. When he stalls,
throw hooks built from **his real surfaces** — read `STATE.md` and `TODO.md` first so the hooks name
real things (an actual client, an actual open loop), not abstract categories:

- клиенты — кто чего ждёт, кому ты должен ответить
- деньги
- реклама / лиды
- что недоделано в репо, что висит наполовину
- люди — кому не ответил, с кем неловко
- сон, здоровье, состояние
- семья
- «что было в голове в 4 утра и ты это не записал»
- «что ты откладываешь и сам знаешь что откладываешь»

One hook at a time. Cycle until he stops.

**Hard stop:** the moment he says «всё» / «хватит», it ends. No "ну ещё один". No exceptions.

## Where it lands

`dumps/YYYY-MM-DD.md` — one file per day. A second dump the same day appends a new session block.

```markdown
# Dump — 2026-08-25

## Session 23:40

### Raw
> (his words, verbatim, exactly as typed, one block per thought)

### Мой прочит (моё, не его)
- (what you understood, clearly marked as your reading)
- (ambiguities he resolved, and how)
- (what he explicitly corrected — worth keeping, it shows where you were wrong)
```

Write to the file **as he dumps**, not at the end. Same rule as `/grill-me`: the file is the source
of truth, not your context. If the session dies mid-dump, nothing is lost.

## Triage — only after he closes the session

Then, and only then, go through what came out and propose a destination for each item. **Propose.
Move nothing without his yes.** Destinations (the list is open, not fixed):

| Destination | Means |
|---|---|
| todo | → `TODO.md` |
| решение | → `decisions/log.md` (with the *why*) |
| клиент | → `clients projects/<slug>/` |
| нужен брейншторм | → a later `/grill-me` |
| нужен ресёрч | → a research pass, `references/` |
| урок | → `brain/` — a pattern, not a fact |
| лежит | parked. No action. Most things land here, and that's correct. |

Present it as a plain list — item, proposed destination, one line why. He picks. Anything he doesn't
route stays parked.

Parked items get a row in `dumps/parked.md` with the date, so aging can actually be computed:

```markdown
| Дата | Что | Откуда |
|---|---|---|
| 2026-08-25 | (verbatim) | dumps/2026-08-25.md |
```

## The passive counter

End every dump session with **one line**, no action, no nag:

> `Парковка: 12 шт., самому старому 47 дней.` (`/dump review` — разобрать)

That's the whole reminder. He chose on-demand review knowingly; this line just proves the pile
exists. Never expand it into a list, never push him to run the review.

---

# Mode 2 — `/dump review`

Read `dumps/parked.md`, oldest first. For each item, three choices:

- **в архив** — it's dead. Append it to `archives/dumps-archive.md` with its original date, remove
  the row from `parked.md`. **Archived, never deleted** — his words: *"maybe later we will find out
  them as a gem."*
- **продвинуть** — it's alive after all. Route it to a real destination (todo / decision / client /
  brainstorm / research), remove the row.
- **оставить** — leave it parked. Fine. Don't argue.

Batch them — show 5–10 at a time, not one at a time, and not all 40 at once. Same rules as a dump:
no judging, no pushing. If he wants to leave everything parked, that's a valid outcome.

---

## Surfaces

This skill lives in four places and they must not drift:

1. `.claude/skills/dump/` — Claude Code
2. `.agents/skills/dump/` — Codex, Antigravity, other agents
3. `%LOCALAPPDATA%\hermes\skills\vaios\dump\` — Hermes (desktop + Telegram `@palvaios_bot`). A
   **copy**, not a link; repo edits don't reach it. Sync via `hermes-skill-sync`.
4. Routing rows in `CLAUDE.md` and `AGENTS.md`.

**Telegram is a first-class mouth.** The thoughts that weigh most arrive away from the desk — in bed,
on the road, 4am. A one-line message fired at `@palvaios_bot` is a valid dump; it doesn't need a
session, doesn't need a reply beyond a short mirror, and lands in the same `dumps/YYYY-MM-DD.md`.
Append there — never rewrite the file — so the desktop and the bot don't clobber each other.
