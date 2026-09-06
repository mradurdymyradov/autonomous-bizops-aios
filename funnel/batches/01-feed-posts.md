# IG Content Batch 01 v3 — 3 posts, new brand system (agent-executed)

**For Antigravity (executor).** This file is the whole job. Workflow: read this file + `brand/character.md` + `brand/content-rules.md` → generate every image with Nano Banana 2 → run QC → **show Operator and WAIT for his approval** → on approval, post automatically via `automations/ig-poster/post.py`. Do not post anything without an explicit "approve" from Operator. Russian copy is final — never rewrite it.

**Status:** Published 2026-07-21 · Post 1 (Carousel 6 slides): 18370366378237735 · Post 2: 18225743437320236 · Post 3: 17898538605480915.
**Note:** the old flat v1 versions of these 3 posts are already live on @voronka.tm (2026-07-12). At approval time, ask Operator: keep them or archive/delete in-app after the new ones publish.

---

## 1. Setup (executor checklist)

- **Model:** use your built-in image generation tool (Nano Banana 2).
- **Aspect ratio:** request **4:5** (1080×1350) as a generation parameter, 2K if available. If the model path only returns 1:1: compose everything in a centered vertical column with wide empty dark side margins and crop to 4:5 afterward — never squeeze or stretch.
- **Character images:** ALWAYS attach `brand/character-refs/ref-02-hero-closeup-flag-jacket.png` + `ref-03-full-sheet-poses-expressions.png` as reference images. Never generate him from text alone (`brand/character.md` §1).
- **Posting:** runs on The Windows machine, **VPN ON**. Check `post.log` for `PUBLISHED ✅` after each publish. Connection-refused = VPN off → tell Operator, retry.
- **Files:** save finished images to `automations/ig-poster/` with the exact filenames below (overwrite leftovers with the same names).

## 2. Hard rules (recap — full law in the two brand files)

