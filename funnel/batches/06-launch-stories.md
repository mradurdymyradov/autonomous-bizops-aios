# IG Content Batch 06 — Launch-day stories (5 stories, agent-executed)

**For Antigravity (executor).** This file IS the implementation plan — **do not write your own implementation_plan.md. Execute this file directly, top to bottom.** Workflow: read this file + `brand/content-rules.md` + `brand/character.md` → generate every story 1:1 with your **built-in image tool (Nano Banana 2)** → **fit to 9:16 with `automations/ig-poster/crop916.py`** → QC → **show Operator and WAIT for approval**. Then **Operator posts these stories HIMSELF from his phone** (so he can drop a real link sticker on the CTA frame — the API can't do stickers). Do NOT post via post.py. Russian copy is final — never rewrite it.

**Why this exists:** the $25 Ahal ad is going live. Cold visitors who land on the profile from it should see an account that is *alive right now*. This is an ephemeral 5-story set (24h) that adds a launch-moment pulse and one clean push to the free audit — **not** a highlight, don't assemble it. Every angle here is deliberately NOT already covered by the feed posts (batch-01) or the highlights (batch-02): no 4-step system breakdown, no "клиенты не доходят" pain, no analytics/«без догадок», no FAQ, no niche list. Fresh angles only.

**Status:** generated and compressed 2026-07-24 — 5 files (s1.jpg … s5.jpg) ready in `automations/ig-poster/stories-launch/` for manual posting by Operator.

---

## 0. Hard rules (full law in the two brand files — read §8 composition law)

- **9:16 output.** Generate 1:1 (the tool is locked to it), then `crop916.py --folder stories-launch` **fits** the square into 1080×1920 — nothing is ever cut. Put **`9:16`** in every prompt as the target ratio anyway (§1).
- **All visible text Russian**, exact copy in the table, final. Agency «мы», client «вы». Banned: CAC, лиды, конверсия, ROI, performance, трафик. **Never mention price.** Single CTA = бесплатный аудит.
- **Tokens:** bg `#0A0C0B`, text `#F1F4EC`, muted `#98A29A`, single lime accent `#B4FF3A`. Clean geometric sans-serif. No photos/gradients/watermarks.
- **Wordmark stamp = `@voronka.tm`** (with the @). Hook story (s1) carries it; middle/CTA stories don't (fewer Cyrillic elements = safer).
- **PROMPT DISCIPLINE (the model draws your instructions):** only name text by its exact literal string. Never write "label", "caption", "band", "column", "strip", "panel", "frame", pixel numbers or "safe zone" — they render as gibberish or drawn rectangles. Use the templates below verbatim.
- **COMPOSITION (`brand/content-rules.md` §8):** never name a container — say only *"keep the left and right sides completely empty dark background."* Dictate line breaks (they control wrapping). Props stack **above/below/in-hand, never beside him**. Character centered, facing forward, half-body.
- **NO text-bearing reference images — generate every flat story STANDALONE.** The ONLY refs ever attached are the character sheets on s1 (T1), and its prompt forbids copying text from them.

## 1. Pipeline (don't fight it)

1. Generate each story **1:1** with the built-in tool. Save PNGs to `automations/ig-poster/stories-launch/` with the exact filenames `s1.png` … `s5.png`.
2. Fit to 9:16 (scales to 1080×1920, extends top/bottom edges to brand black, writes `<name>.jpg`; sources untouched):
   ```
   cd "D:\ai projects\vaios\automations\ig-poster"
   python crop916.py --folder stories-launch
   ```
3. The `.jpg` files are the deliverables Operator posts from his phone (§4).

## 2. QC gate (one fail = regenerate)

**On the square PNG, before fitting:**
- [ ] **No vertical seams** (no drawn container). View at 100%, scan for full-height tone shifts.
- [ ] Lines broken exactly as the table's `_LINES` specify — no hyphenated Cyrillic, no orphan word.
- [ ] Character (s1 only) large enough to read as the hero, not shrunk by anything off to his side.

**On the fitted .jpg:**
- [ ] Every Russian word matches this file exactly — zoom in, letter by letter. No duplicated/ghost text, no invented text/numbers/doodles.
- [ ] s1 character: full `brand/character.md` §6 checklist (face vs ref-02, flag patch, no foreign logos/«TRADING», no blue).
- [ ] The join between square and extended bands is invisible; lime the only accent; body noticeably smaller than the headline; 1080×1920.
- [ ] One wrong letter → regenerate, or edit: `Fix the text to say "..." exactly, change nothing else.`

## 3. Approval flow (mandatory)

Generate all 5 → fit → QC → show Operator the set. WAIT. "Approve" → hand files to phone (§4). "Fix X" → fix, re-show. No answer = no delivery.

---

## Story prompt templates

**T1 — character hook story** (s1 only — Style A). **Attach `brand/character-refs/ref-02-hero-closeup-flag-jacket.png` + `ref-03-full-sheet-poses-expressions.png` as reference images.** QC against `brand/character.md` §6.

```
A vertical 9:16 cinematic image. Everything sits close to the middle of the image, stacked from top to bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. In the upper half, over clean dark background, only this text:
- Small muted-gray text: @voronka.tm
- An off-white headline, each line short and centered, broken exactly like this: {HOOK_LINES}
- Smaller muted-gray text below it, on {SUB_LINES}: "{SUB}"
In the lower half, centered: {SCENE}

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere. No other logos, no watermarks, no English text.

Render each text exactly as written, once — no repeated or extra words, no other text or symbols, and do not copy any text, labels or logos from the reference images. The background is one single continuous flat dark surface, even and unbroken from edge to edge.
```

`{HOOK_LINES}` = one quoted fragment per line. `{SUB_LINES}` = `one line` or `two lines`. Character centered, facing forward; every prop above/below/in-hand, never off to one side.

**T2 — content story** (s2–s4 — flat, standalone, NO reference images):

```
A minimal vertical 9:16 graphic. Everything sits close to the middle of the image, stacked from top to bottom, with empty dark space at the very top and the very bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. Centered, top to bottom, only these things:
- {TITLE_SIZE} off-white headline, each line short and centered, broken exactly like this: {TITLE_LINES}
- Smaller muted-gray text below it, on {DESC_LINES}, each line short: "{DESC}"
- Below that, one lime line-art icon with a soft dim lime glow around it in the dark background: {ICON}
Render each text exactly as written, once — no repeated or extra words, and no other text, numbers, labels or symbols besides the icon. The background is one single continuous flat dark surface, even and unbroken from edge to edge.
{STYLE}
```

`{STYLE}` (append verbatim to every T2/T3 prompt):

> Style: minimal flat vector design, clean and uncluttered. Solid near-black #0A0C0B background with lots of empty dark space and a very subtle deep-green tint in the corners. Off-white #F1F4EC headline text, muted gray #98A29A secondary text, a single electric-lime #B4FF3A accent. Clean geometric sans-serif at standard mobile app text sizes — the headline at the size stated above, the secondary text noticeably smaller, never giant poster type. Do not add any text, letters, numbers, labels, captions, frames, brackets, symbols or decorative doodles other than the exact elements listed above. No photos, no people, no watermarks.

- `{TITLE_SIZE}` = `A large` normally; `A medium` if any word is longer than ~12 characters. Never hyphenate a Russian word across lines.
- `{TITLE_LINES}` / `{DESC_LINES}` = one quoted fragment per line / `two lines`, `three lines`.

**T3 — CTA story** (s5 — flat, standalone, NO reference images). Operator places a **real link sticker** in the empty area — the image must leave it completely blank:

```
A minimal vertical 9:16 graphic. Everything sits close to the middle of the image, stacked from top to bottom, with empty dark space at the very top and the very bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. Centered, top to bottom, only these things:
- {CTA_SIZE} off-white headline, each line short and centered, broken exactly like this: {CTA_HEAD_LINES}
- Smaller muted-gray text below it, on {CTA_SUB_LINES}, each line short: "{CTA_SUB}"
- Below that, a lime arrow pointing straight down at a large empty dark area lit by a soft dim lime glow from below — leave that whole area completely empty, do not draw anything or write any words in it
- Near the bottom, small muted-gray text: "или напишите «аудит» в Direct"
Render each text exactly as written, once — no repeated or extra words, no other text or symbols. The background is one single continuous flat dark surface, even and unbroken from edge to edge.
{STYLE}
```

`{CTA_HEAD_LINES}` = one quoted fragment per line; `{CTA_SIZE}` drops to `A medium` if any word exceeds ~12 characters; `{CTA_SUB_LINES}` = `two lines` / `three lines`.

---

## The 5 stories

Files `s1.png` … `s5.png` (→ `.jpg` after fit). Post in order s1 → s5.

| # | File | Template | Text / variables |
|---|------|----------|------------------|
| 1 | s1 | T1 | HOOK_LINES: `"Хватит ждать," / "что клиенты" / "придут сами"` · SUB_LINES: `two lines` · SUB: `Пора идти за ними — с системой` · SCENE: the character half-body, centered, facing forward, confident closed-mouth smirk, arms crossed, a soft lime rim light on his shoulders |
| 2 | s2 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Постов много —" / "клиентов нет"` · DESC_LINES: `three lines` · DESC: `Лента сама не приводит покупателей. Это делает реклама, настроенная в систему.` · ICON: a megaphone with a few small signal lines coming out of it |
| 3 | s3 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Мы —" / "местные"` · DESC_LINES: `three lines` · DESC: `Понимаем рынок Туркменистана и ваших клиентов. Говорим с ними на одном языке.` · ICON: a simple map pin with a small dot in the center |
| 4 | s4 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Кто первый —" / "тот и собирает" / "заявки"` · DESC_LINES: `three lines` · DESC: `Пока другие просто ведут ленту, вы уже забираете клиентов из рекламы.` · ICON: a small flag planted on top of a rising line |
| 5 | s5 | T3 | CTA_SIZE: `A large` · CTA_HEAD_LINES: `"Начнём с" / "бесплатного" / "аудита"` · CTA_SUB_LINES: `two lines` · CTA_SUB: `10 минут по телефону. Покажем, где вы теряете клиентов.` |

**Angle check (why none of these repeat):** s1 = a fresh "stop waiting, go get them" hook (not the "система vs красивый профиль" or "клиенты не доходят" angles). s2 = the *posting-more-won't-help* myth, never stated on its own before. s3 = the *local / same-language* trust angle — brand pillar, unused anywhere. s4 = a *first-mover / launch-moment* nudge that fits the ad going live. s5 = the standard audit CTA, worded fresh.

---

## 4. Posting — MANUAL, by Operator (agent only delivers files)

After approval, the agent's last step: get the 5 cropped `.jpg`s onto The phone (easiest: drag them into Telegram Saved Messages; remind Operator and list the filenames).

**Operator, in the IG app, same session:**
1. Post s1 → s5 **in order** to your story (from gallery).
2. On the **CTA story (s5): add the link sticker** in the big empty area under the arrow → URL `https://voronkatm.com` → edit sticker text to «Бесплатный аудит».
3. That's it — this set is ephemeral (dies in 24h). Do **not** save it as a highlight.

**Timing:** publish these when the ad goes live (or the same evening, 19:00–21:00 Ashgabat), VPN ON — so the first cold visitors from the ad see an active profile.

## 5. After the batch

- Update the Status line here (post date, whether all 5 shipped).
- No `funnel/01-instagram.md` change needed (ephemeral, not profile furniture).
- Log in `decisions/log.md`: launch-day story set shipped alongside the $25 Ahal ad (5 fresh angles, audit-only CTA, ephemeral).
