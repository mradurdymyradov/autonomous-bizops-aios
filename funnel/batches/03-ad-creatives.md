# Content Batch 03 — Meta ad creatives (3 statics for the first $23 test)

**For Antigravity (executor).** This file IS the implementation plan — do not write your own planning doc. Execute top to bottom. Workflow: read this file + `brand/content-rules.md` + `brand/character.md` → generate 3 images 1:1 with your built-in image generation tool → QC → **show Operator and WAIT for approval**. That's where your job ends: **these are NOT Instagram posts — do not post anything, do not run post.py.** Operator uploads the approved files by hand in Meta Ads Manager. Russian copy is final — never rewrite it.

**Why this exists:** first paid traffic test. $23 total (~$6/day), IG only, traffic objective optimized for landing page views, destination voronkatm.com. Goal: book one free audit call. Decision logged 2026-07-23: static images, not video — 3 variants, Meta picks the winner. All three share one hook angle (the LP hero pain: «Инстаграм есть, а клиентов нет?») with different visuals, so click→page feels continuous.

**Status:** created 2026-07-23. Not generated, not run.

---

## 0. Hard rules

- **All visible text Russian**, exact strings below, final. Agency «мы». Banned: CAC, лиды, конверсия, ROI, performance, трафик. **Never any price.**
- **Tokens:** bg `#0A0C0B`, text `#F1F4EC`, muted `#98A29A`, single lime accent `#B4FF3A`. No blue, ever.
- **Ratio: 1:1 square, 2K.** No cropping/fitting step — square runs as-is in IG feed placements. Do not run crop916.py.
- **Keep text on the image minimal** — ads with heavy text get suppressed by Meta. Each creative lists its exact text elements; add NOTHING else.
- **PROMPT DISCIPLINE:** only name text by its exact literal string. Never write "label", "caption", "frame", "brackets" — they render as gibberish or doodles. No pixel numbers or ratios in prompts. Use the prompts below verbatim.
- **COMPOSITION (`brand/content-rules.md` §8):** never name a container («column», «band», «strip», «panel») — it gets drawn as a visible rectangle. Dictate headline line breaks exactly. Props stack above/below/in-hand, never beside the character. Never hyphenate Cyrillic across lines.
- **Character images (ad-a, ad-b):** attach `brand/character-refs/ref-02-hero-closeup-flag-jacket.png` + `ref-03-full-sheet-poses-expressions.png` as reference images, every time, with the do-not-redesign instruction. Do not copy any text, labels or logos from the reference images. **ad-c is flat Style B — generate STANDALONE, no reference images.**
- **Wordmark law:** scene with background lime neon `voronka.tm` → no corner stamp. Otherwise small muted-gray `@voronka.tm` stamp.

## 1. Files

Save to `automations/meta-ads/creatives/`:

| File | Concept | Style |
|---|---|---|
| `ad-a-pain.png` | Pain hook — character thinking | A (character) |
| `ad-b-proof.png` | Result — заявка arriving on phone | A (character) |
| `ad-c-flat.png` | Bold text only | B (flat) |

## 2. QC gate (one fail = regenerate)

- [ ] Every Russian word matches this file exactly — zoom in, letter by letter. No ghost/duplicated text, no invented words, numbers or doodles.
- [ ] ad-a, ad-b: full `brand/character.md` §6 checklist — face vs ref-02, glowing flag patch (crescent + 5 stars + red ornament stripe), no TRADING/Nike/Atlético/Plus500, no blue accent.
- [ ] No vertical seams (drawn containers) — scan at 100%.
- [ ] Lime `#B4FF3A` is the only accent; headline key word in lime as specified.
- [ ] 1:1, no watermarks.
- [ ] One wrong letter → regenerate or edit: `Fix the text to say "..." exactly, change nothing else.`

## 3. The 3 creatives

### ad-a-pain.png — the pain hook

Text elements (exactly these, nothing else):
- Headline, off-white, centered, broken exactly on two lines: line 1 `"Инстаграм есть,"` line 2 `"а клиентов нет?"` — the word `"клиентов"` in electric lime
- Background neon signage: `"voronka.tm"` in lime (so: NO corner stamp)

Prompt (verbatim):

