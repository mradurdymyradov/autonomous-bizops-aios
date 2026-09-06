# IG Content Batch 02 v5 — Profile highlights (5 highlights × 4–6 stories + covers), agent-executed

**For Antigravity (executor).** This file IS the implementation plan — **do not write your own implementation_plan.md or any planning doc. Execute this file directly, top to bottom.** Workflow: read this file + `brand/content-rules.md` + `brand/character.md` → generate every story 1:1 with your **built-in image generation tool** → **crop to 9:16 with `automations/ig-poster/crop916.py`** → QC → **show Operator and WAIT for approval**. That's where your job ends: **Operator posts these stories HIMSELF from his phone** (so he can add a real link sticker on the CTA frames — the API can't do stickers). Do NOT post them via post.py. Russian copy is final — never rewrite it.

**Why this exists:** highlights are profile furniture for the cold visitor who lands from the $25 ad. Each kills one doubt: *how does it work → is it for me → what do I get → what will it cost me to find out → what if I have questions.* Single CTA everywhere: бесплатный аудит. No case study in this batch (future «Кейс» highlight).

**Status:** v5 2026-07-21 — **the pipeline switched from cropping to fitting; the v4 images are approved-shape and h1s1–s3 are ready to post.** The v4 prompts fixed the drawn-container stripes (zero seams) and the line breaks landed, but text width did not move — the model draws each line bigger to fill whatever width it has, so no prompt gets content inside a 56% crop window. Rather than burn more runs on it, `crop916.py` now **fits** the square into 9:16 instead of cropping, and nothing can be cut. Covers c1–c5 ✅ · h1s1–s3 done ✅ · h1s4–s6 + h2–h5 to generate · not posted.

*(v4 2026-07-21 — composition law added after the h1 run failed 4/4: two overflowed the crop line, two shipped drawn stripes. v3 2026-07-20 — first run scrapped: ref-chaining bled duplicate/corrupted text.)*

---

## 0. Hard rules

