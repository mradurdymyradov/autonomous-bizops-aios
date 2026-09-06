---
name: state-check
description: Use when Operator asks whether STATE.md is still accurate, says "is STATE stale", "check STATE", "what's STATE lying about", "обнови STATE", or when a session starts after a gap and STATE.md's numbers need trusting before anything is built on them. Also runs weekly as a freshness cron. Reports what STATE.md claims that reality no longer supports. Read-only — never rewrites STATE.md.
---

# State check — what is STATE.md lying about?

`STATE.md` is the only file in this repo carrying current state, which makes it the only file that
can go silently wrong. Everything else is law or reference — wrong law is loud, wrong state is quiet.
A stale STATE doesn't error; it confidently answers a question with last week's reality.

**Read-only. Never rewrite `STATE.md`.** Report the drift and let Operator decide. He owns this file —
an agent quietly editing the one source of truth is how the source of truth stops being trusted.

## What this is not

Not `/os-audit`. That one checks whether the *structure* is true — routing, indexes, duplication,
where context sits. This one checks whether the *claims* are true. Run both; they catch different
failures. If `/os-audit` also ran today, don't re-do its structural checks — read its report from
`audits/` and focus here on facts and numbers.

## Step 0 — what does STATE claim, and as of when

Read `STATE.md`. Note its `Last updated` date — call it **D**. Every check below asks: *has reality
moved since D, and does STATE know?*

## The checks

Work through all five. For each, state the claim, the evidence, and a verdict:
**GREEN** (still true) · **YELLOW** (drifting, worth a line) · **RED** (actively wrong, would
mislead today).

### 1. Has work happened that STATE doesn't mention?

```bash
git log --oneline --since="<D>" --stat | head -60
git status --short
```

Uncommitted work counts as work. Three files changed in a client folder since D, with no
corresponding line in STATE's board, is a RED — the board is the thing people read.

Also check folder mtimes for anything git can't see:

```bash
ls -lt "clients projects"/*/ brain/ automations/ | head -30
```

### 2. Do the lead and revenue numbers still hold?

Run `/check-crm`. Compare against every count STATE asserts — leads, calls, answered, who's
uncalled. **The Sheet is truth; STATE is a snapshot of it.**

Note carefully: STATE is *allowed* to quote a historical figure (test-01's 39 leads is a
permanent fact about a finished campaign). It is not allowed to quote a *live* figure as if
current. Distinguish "39 leads came from test-01" (fine, forever) from "7 leads said yes"
(a live pipeline count that moves).

If a campaign is live, run `/check-ads` too and reconcile.

### 3. Is the client board accurate?

For each row in STATE's client table: does the stage match what's on disk? A client listed as
`spec` with a built `site/` in their build repo is RED. A client listed as blocked whose blocker
was resolved in `decisions/log.md` is RED.

Check each build repo named in `clients projects/<slug>/engagement.md`, and run its weight gate
if it has one:

```bash
node tools/budget.mjs   # from the build repo
```

A failing gate that STATE doesn't mention is a RED — it blocks a deploy and nobody knows.

### 4. Are the open loops still open?

Read each numbered loop. For each, find the evidence that would close it. A loop that was
quietly finished is worse than a loop that's still open: it costs attention every time the file
is read, and it makes the rest of the list less believable.

Cross-check against `decisions/log.md` since D — a decision often closes a loop without anyone
striking it out.

### 5. Does STATE contradict the brain, the funnel, or itself?

- Numbers that appear in both `STATE.md` and [brain/](../../../brain/index.md): the brain cites
  `notes.py` and is reproducible; STATE is hand-written. **On a conflict the reproducible source
  wins**, and STATE is the one to fix.
- Terms, price, or offer quoted in STATE must match `funnel/00-core.md`, which is law.
- STATE against itself: a figure in §Ads that a later section restates differently.

## The report

Print it. Do not write a file — `audits/` belongs to `/os-audit`, and a second report format there
is exactly the duplication that skill flags.

```
STATE.md freshness — <today>, last updated <D>, <N> days

  work not in STATE      RED/YELLOW/GREEN — one line
  numbers                RED/YELLOW/GREEN
  client board           RED/YELLOW/GREEN
  open loops             RED/YELLOW/GREEN
  contradictions         RED/YELLOW/GREEN

WHAT WOULD WRONG-ANSWER YOU TODAY
  - <the specific question, and the wrong answer STATE would give>

SUGGESTED EDITS — awaiting approval
  1. <section> — <exact change>
```

Lead with **"what would wrong-answer you today."** A list of drifted facts is a chore; a list of
questions the system would answer wrongly is a decision. If nothing would wrong-answer him, say
that in one line and stop — a clean check should be cheap to read.

## Rules

- **Never edit `STATE.md`.** Suggest; he approves.
- **Never quote a live number from a file.** If you're checking whether STATE's lead count is
  right, the comparison comes from `/check-crm`, not from another markdown file.
- **Distinguish stale from wrong.** A three-day-old figure that hasn't moved is GREEN, not YELLOW.
  Age alone is not drift.
- **Say when you couldn't check.** VPN down, API unreachable, no live campaign — an unchecked
  check reported as GREEN is the poisoning failure mode, in the tool built to prevent it.