```
A square cinematic image. Everything sits close to the middle, stacked from top to bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. In the upper half, over clean dark background, only this text: an off-white headline, each line short and centered, broken exactly like this: "Инстаграм есть," on the first line, "а клиентов нет?" on the second line, with the single word "клиентов" colored electric lime #B4FF3A. In the lower half, centered: the character in a thinking pose, chin resting on his hand, looking up at the headline with a knowing smirk, half-body, facing forward. Behind him, small and soft in the dark background, a lime neon sign reads "voronka.tm". Do not add any other text, letters, numbers, symbols or decorations besides the exact elements listed above.

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Do not copy any text, labels or logos from the reference images. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere.
```

References: attach `ref-02` + `ref-03`.

### ad-b-proof.png — заявки arriving

Text elements (exactly these, nothing else):
- Headline, off-white, centered, broken exactly on two lines: line 1 `"Заявки"` line 2 `"каждый день"` — `"каждый день"` in electric lime
- On the phone screen: one short line `"Новая заявка"`
- Small muted-gray stamp: `"@voronka.tm"` (no neon in this scene)

Prompt (verbatim):

```
A square cinematic image. Everything sits close to the middle, stacked from top to bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. At the top, small muted-gray text: "@voronka.tm". Below it an off-white headline, each line short and centered, broken exactly like this: "Заявки" on the first line, "каждый день" on the second line, with the words "каждый день" colored electric lime #B4FF3A. In the lower half, centered: the character smiling wide, holding a phone up in both hands in front of his chest, the screen glowing green and showing a single clean notification that reads "Новая заявка". The green glow from the screen lights his face. Half-body, facing forward. Do not add any other text, letters, numbers, symbols or decorations besides the exact elements listed above.

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Do not copy any text, labels or logos from the reference images. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere.
```

References: attach `ref-02` + `ref-03`.

### ad-c-flat.png — bold text, Style B (STANDALONE, no references)

Text elements (exactly these, nothing else):
- Headline, off-white, large, centered, broken exactly on two lines: line 1 `"Инстаграм есть,"` line 2 `"а клиентов нет?"` — `"клиентов"` in electric lime
- Below, noticeably smaller, muted gray, one line: `"Бесплатный аудит вашей рекламы"`
- Small muted-gray stamp at the bottom: `"@voronka.tm"`

Prompt (verbatim):

```
A square minimal design. Everything sits close to the middle, stacked from top to bottom, centered. Keep the left side and the right side of the image completely empty dark background — nothing there at all. Only this text: an off-white headline in clean geometric sans-serif, each line short and centered, broken exactly like this: "Инстаграм есть," on the first line, "а клиентов нет?" on the second line, with the single word "клиентов" colored electric lime #B4FF3A. Below the headline, noticeably smaller, muted gray #98A29A, one line: "Бесплатный аудит вашей рекламы". At the bottom, small muted-gray text: "@voronka.tm". Style: minimal flat design, clean and uncluttered. Solid near-black #0A0C0B background with lots of empty dark space and a very subtle deep-green tint in the corners. Do not add any other text, letters, numbers, labels, symbols, frames or decorative elements besides the exact elements listed above. No photos, no people, no watermarks.
```

## 4. Approval flow (mandatory)

1. Generate all 3, run QC, fix fails.
2. Show Operator all 3 side by side. WAIT.
3. Approve → done, hand back to Operator. "Fix X" → fix, re-show. No answer = nothing happens.

## 5. Ads Manager copy (for Operator, campaign setup — NOT for image generation)

Antigravity: skip this section. Operator: copy-paste when building the campaign by hand.

- **Campaign:** Traffic → optimize for landing page views. Budget **$6/day**, run ~4 days, cap ≈$23–25.
- **Ad set:** geo Turkmenistan, broad (no interest stacking on this budget), placements: Instagram feed + explore only.
- **Destination:** voronkatm.com
- **Primary text:** «Инстаграм есть, а клиентов нет? Мы настраиваем систему, которая приводит заявки: таргет-реклама → сайт → Telegram-бот → CRM-таблица. Запишитесь на бесплатный аудит — за 10 минут покажем, где ваша реклама теряет клиентов.»
- **Headline:** «Бесплатный аудит вашей рекламы»
- **CTA button:** «Подробнее» (Learn More)
- One ad set, 3 ads (ad-a, ad-b, ad-c). Don't touch it for 3 days — let Meta pick the winner.

## 6. After the batch

- Update `funnel/02-meta-ad.md`: creative status → generated/approved, then → live with launch date.
- After the run: log results (spend, LP views, cost per LP view, заявки) in `funnel/02-meta-ad.md`.
- The winning static becomes the Veo 3.1 image-to-video candidate for round 2 — do NOT spend video credits before there's a winner.
