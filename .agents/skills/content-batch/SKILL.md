---
name: content-batch
description: >
  Write a content batch file for @voronka.tm — IG feed posts, stories, highlights,
  or ad creatives. Use whenever Operator asks for new content, new post prompts, a new
  highlight, an ad creative, or says "write a batch", "make me some posts",
  "нужен контент". Carries the image-generation rules that cost two scrapped runs
  to learn. Read this before writing any image prompt.
---

# Writing a content batch

A batch file is a **self-contained work order**: Claude writes it, a generator agent (Antigravity,
using its built-in image tool) executes it into images with no other context. The executor reads
**only** the batch file plus `brand/character.md` and `brand/content-rules.md`.

**Read first, every time:**

1. `brand/character.md` — the character bible. §4 is the verbatim prompt block, §5 the scene
   vocabulary, §6 the QC checklist. Reference images live in `brand/character-refs/`.
2. `brand/content-rules.md` — design tokens (§2), the two styles (§3), pillars (§4), prompt recipe
   (§5), copy rules (§6), **the batch file contract (§7)**, composition law (§8), QC gate (§9).
3. `funnel/00-core.md` — voice law. Russian, agency «мы», banned jargon (CAC / лиды / конверсия /
   ROI / трафик), never show price, single CTA = бесплатный аудит.

Existing batches in `funnel/batches/` are the model — `01-feed-posts.md` and `02-highlights.md` are
the reference implementations. New batches go there as `NN-<topic>.md`.

## The seven rules (learned the hard way — do not relearn them)

**1. The model draws your instructions.** No meta-words anywhere in a prompt — "safe zone", "label",
"marker", pixel numbers, aspect ratios. They get printed into the image as gibberish or doodles. Use
only exact literal quoted strings, a short closed list of elements, and end with a ban on everything
else.

**2. Never attach a text-bearing image as a reference.** The reference's text bleeds into the new
image as duplicated, corrupted ghost lines — this scrapped an entire run. Flat images generate
**standalone**; consistency comes from identical templates and tokens, not from references. The only
sanctioned references are the character sheets `ref-02-hero-closeup-flag-jacket.png` and
`ref-03-full-sheet-poses-expressions.png`, always accompanied by *"do not copy any text, labels or
logos from the reference images."*

**3. The wordmark is `@voronka.tm`, with the @.** It's the Instagram handle, not a domain. Skip the
corner stamp entirely on character scenes whose background neon sign already reads `voronka.tm` —
one less text element is one less chance of corrupted Cyrillic. Never a bare `voronka.tm` stamp.

**4. Text sizes are mobile-app sizes.** Headline like a phone's large title, body smaller. Never
giant poster type.

**5. 1:1 → 9:16 is a FIT, not a crop.** `automations/ig-poster/crop916.py --folder X` scales the
square to 1080 wide and extends its top/bottom edge rows to fill 1920. Nothing is ever cut, so no
image can fail on composition. Settled 2026-07-21 after two runs proved the model will not draw text
narrow enough to survive a center-crop — told to break a headline into more lines, it obeys the
breaks and draws each line bigger, filling the same width. `--crop --check` is legacy.

**6. Never name a container.** «column», «band», «strip», «panel», «frame» get *drawn* as a visible
rectangle whose hard edges survive into the final story. Say instead: *"keep the left and right sides
completely empty dark background."* Give the middle no noun. Removing the word fixed it outright —
the v4 run came back with zero seams. Related: dictate line breaks explicitly (the `_LINES` values in
the batch tables) — they control wrapping, not width. Props stack **above, below, or in his hands**,
never "beside him"; v4's funnel-above-the-palm is the reference composition.

**7. Fix one wrong word, regenerate anything worse.** A single misspelling → edit endpoint:
`Fix the text to say "..." exactly, change nothing else.` A ghost line or a second wrong letter →
regenerate from scratch.

## Batch file header

Every batch opens with: purpose, status line, pointers to the two brand files and the required ref
images, then the hard-rules recap. Include this line verbatim — the executor writes its own
`implementation_plan.md` unless told not to:

> **This file IS the plan. Execute it directly. Do not write an implementation plan.**

## After the batch runs

- Feed posts publish via the `ig-post` skill. **Stories Operator posts himself from his phone** — the link
  sticker (`https://voronkatm.com`, text «Бесплатный аудит») goes in the deliberately empty area of
  CTA frames, and highlights get assembled in-app the same day because stories die in 24h. The
  agent's job ends at approved files.
- Update `STATE.md` (batch status + open loops) and log media IDs in `decisions/log.md`.
- **Any new generation failure → write the fix into `brand/content-rules.md` immediately.** That is
  the entire compounding mechanism of this system.