- All visible text Russian, spelled EXACTLY as written. Latin only for brand names (Instagram, Telegram, CRM, voronka.tm).
- Tokens: bg `#0A0C0B` (deep green tint allowed in character scenes), text `#F1F4EC`, muted `#98A29A`, single accent lime `#B4FF3A`. Headline pattern: off-white sentence with ONE key word in lime.
- Wordmark stamp = `@voronka.tm` (with the @ — it's our IG handle, not a domain; see `brand/content-rules.md` §2). Skipped on scenes where the background neon already carries `voronka.tm`.
- Character: face/hair/outfit/flag patch identical to refs. Never reproduce "TRADING", Nike, Atlético, Plus500 or any invented logo. Background signage, if any, reads only "voronka.tm" in lime.
- Never show price. CTA everywhere: бесплатный аудит → ссылка в шапке профиля.
- **Prompt discipline (learned the hard way — the model draws your instructions):** prompts below are final, use them verbatim. Never add meta-words ("safe zone", pixel numbers, "label", "marker", "decorative elements") when editing prompts — the model prints them as gibberish text or doodles. Only ever name text by its exact literal string.

### QC gate (before showing Operator; one fail = regenerate)

- [ ] Every Russian word matches this file exactly — zoom in, letter by letter. No repeated words (`работать работать`), no invented text/numbers/doodles.
- [ ] Character checklist from `brand/character.md` §6: face matches ref-02, flag patch present + glowing, no foreign logos, no blue accent.
- [ ] Lime is the only accent; wordmark present; ratio 4:5; no watermarks.
- [ ] Misspelled single word → edit endpoint: `Fix the text to say "..." exactly, change nothing else.` Face drift → regenerate with stronger reference weighting.

## 3. Approval flow (mandatory)

1. Generate ALL images for a post, pass QC.
2. Show Operator the finished set (previews + filenames) and the caption. Say what will be posted and in what order.
3. WAIT. Only an explicit approve → run the post command. "Fix X" → fix, re-show. No answer = no post.
4. After publish: confirm `PUBLISHED ✅` in `post.log`, note the media id in the Status line of this file.

---

## 4. POST 1 — Carousel «Как к вам приходит клиент» (6 slides, hybrid)

Cover + CTA slide = Style A (character). Inner steps 2–5 = Style B (flat). Files `p1s1.png` … `p1s6.png`, 4:5, 2K.

### Slide 1 — cover · character · refs: ref-02 + ref-03 · `p1s1.png`

```
Instagram carousel cover, 4:5 vertical. Scene: the character stands on the left third of the frame, half-body, friendly confident smirk, one open hand gesturing toward the right side, where a thin glowing lime funnel diagram of four narrowing segments with small flowing dots floats in the dark.

Render exactly this Russian text, each string once:
- small muted gray text top left: "@voronka.tm"
- large off-white headline in the upper right area: "Как к вам приходит клиент", with only the word "клиент" in electric lime
- smaller muted gray line under it: "Система из 4 частей — от рекламы до звонка"
- small lime text bottom right: "листайте →"

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere. Background neon signage, if any, reads "voronka.tm" in lime. No other logos, no watermarks, no English text. No other text than the strings listed above.
```

### Slides 2–5 — flat steps · one template, 4 runs · NO reference images (generate standalone)

Never attach a previous slide as a reference — images containing text bleed their text into the new generation (proven failure: duplicated ghost lines). The identical template + tokens keep the slides consistent on their own. Template (substitute variables from the table):

```
Instagram carousel slide, 4:5 vertical, minimal flat vector design, no people. Solid near-black #0A0C0B background with generous empty dark space. In the lower half, one large minimal flat lime line-art icon: {ICON}.

Render exactly this Russian text, each string once:
- large lime number top left: "{NUM}"
- off-white headline: "{TITLE}", with only the word "{LIME_WORD}" in electric lime
- smaller muted gray line under it: "{DESC}"
- small muted gray text bottom left: "@voronka.tm"
- a row of four small dots bottom right, dot number {N} filled lime, the others hollow

Off-white #F1F4EC text, muted gray #98A29A secondary text, electric lime #B4FF3A the only accent, clean geometric sans-serif. No photos, no gradients, no watermarks, no other text or symbols than the elements listed above.
```

| Slide | NUM | N | TITLE | LIME_WORD | DESC | ICON |
|---|---|---|---|---|---|---|
| p1s2 | 01 | 1 | Таргетированная реклама | реклама | Показываем вашу рекламу в Instagram тем, кому это интересно | a target with a crosshair |
| p1s3 | 02 | 2 | Сайт с заявкой | заявкой | Клиент за 10 секунд оставляет свой номер телефона | a smartphone with a simple form field and a button |
| p1s4 | 03 | 3 | Telegram-бот | Telegram | Каждая заявка сразу приходит вам в телефон | a paper-plane chat bubble with a notification dot |
| p1s5 | 04 | 4 | CRM и аналитика | аналитика | Все клиенты в одном месте. Видно, сколько стоила каждая заявка | a clean table with a small rising chart |

### Slide 6 — CTA · character · refs: ref-02 + ref-03 · `p1s6.png`

```
Instagram carousel final slide, 4:5 vertical. Scene: the character stands on the right side, half-body, friendly confident smirk, one hand pointing down toward a lime rounded-rectangle button in the lower left area.

Render exactly this Russian text, each string once:
- large off-white headline in the upper area: "Хотите так же?", with only "так же" in electric lime
- smaller muted gray line under it: "Бесплатный аудит — покажем, где вы теряете клиентов"
- inside the lime button, dark bold text: "Ссылка в шапке профиля"
- small muted gray text at the bottom: "@voronka.tm"

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere. Background neon signage, if any, reads "voronka.tm" in lime. No other logos, no watermarks, no English text. No other text than the strings listed above.
```

### Caption (post exactly this)

```
Заявки из Instagram приносит не красивый профиль, а система.

Вот как она устроена:

1. Таргетированная реклама — показываем вас тем, кому это интересно
2. Сайт с заявкой — клиент оставляет номер за 10 секунд
3. Telegram-бот — заявка сразу у вас в телефоне
4. CRM и аналитика — видно, откуда пришёл каждый клиент и сколько стоила заявка

Четыре части работают вместе — и заявки приходят каждый день, без вашего участия.

Хотите посмотреть, как это будет работать в вашем бизнесе? Бесплатный аудит — ссылка в шапке профиля.

#туркменистан #ашхабад #бизнес #реклама #маркетинг
```

### Post command (after approval)

```
cd "D:\ai projects\vaios\automations\ig-poster"
python post.py --image p1s1.png p1s2.png p1s3.png p1s4.png p1s5.png p1s6.png --caption "<caption above>" --type carousel
```

---

## 5. POST 2 — Character post «Клиенты есть — но до вас не доходят»

Pillar 2 (разбор/education), Style A. File `p2.png`, 4:5, 2K, refs: ref-02 + ref-03. The 4 pains live in the caption — the image carries the emotional hook only.

### Prompt

```
Instagram post, 4:5 vertical. Scene: the character in a thinking pose, chin resting on his hand, looking slightly up at the headline, half-body on the right side of the frame, in a dark modern office with a soft out-of-focus lime "voronka.tm" neon sign far in the background.

Render exactly this Russian text, each string once:
- large off-white headline in the upper left area, wrapping to two lines: "Клиенты есть в Instagram — но до вас не доходят", with only "не доходят" in electric lime
- smaller lime line lower left: "Причина одна: нет системы"

(No corner stamp on this one — the background neon sign already carries "voronka.tm", per brand/content-rules.md §2.)

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere. No other logos, no watermarks, no English text. No other text than the strings listed above.
```

### Caption (post exactly this)

```
Знакомо?

Профиль ведёте, посты выходят — а новых клиентов нет. Реклама была — бюджет ушёл, результата нет. Кто-то написал в Direct — и потерялся среди сообщений.

Проблема не в вас и не в Instagram. Просто лайки не превращаются в продажи сами по себе. Это делает система: реклама → сайт с заявкой → Telegram-бот → CRM.

Мы разберём ваш профиль и покажем, где именно теряются клиенты. Бесплатно, за 10 минут.

Ссылка на бесплатный аудит — в шапке профиля.

#туркменистан #ашхабад #бизнес #реклама #продажи
```

### Post command (after approval)

```
python post.py --image p2.png --caption "<caption above>"
```

---

## 6. POST 3 — Character post «Реклама без догадок» (аналитика/CRM)

Pillar 1 (система) with a proof-of-competence angle, Style A. File `p3.png`, 4:5, 2K, refs: ref-02 + ref-03.

### Prompt

```
Instagram post, 4:5 vertical. Scene: the character stands on the left side, half-body, confident smirk, pointing with one finger at a large dark floating dashboard panel on the right — the panel has thin lime borders, a small abstract table of soft blurred rows and a small rising lime line chart, with no readable text, letters or numbers anywhere on the panel.

Render exactly this Russian text, each string once:
- large off-white headline in the upper area: "Реклама без догадок", with only "без догадок" in electric lime
- smaller muted gray line under it: "Видно, сколько стоит каждая заявка"
- small muted gray text at the bottom: "@voronka.tm"

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere. No other logos, no watermarks, no English text. No other text than the strings listed above.
```

The dashboard must stay text-free (blurred abstract rows) — this is deliberate, so Cyrillic can't corrupt and no fake numbers appear. Never let the model add readable values to it.

### Caption (post exactly this)

```
Обычно реклама выглядит так: заплатили — и надеетесь, что сработает.

У нас по-другому. Каждая заявка записана в CRM-таблицу: откуда пришёл человек, что его заинтересовало и во сколько обошлась его заявка. Вы открываете таблицу и видите всю картину.

Реклама перестаёт быть лотереей — становится понятным инструментом: что работает, то усиливаем, что не работает — выключаем.

Хотите увидеть эти цифры по своему бизнесу? Бесплатный аудит — ссылка в шапке профиля.

#туркменистан #ашхабад #бизнес #аналитика #маркетинг
```

### Post command (after approval)

```
python post.py --image p3.png --caption "<caption above>"
```

---

## 7. Posting order & schedule

Post 1 (carousel) → Post 2 → Post 3, one per day, 19:00–21:00 Ashgabat. Each post goes through the §3 approval flow separately — generate and get approval for Post 1 before spending generations on 2 and 3 (The feedback on the first character images will tune the rest).

## 8. After the batch

- Update the Status line here with media ids and dates.
- Update `funnel/01-instagram.md` content status.
- Log in `decisions/log.md`: batch-01 regenerated in the character brand system (v3), old flat posts kept/removed (whichever Operator chose).
- Next milestone unchanged: the **case-study hero post** («пара долларов за клиента», per core §proof) — its own batch, character celebrating, understated wording.