- **All visible text Russian**, exact copy below, final. Agency «мы». Banned: CAC, лиды, конверсия, ROI, performance, трафик. Never mention price.
- **Tokens:** bg `#0A0C0B`, text `#F1F4EC`, muted `#98A29A`, single lime accent `#B4FF3A`, clean geometric sans-serif, flat minimal, no photos/people/gradients/watermarks.
- **Wordmark stamp = `@voronka.tm`** (with the @ — it's our IG handle, not a domain; law in `brand/content-rules.md` §2). Hook stories carry it; middle/CTA stories don't (fewer text elements = safer Cyrillic).
- **PROMPT DISCIPLINE (the model draws your instructions):** only name text by its **exact literal string**. Never write "label", "caption", "marker", "brackets", "connectors", "frames", "motifs" — they render as gibberish (`monopcme line`, `MICGER`) or doodles (rocket, eye, magic wand). Never put pixel numbers, ratios, or "safe zone" in a prompt — they get printed. Short prompts, a small closed list of elements, end with an explicit ban on anything else. Use the prompts below verbatim.
- **COMPOSITION (`brand/content-rules.md` §8 — read it):** never name a container ("column", "band", "strip", "panel") — the model draws it as a visible rectangle and the stripes survive into the story. Say only *"keep the left and right sides completely empty dark background."* Dictate headline line breaks (they control wrapping, not width — width is unfixable, which is why we fit instead of crop). Props stack **above/below/in-hand**, never "beside him."
- **NO text-bearing reference images — generate every flat story STANDALONE.** (Learned 2026-07-20: chaining the hook story as a reference made the model blend the reference's text into new images — duplicated ghost lines like «Заявка мгновенно проходит сат.» over the real line. That run was scrapped.) Consistency comes from the identical templates + style block, which is enough for this flat design. The ONLY reference images ever attached are the character refs on T1 stories — and those prompts explicitly forbid copying text from them.

## 1. Format: 1:1 generation → 9:16 crop (this is the pipeline, don't fight it)

Your image tool only outputs **1:1**. That's fine — we designed for it:

1. **Nothing gets cropped — the square is FITTED into the story.** `crop916.py` scales the whole square to full story width and extends its top and bottom edges to fill 9:16. No content can be cut, so composition can't fail the way it did in v3/v4. Two things still matter in the prompt: **never name a container** ("column", "band", "strip", "panel") — the model draws it as a rectangle and the stripes ruin a fitted story too — and **stack props above/below/in-hand, never beside him**, or the character ends up small and lost. Never put measurements or ratios in a prompt.
2. **Save** generated PNGs to `automations/ig-poster/highlights/` with the exact filenames below.
3. **Fit to 9:16** (scales to 1080×1920, flattens to brand black, writes `<name>.jpg` next to each PNG; sources untouched):
   ```
   cd "D:\ai projects\vaios\automations\ig-poster"
   python crop916.py --folder highlights
   ```
4. The `.jpg` files are the deliverables Operator will post from his phone (§5). Covers `c1.png`…`c5.png` stay square — never run them through crop916.

*(`--crop --check` is the legacy center-crop path, kept for images deliberately composed narrow. Don't reach for it by default: the generator will not draw text narrow enough on request — proven across two full runs.)*

## 2. QC gate (one fail = regenerate)

**On the square PNG, before fitting:**

- [ ] **No vertical seams.** View at 100% and scan for full-height lines where the background tone shifts — that's a drawn container and it survives into the story. Regenerate; don't try to retouch it.
- [ ] Text lines broken as the table's `_LINES` variable specifies — no word hyphenated across lines, no orphan single word on its own line.
- [ ] Character (T1 only) large enough to read as the hero of the frame, not shrunk by something placed off to his side.

**On the fitted .jpg:**

- [ ] Every Russian word matches this file exactly — zoom in, letter by letter. **No duplicated/ghost text blocks** (the 2026-07-20 run failed with the DESC rendered twice, one copy corrupted), no invented text/numbers/labels/doodles.
- [ ] T1 character stories: run the full `brand/character.md` §6 checklist (face vs ref-02, flag patch, no foreign logos, no blue).
- [ ] The join between the square and the extended top/bottom bands is invisible — no visible horizontal edge. (If a design ever has bright content running to the square's very top or bottom edge, the band will smear it; recompose with dark edges.)
- [ ] Lime the only accent; body noticeably smaller than the headline; 1080×1920.
- [ ] One wrong letter → regenerate, or edit the image: `Fix the text to say "..." exactly, change nothing else.`

## 3. Approval flow (mandatory)

1. Finish a full highlight (all stories generated, cropped, QC passed).
2. Show Operator the cropped set + which highlight it is. WAIT.
3. Approve → post per §4. "Fix X" → fix, re-show. No answer = no post.
4. After posting, remind Operator to assemble the highlight in-app **the same day** (stories die in 24h).

---

## 4. The 5 highlights

Build/post order below (newest highlight shows leftmost on the profile, so posting in this order puts «Вопросы»/«Аудит» first where thumbs land — intended). In-app names: **Система · Для кого · Результат · Аудит · Вопросы**.

**Shared style block** `{STYLE}` (appended to every T2/T3 prompt — NOT to T1, which has its own character style):

> Style: minimal flat vector design, clean and uncluttered. Solid near-black #0A0C0B background with lots of empty dark space and a very subtle deep-green tint in the corners. Off-white #F1F4EC headline text, muted gray #98A29A secondary text, a single electric-lime #B4FF3A accent. Clean geometric sans-serif at standard mobile app text sizes — the headline at the size stated above, the secondary text noticeably smaller, never giant poster type. Do not add any text, letters, numbers, labels, captions, frames, brackets, symbols or decorative doodles other than the exact elements listed above. No photos, no people, no watermarks.

### Story prompt templates

**T1 — character hook story** (first story of each highlight — Style A, the brand character opens every highlight). **Attach `brand/character-refs/ref-02-hero-closeup-flag-jacket.png` + `ref-03-full-sheet-poses-expressions.png` as reference images, every time.** QC these against `brand/character.md` §6.

```
A square cinematic image. Everything sits close to the middle of the image, stacked from top to bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. In the upper half, over clean dark background, only this text:
- Small muted-gray text: @voronka.tm
- An off-white headline, each line short and centered, broken exactly like this: {HOOK_LINES}
- Smaller muted-gray text below it, on {SUB_LINES}: "{SUB}"
In the lower half, centered: {SCENE}

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere. No other logos, no watermarks, no English text.

Render each text exactly as written, once — no repeated or extra words, no other text or symbols, and do not copy any text, labels or logos from the reference images. The background is one single continuous flat dark surface, even and unbroken from edge to edge.
```

`{HOOK_LINES}` is written out as one quoted fragment per line, e.g. `"Откуда берутся" / "клиенты" / "из Instagram?"`. `{SUB_LINES}` = `one line` or `two lines`. **The character is centered and faces forward; every prop is above him, below him, or in his hands — never off to one side.**

**T2 — content story** (middle stories — flat, standalone, NO reference images):

```
A minimal square graphic. Everything sits close to the middle of the image, stacked from top to bottom, with empty dark space at the very top and the very bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. Centered, top to bottom, only these things:
- {NUMBER_LINE}
- {TITLE_SIZE} off-white headline, each line short and centered, broken exactly like this: {TITLE_LINES}
- Smaller muted-gray text below it, on {DESC_LINES}, each line short: "{DESC}"
- Below that, one lime line-art icon with a soft dim lime glow around it in the dark background: {ICON}
Render each text exactly as written, once — no repeated or extra words, and no other text, numbers, labels or symbols besides the icon. The background is one single continuous flat dark surface, even and unbroken from edge to edge.
{STYLE}
```

- `{NUMBER_LINE}` = `A large lime number: {NUM}` if the story has a step number — otherwise omit the line entirely.
- `{TITLE_LINES}` = one quoted fragment per line, e.g. `"Сайт" / "с заявкой"`.
- `{TITLE_SIZE}` = `A large` normally. **If any word in the title is longer than ~12 characters, use `A medium` instead** — long words cannot wrap and will otherwise set the block width themselves. Never hyphenate a Russian word across lines.
- `{DESC_LINES}` = `two lines` / `three lines`.

**T3 — CTA story** (last story of each highlight — flat, standalone, NO reference images). Operator posts these manually and places a **real link sticker** in the empty area — so the image must leave that area completely blank. Deliberate, don't fill it:

```
A minimal square graphic. Everything sits close to the middle of the image, stacked from top to bottom, with empty dark space at the very top and the very bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. Centered, top to bottom, only these things:
- {CTA_SIZE} off-white headline, each line short and centered, broken exactly like this: {CTA_HEAD_LINES}
- Smaller muted-gray text below it, on {CTA_SUB_LINES}, each line short: "{CTA_SUB}"
- Below that, a lime arrow pointing straight down at a large empty dark area lit by a soft dim lime glow from below — leave that whole area completely empty, do not draw anything or write any words in it
- Near the bottom, small muted-gray text: "или напишите «аудит» в Direct"
Render each text exactly as written, once — no repeated or extra words, no other text or symbols. The background is one single continuous flat dark surface, even and unbroken from edge to edge.
{STYLE}
```

Same line-break discipline as T2: `{CTA_HEAD_LINES}` = one quoted fragment per line, `{CTA_SIZE}` drops to `A medium` if any word exceeds ~12 characters, `{CTA_SUB_LINES}` = `two lines` / `three lines`.

---

### Highlight 1 — «Система» (6 stories) — how it works

Files `h1s1.png` … `h1s6.png` (→ `.jpg` after crop).

| # | Template | Text / variables |
|---|---|---|
| 1 | T1 | HOOK_LINES: `"Откуда берутся" / "клиенты" / "из Instagram?"` · SUB_LINES: `two lines` · SUB: `Не из красивого профиля. Из системы.` · SCENE: the character half-body, centered, facing forward, friendly confident smirk, one open hand held out palm-up in front of his chest with a small glowing lime funnel of four narrowing segments floating just **above** the palm |
| 2 | T2 | NUM: `01` · TITLE_SIZE: `A medium` (Таргетированная = 15 chars) · TITLE_LINES: `"Таргетированная" / "реклама"` · DESC_LINES: `three lines` · DESC: `Вашу рекламу видят те, кому она действительно нужна` · ICON: a target with a crosshair |
| 3 | T2 | NUM: `02` · TITLE_SIZE: `A large` · TITLE_LINES: `"Сайт" / "с заявкой"` · DESC_LINES: `two lines` · DESC: `Клиент оставляет номер за 10 секунд` · ICON: a smartphone with a form field and a button |
| 4 | T2 | NUM: `03` · TITLE_SIZE: `A large` · TITLE_LINES: `"Telegram-бот"` · DESC_LINES: `two lines` · DESC: `Заявка мгновенно приходит вам в телефон` · ICON: a paper-plane chat bubble with a notification dot |
| 5 | T2 | NUM: `04` · TITLE_SIZE: `A large` · TITLE_LINES: `"CRM" / "и аналитика"` · DESC_LINES: `three lines` · DESC: `Видно, откуда пришёл клиент и сколько стоила заявка` · ICON: a clean table with a small rising chart |
| 6 | T3 | CTA_SIZE: `A large` · CTA_HEAD_LINES: `"Покажем, как это" / "будет работать" / "у вас"` · CTA_SUB_LINES: `two lines` · CTA_SUB: `Бесплатный аудит — 10 минут, без обязательств` |

### Highlight 2 — «Для кого» (5 stories) — is it for me?

Files `h2s1.png` … `h2s5.png`.

| # | Template | Text / variables |
|---|---|---|
| 1 | T1 | HOOK_LINES: `"Кому это" / "подходит?"` · SUB_LINES: `two lines` · SUB: `Малому и среднему бизнесу в Туркменистане` · SCENE: the character half-body, centered, facing forward, warm smile, both arms open in a welcoming gesture, palms up, kept close to his body |
| 2 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Магазины" / "Кафе" / "Доставка"` · DESC_LINES: `three lines` · DESC: `Товары и еда — реклама приводит покупателей и заказы` · ICON: a shopping bag |
| 3 | T2 | TITLE_SIZE: `A medium` (Барбершопы = 10, but three long words) · TITLE_LINES: `"Салоны" / "Барбершопы" / "Услуги"` · DESC_LINES: `three lines` · DESC: `Записи и обращения приходят сами — без ожидания в Direct` · ICON: scissors |
| 4 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Обучение" / "Курсы" / "Клиники"` · DESC_LINES: `two lines` · DESC: `Заявки от тех, кто уже ищет вашу услугу` · ICON: a graduation cap |
| 5 | T3 | CTA_SIZE: `A large` · CTA_HEAD_LINES: `"Не нашли" / "свою нишу?"` · CTA_SUB_LINES: `four lines` · CTA_SUB: `Не важно, что вы продаёте. Важно, что вам нужны клиенты — разберём на бесплатном аудите` |

### Highlight 3 — «Результат» (6 stories) — what do I get?

Files `h3s1.png` … `h3s6.png`.

| # | Template | Text / variables |
|---|---|---|
| 1 | T1 | HOOK_LINES: `"Что вы" / "получаете"` · SUB_LINES: `two lines` · SUB: `Не лайки. Заявки и продажи.` · SCENE: the character half-body, centered, facing forward, proud smile, holding a phone up in front of his chest with both hands; the screen glows soft lime and shows only glow, no readable text |
| 2 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Поток заявок" / "каждый день"` · DESC_LINES: `three lines` · DESC: `Реклама работает — номера клиентов приходят вам в телефон` · ICON: a phone with incoming notification cards |
| 3 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Ни одного" / "потерянного" / "клиента"` · DESC_LINES: `three lines` · DESC: `Каждый, кто оставил номер, записан в CRM-таблицу` · ICON: a checklist with checkmarks |
| 4 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Понятные" / "цифры"` · DESC_LINES: `three lines` · DESC: `Видно, что приносит заявки, а что — просто тратит бюджет` · ICON: a simple bar chart |
| 5 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Ваше время" / "— бизнесу"` · DESC_LINES: `four lines` · DESC: `Рекламу, сайт и таблицы ведём мы. Вы отвечаете на заявки и продаёте` · ICON: a clock with a checkmark |
| 6 | T3 | CTA_SIZE: `A large` · CTA_HEAD_LINES: `"Хотите" / "так же?"` · CTA_SUB_LINES: `three lines` · CTA_SUB: `Начнём с бесплатного аудита — покажем, где вы теряете клиентов` |

### Highlight 4 — «Аудит» (5 stories) — the offer itself, de-risked

Files `h4s1.png` … `h4s5.png`.

| # | Template | Text / variables |
|---|---|---|
| 1 | T1 | HOOK_LINES: `"Что такое" / "бесплатный" / "аудит?"` · SUB_LINES: `two lines` · SUB: `10 минут по телефону. Бесплатно и без обязательств.` · SCENE: the character half-body, centered, facing forward, relaxed friendly smile, holding a phone to his ear with one hand, elbow tucked in close to his body |
| 2 | T2 | NUM: `01` · TITLE_SIZE: `A large` · TITLE_LINES: `"Разберём ваш" / "профиль и нишу"` · DESC_LINES: `two lines` · DESC: `Посмотрим, как клиенты находят вас сейчас` · ICON: a magnifying glass over a profile card |
| 3 | T2 | NUM: `02` · TITLE_SIZE: `A large` · TITLE_LINES: `"Покажем, где" / "теряются клиенты"` · DESC_LINES: `three lines` · DESC: `Конкретные места, где вы теряете заявки и продажи` · ICON: a funnel with a drop leaking from a crack |
| 4 | T2 | NUM: `03` · TITLE_SIZE: `A large` · TITLE_LINES: `"Предложим" / "план"` · DESC_LINES: `three lines` · DESC: `Что настроить, чтобы заявки пошли. Решение — за вами.` · ICON: a map route with a lime pin at the end |
| 5 | T3 | CTA_SIZE: `A large` · CTA_HEAD_LINES: `"Записаться —" / "10 секунд"` · CTA_SUB_LINES: `three lines` · CTA_SUB: `Оставьте номер — мы перезвоним в течение рабочего дня` |

### Highlight 5 — «Вопросы» (6 stories) — objections, answered honestly

Files `h5s1.png` … `h5s6.png`. Answers mirror the live LP FAQ — don't drift.

| # | Template | Text / variables |
|---|---|---|
| 1 | T1 | HOOK_LINES: `"Частые" / "вопросы"` · SUB_LINES: `one line` · SUB: `Коротко и честно` · SCENE: the character half-body, centered, facing forward, curious smile, thinking pose with his chin resting on one hand, elbow tucked in close to his body |
| 2 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Сколько" / "это стоит?"` · DESC_LINES: `five lines` · DESC: `Зависит от задач вашего бизнеса. Начнём с бесплатного аудита — разберём ситуацию и предложим решение.` · ICON: a price tag with a question mark |
| 3 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"Как быстро" / "будут заявки?"` · DESC_LINES: `three lines` · DESC: `Обычно первые заявки приходят уже в первые дни после запуска рекламы` · ICON: a stopwatch |
| 4 | T2 | TITLE_SIZE: `A medium` (настраивать? = 12 chars) · TITLE_LINES: `"Мне нужно" / "что-то" / "настраивать?"` · DESC_LINES: `three lines` · DESC: `Нет. Мы настроим всё под ключ — вам останется отвечать на заявки` · ICON: a toggle switch set to on |
| 5 | T2 | TITLE_SIZE: `A large` · TITLE_LINES: `"А если у меня" / "нет сайта?"` · DESC_LINES: `three lines` · DESC: `Сделаем простую страницу с формой заявки — она входит в работу` · ICON: a browser window with a lime plus sign |
| 6 | T3 | CTA_SIZE: `A large` · CTA_HEAD_LINES: `"Остался" / "вопрос?"` · CTA_SUB_LINES: `three lines` · CTA_SUB: `Зададите его на бесплатном аудите — заодно разберём ваш профиль` |

---

## 5. Posting & assembling — MANUAL, by Operator (agent only delivers files)

After approval, the agent's last step: get the files onto The phone — the whole approved set of cropped story `.jpg`s plus the 5 square covers `c1.png`…`c5.png` (easiest: Operator drags them into Telegram Saved Messages; agent just reminds him and lists the exact filenames per highlight).

**Operator, one highlight per day, 5 days, in the IG app:**

1. Post the highlight's stories **in order s1 → sN** to your story (from gallery).
2. On the **CTA story (last one): add the link sticker** in the big empty area under the arrow → URL `https://voronkatm.com` → edit sticker text to «Бесплатный аудит».
3. **Same day** (stories die in 24h): Profile → «+» / New highlight → select today's stories s1…sN → name it exactly (`Система` / `Для кого` / `Результат` / `Аудит` / `Вопросы`) → Edit cover → choose from gallery → pick the icon cover (`c1`…`c5`) → save.

Day order: Day 1 «Система» → Day 2 «Для кого» → Day 3 «Результат» → Day 4 «Аудит» → Day 5 «Вопросы».

## 6. After the batch

- Update the Status line here (dates, media ids per highlight).
- Update `funnel/01-instagram.md`: check off the Highlights blocker, list the 5 live highlights.
- Log in `decisions/log.md`: highlights shipped (5 doubt-killers, audit-only CTA, case study deferred to «Кейс»).
- Next milestone: the case-study post → «Кейс» highlight.
