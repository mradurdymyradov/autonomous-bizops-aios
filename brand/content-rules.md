# voronka.tm content system — visual style & generation rules

**This file + `brand/character.md` = the content law.** Claude writes batch files from these rules; antigravity executes batch files against them. Must never contradict `funnel/00-core.md` (offer, voice, CTA) — if it ever does, core wins and we fix this file.

*Created 2026-07-17. Model: RebelsFunding-style character-first system, adapted: their blue → our lime, their trader kid → our Turkmen guy with the flag patch.*

---

## 1. The system in one paragraph

One recurring 3D character (see `brand/character.md`) on a near-black stage, one accent color (electric lime), one recognizable mark (glowing Turkmenistan flag patch), consistent typography, logo/wordmark in a corner, tiny consistent caption structure. Every post looks like it came from the same factory. Consistency IS the brand — a follower should recognize our post from 2 meters away before reading a word.

## 2. Design tokens (use in every image)

- Background near-black `#0A0C0B`, deep green tint allowed in scenes
- Primary text off-white `#F1F4EC`
- Muted gray `#98A29A`
- **Single accent: electric lime `#B4FF3A`** — highlights the ONE key word in a headline, rim light, glow, UI accents. Never blue (that's the reference brand, not us). The flag patch glow is bright green leaning lime — the only sanctioned second glow.
- Typography on images: modern geometric sans-serif (Manrope-like) headlines; monospace (JetBrains Mono-like) small labels. Headline pattern: off-white sentence with the key word in lime — e.g. «Заявки **каждый день**» (каждый день in lime).
- **Wordmark = the IG handle, written `@voronka.tm`** (WITH the @). Small, muted gray monospace, top-left or bottom. Rationale (decided 2026-07-20): without the @ it reads like a web domain — and voronka.tm is not a live site (yet; we may buy the domain at revenue). The @ makes it unambiguous: this is our Instagram. Rules:
  - Flat images: `@voronka.tm` stamp on hook/cover/CTA frames. On dense middle slides/stories the stamp is optional — fewer text elements = safer Cyrillic.
  - Character scenes that include the background lime neon sign: the neon reads `voronka.tm` (no @ — it's signage) and the corner stamp is SKIPPED, one less text element.
  - Never write bare `voronka.tm` as a corner stamp again.

## 3. Two content styles (and when each is used)

**Style A — Character posts (default, ~80% of the grid):**
3D cinematic scene with the character. Emotional hook, recognition, brand identity. Educational hooks, announcements, celebrations, memes, story covers. Prompt recipe in §5.

**Style B — Flat infographic (the batch-01 style, ~20%):**
Minimal flat vector, no people — for data-dense slides: carousel inner slides, CRM/dashboard mockups, step diagrams. Full spec lives in `funnel/batches/01-feed-posts.md` §0–1 (shared style block). Same tokens, so A and B sit on one grid seamlessly.

Hybrid is allowed and encouraged: carousel cover = Style A (character), inner slides = Style B (data), closing CTA slide = Style A (character pointing at the CTA button).

## 4. Content pillars (rotate; map to funnel goal)

1. **Система** — how the machine works (таргет → сайт → бот → CRM). Character demonstrates a part.
2. **Разбор / education** — why ads eat budget, why Direct loses clients. Character in thinking pose. Positions competence.
3. **Proof / результат** — заявки arriving on the phone screen, CRM filling up. Understated wording per core: «пара долларов за клиента», never "$2 CAC". Never invent client results that don't exist.
4. **Brand / lifestyle** — character with tea, Novruz, city at night, "we're local" energy. Builds the persona. No offer, no CTA pressure.

Every post except pillar 4 ends with the single CTA: **бесплатный аудит → ссылка в шапке профиля.** Never price, never «$500» — price lives only in the audit call (core law).

## 5. Prompt recipe for character posts (Claude: build prompts exactly like this)

Order matters for Nano Banana 2 (front-loaded weight):

1. **Format:** `Instagram post, 4:5 vertical` (or `9:16` for stories), 2K, thinking mode ON
2. **Scene:** one sentence — where he is, what he's doing, what he's holding (pick from character.md §5 scene vocabulary)
3. **Text elements:** each in "double quotes" with position + style; max 3–6, Russian spelled EXACTLY (Cyrillic corrupts easily); headline key word specified as lime
4. **Character prompt block:** paste verbatim from `brand/character.md` §4
5. **Reference images:** attach `brand/character-refs/ref-02-hero-closeup-flag-jacket.png` + `ref-03-full-sheet-poses-expressions.png` — mandatory, every time

Nano Banana 2 ground rules (researched 2026-07, updated 2026-07-20): natural-language sentences not keyword lists; generate at target ratio when the tool allows (1:1-locked tools → compose per §8, then `crop916.py`); misspelled word → edit endpoint `Fix the text to say "..." exactly, change nothing else.`

**REFERENCE-IMAGE LAW (learned from a scrapped run):** never attach an image that contains text as a reference — the model bleeds the reference's text into the new image as duplicated/corrupted ghost lines. Flat slides/stories are generated STANDALONE; consistency comes from identical templates + tokens. The only sanctioned references are the character sheets (ref-02/ref-03) for character images, always with "do not copy any text, labels or logos from the reference images."

## 6. Copy rules for images + captions (from core — summary, core wins)

- All visible text Russian; Latin only for brand names (Instagram, Telegram, CRM, voronka.tm)
- Agency «мы», client «вы»
- Banned: CAC, лиды, конверсия, ROI, performance, трафик. Allowed: таргет/таргетированная реклама, Telegram-бот, CRM-таблица, аналитика, заявки, клиенты, продажи
- Caption structure: hook line → 2–4 short lines of value → CTA (бесплатный аудит, ссылка в шапке профиля) → hashtags
- Hashtag base set (rotate 4–6): `#туркменистан #ашхабад #бизнес #реклама #маркетинг #продажи #предприниматель`
- Captions are final when written in a batch file — antigravity posts them verbatim, no rewriting

## 7. Batch file contract (how Claude ↔ antigravity hand off)

Every content batch is one self-contained file: `funnel/batches/NN-<topic>.md`. Antigravity reads ONLY that file plus the two brand files. Claude writes them via the `content-batch` skill. Required sections (`01-feed-posts.md` / `02-highlights.md` are the model):

1. Header: purpose, status line, pointer to `brand/character.md` + `brand/content-rules.md` + ref images
2. Hard rules recap (QC, Russian-exact, ratio, file naming `automations/ig-poster/pNsN.png`)
3. Per post: format/ratio/filename → full prompt (with character block pasted, refs listed) → caption verbatim → post command for `automations/ig-poster/post.py`
4. Posting order & schedule (default: 1/day, 19:00–21:00 Ashgabat, VPN ON on The machine)
5. "After the batch" — what to update (`funnel/01-instagram.md` status, log media IDs)

## 8. Composition law for 1:1 → 9:16 stories

*Learned over two failed h1 runs, 2026-07-20 and 07-21. Both had perfect spelling and died on layout.*

**The headline finding: you cannot make this model draw narrow text.** Told to break a headline into more lines, it obeys the line breaks and then simply draws each line bigger, filling the same width. Measured across both runs, as % of image width: v3 was 76/67/39/54, v4 (with explicit per-line breaks and a "medium" size instruction) came back 59/67/50 — against a 56% crop window. The instruction was followed; the width didn't move. Don't spend more runs fighting this.

**So: stories are FITTED, not cropped.** `crop916.py` defaults to `--fit` — the whole square scales to 1080 wide and its top/bottom edge rows extend to fill 1920. Nothing is ever cut, no image can fail on composition, and because the bands are the same near-black as the design the join is invisible. Bonus: content lands exactly in Instagram's story safe zone, which IG covers with its own UI anyway. `--crop` is kept as legacy for images deliberately composed narrow; run `--check` first if you use it.

Still binding regardless of mode:

1. **Never name a container.** «column», «band», «strip», «panel», «frame» get **drawn** as a visible rectangle with hard edges (measured: seams at x≈300/725 and x≈339/681 on a 1024 square). This ruins a fitted story just as badly as a cropped one. Say instead: *"Keep the left and right sides of the image completely empty dark background — nothing there at all."* Give the middle no noun. Removing the word fixed it — v4 came back with zero seams.
2. **Dictate line breaks anyway.** They don't control width, but they do control where the text wraps, which is the difference between a clean three-line headline and an ugly orphan. One quoted fragment per line.
3. **Never hyphenate Cyrillic across lines** — it corrupts.
4. **Stack vertically, never side by side.** «beside him», «next to», «to his left» spread the composition horizontally and shrink the character. Props go **above, below, or in his hands** — v4's funnel-above-the-palm is the reference. Character centered, facing forward, half-body.

## 9. QC gate (antigravity: run before every publish)

- [ ] Character checklist from `brand/character.md` §6 passed
- [ ] Every Russian word spelled exactly as in the batch file (zoom in)
- [ ] Lime is the only accent; tokens match §2
- [ ] Wordmark present; ratio correct; no watermarks
- [ ] Caption matches batch file verbatim; CTA is бесплатный аудит; no price anywhere
- [ ] `--dry-run` first if anything about the pipeline changed since last batch
