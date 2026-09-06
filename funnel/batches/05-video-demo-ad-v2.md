# Content Batch 05 — video demo ad v2 (dead phone → заявки, Veo 3.1 + LP screen recording)

**For Antigravity (executor).** Your job is §1 only: generate **`img-1-dead-phone.png`**, QC it against `brand/character.md` + `brand/content-rules.md`, show Operator, WAIT. §2 (`img-2-phone-full.png`) is **OPTIONAL** — skip it unless Operator asks for the 2-clip cut. Do NOT touch the video model, do NOT assemble, do NOT post. Operator runs Omni Flash and edits himself.

**For Operator:** §3 (Omni Flash prompt), §4 (your phone recording), §5 (voiceover), §6 (assembly) are yours.

**Why:** proven format (hook → LP screen recording → end card; previous run 12 заявок / 7 sales on $20). v2 swaps the static hook for a ~10s AI hook: one Omni Flash clip from image 1 → then your real phone recording of leaving a заявка on voronkatm.com. Concept: **мёртвый телефон → взрыв заявок.** Reads with the sound off, one object (phone) carries the whole ad.

**Read first:** `brand/character.md` (character law), `brand/content-rules.md` (tokens, composition §8). Refs: `brand/character-refs/ref-02-hero-closeup-flag-jacket.png` + `ref-03-full-sheet-poses-expressions.png`.

**Status:** created 2026-07-23. Images not generated.

---

## 0. Hard rules (recap)

- **Ratio: 9:16 vertical, 2K.** This is a video, not a square feed static.
- **All visible text Russian**, exact strings below, final. Banned: CAC, лиды, конверсия, ROI, performance, трафик. **Never any price.**
- **Tokens:** bg `#0A0C0B`, text `#F1F4EC`, muted `#98A29A`, single lime accent `#B4FF3A`. No blue, ever.
- **Keep on-image text minimal** — fewer text zones = safer Cyrillic AND less to warp when Veo animates it. Each image lists its exact text; add NOTHING else.
- **Composition (`content-rules.md` §8):** never name a container (column/band/strip/panel/frame → drawn as a rectangle). Keep left/right empty dark. Character centered, half-body, facing forward, phone **in his hands**. Dictate line breaks. Never hyphenate Cyrillic.
- **Character images:** attach `ref-02` + `ref-03` every time with the do-not-redesign instruction + "do not copy any text, labels or logos from the reference images." Flag patch visible (crescent + 5 stars + red ornament stripe). No TRADING/Nike/Atlético/Plus500.
- **Wordmark law:** both scenes carry a background lime neon `voronka.tm` → **no corner stamp** on either.
- **Consistency:** matches `funnel/00-core.md`. Agency «мы», client «вы». Same character, same wardrobe on both images.

## 1. Image 1 — dead phone (source for Veo clip 1)

File: `automations/meta-ads/creatives/img-1-dead-phone.png`

Text elements (exactly these, nothing else):
- Headline, off-white, centered, broken exactly on two lines: line 1 `"Инстаграм есть,"` line 2 `"а клиентов нет?"` — the word `"клиентов"` in electric lime
- Background neon: `"voronka.tm"` in lime (so: NO corner stamp)
- The phone screen: **empty and dark — no text on it at all**

Prompt (verbatim):

```
A vertical 9:16 cinematic image, 2K. Everything sits close to the middle, stacked from top to bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. In the upper part, over clean dark background, only this text: an off-white headline, each line short and centered, broken exactly like this: "Инстаграм есть," on the first line, "а клиентов нет?" on the second line, with the single word "клиентов" colored electric lime #B4FF3A. In the lower part, centered: the character half-body facing forward, holding a phone up in both hands in front of his chest, looking down at the phone screen with a slightly bored, disappointed expression, shoulders a little slumped. The phone screen is completely dark and empty — no notifications, no icons, no text on the screen at all. Behind him, small and soft in the dark background, a lime neon sign reads "voronka.tm". Do not add any other text, letters, numbers, symbols or decorations besides the exact elements listed above.

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Do not copy any text, labels or logos from the reference images. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere.
```

References: attach `ref-02` + `ref-03`.

## 2. Image 2 — phone full of заявки (OPTIONAL — only for a 2-clip cut)

**Not needed for the Omni Flash single-clip route.** Generate this only if Operator decides to do a two-clip version (empty phone → hard cut → text-full phone) for a sharper, legible «Новая заявка» payoff.

File: `automations/meta-ads/creatives/img-2-phone-full.png`

Same character, same wardrobe, same framing as image 1 (so the Veo cut feels like one shot). Only the screen and his expression change.

Text elements (exactly these, nothing else):
- On the phone screen: a short vertical stack of **three identical** notifications, each reading exactly `"Новая заявка"`, one under another
- Background neon: `"voronka.tm"` in lime (so: NO corner stamp)
- No headline

Prompt (verbatim):

```
A vertical 9:16 cinematic image, 2K. Everything sits close to the middle, stacked from top to bottom. Keep the left side and the right side of the image completely empty dark background — nothing there at all. In the lower-center, the character half-body facing forward, smiling wide with excitement, holding a phone up in both hands in front of his chest. The phone screen glows bright green and shows a short vertical stack of three identical clean notifications, each reading exactly "Новая заявка", stacked one under another. The green glow from the screen lights up his face from below. Behind him, small and soft in the dark background, a lime neon sign reads "voronka.tm". Do not add any other text, letters, numbers, badges, counters, symbols or decorations besides the three "Новая заявка" notifications and the neon sign.

Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Do not copy any text, labels or logos from the reference images. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere.
```

References: attach `ref-02` + `ref-03`.

### Image QC gate (antigravity: one fail = regenerate)

- [ ] Both: `character.md` §6 checklist — face vs ref-02, flag patch correct + glowing, no TRADING/Nike/Atlético/Plus500, no blue accent.
- [ ] Image 1: headline letter-exact, `"клиентов"` in lime; phone screen truly dark/empty; neon `voronka.tm` present, no corner stamp.
- [ ] Image 2: exactly three `"Новая заявка"` lines, each letter-exact, no gibberish, no numbers/badges; neon present, no stamp.
- [ ] Same character + wardrobe + framing across both images.
- [ ] 9:16, no seams/drawn containers, no watermarks.
- [ ] Show Operator both, WAIT.

---

## 3. Omni Flash animation prompt (Operator — image-to-video in Google Flow)

**Model note:** Gemini Omni Flash — one clip up to **10s, 720p, native audio**, ~$1/clip. One image in → we feed **only `img-1-dead-phone.png`**. The whole dead-phone → заявки arc now happens inside this single 10s clip. Image 2 (§2) is no longer needed for this route — keep it only if you later want a sharper text-full payoff via a 2-clip cut.

**Prompt (verbatim):**

```
Start from this image and animate it as one continuous 10-second shot with subtle, realistic motion. Keep the Russian headline exactly as in the source image — "Инстаграм есть," on the first line and "а клиентов нет?" on the second — same letters, same position, sharp and unchanged the entire time.

0–4s: the character keeps staring at his dark, empty phone, bored and a little deflated — he blinks, lets out a small disappointed breath, shoulders low. The phone screen stays completely dark.
4–6s: the phone screen suddenly wakes up and floods with bright green light from the bottom, lighting his face from below.
6–10s: plain glowing green notification cards, with no text on them, light up on the screen one after another and fill it; his face shifts from bored to surprised to a wide, happy smile; the lime rim light around him pulses brighter. Very slow, very slight camera push-in across the whole shot.

No dialogue, no music, no sound effects. Do not add any new readable text, letters, numbers, logos, objects, extra characters or camera cuts — only light, the phone screen turning on, plain green cards, and the character's expression change.
```

**Omni Flash reality check — don't overreach:**
- Still no legible fresh Cyrillic. The notification cards are **blank green on purpose** — any model that tries to write «Новая заявка» live will warp it. The word «заявки» is carried by the **voiceover + your real screen recording**, not this clip. The clip's only job is the emotional flip: dead → lit up.
- **Native audio:** Omni Flash generates its own sound. We use our own Russian voiceover, so **mute the clip in the edit** and lay §5 over it. The "no dialogue, no music" line helps, but mute anyway.
- **720p:** fine for IG feed/reels (they recompress). Feed a clean high-res source image; optionally upscale the export.
- Only the headline has to survive — one text zone, much safer than the old 2-clip plan. Budget ~2–3 gens; headline drifts → regenerate. If 10s is too long to hold it sharp, trim the export to 8–9s and add a touch more demo.

---

## 4. The phone recording (the demo, ~5–7s)

Phone screen recorder, vertical, one continuous take:
1. Open `voronkatm.com` (let it load).
2. Short scroll: hero → down to the phone form.
3. Tap the field, type a **dummy** number (e.g. `65 00 00 00` — NOT your real one).
4. Tap «Получить бесплатный аудит».
5. Let the success + chatbot greeting appear. Stop.

After: **delete the test row it creates in the «Заявки» sheet.** Keep this at ~9–10s in the edit (speed ~1.0–1.25× only) so the CTA voiceover plays over it in full — don't over-speed it.

---

## 5. Voiceover (Operator — Russian, ElevenLabs Multilingual v2, ~20s, «вы», agency «мы»)

Three beats, timed to the cut:

| Time | Over | Line |
|---|---|---|
| ~0–5s | AI clip, dead phone | «Инстаграм есть, а клиентов нет? Посты выходят, реклама крутится, а заявок всё нет?» |
| ~5–10s | AI clip, phone lights up | «Мы соберём систему, которая приводит заявки сама: реклама ведёт на сайт, заявки падают вам на телефон.» |
| ~10–20s | phone recording | «Чтобы оставить заявку на бесплатный аудит, перейдите на наш сайт, просто нажав на кнопку «Подробнее», и мы разберём, подходит ли вашему бизнесу онлайн-воронка продаж.» |

**Paste this into ElevenLabs — generate all three in ONE pass so the voice/tone stays consistent, then split & align the beats in the editor:**

```
Инстаграм есть, а клиентов нет? Посты выходят, реклама крутится, а заявок всё нет?

Мы соберём систему, которая приводит заявки сама: реклама ведёт на сайт, заявки падают вам на телефон.

Чтобы оставить заявку на бесплатный аудит, перейдите на наш сайт, просто нажав на кнопку «Подробнее», и мы разберём, подходит ли вашему бизнесу онлайн-воронка продаж.
```

**Why it's formatted this way (ElevenLabs v2 specifics):**
- **Keep the ё letters** (всё, соберём, ведёт, разберём) — v2 reads Russian by spelling; ё vs е changes pronunciation. Don't strip them.
- **Punctuation = pacing.** The «?» give the frustrated rising tone in beat 1; the «:» in beat 2 is a natural half-pause; the commas break the long CTA so it doesn't rush. Leave them.
- **Beat pauses:** the blank lines between paragraphs already give a short pause. For a firmer pause synced to the video cuts, drop a break tag between paragraphs — `<break time="0.6s" />` — but use max 2, more can cause audio artifacts.
- **«Подробнее»** in guillemets reads as the plain word. If the voice adds a weird pause around it, delete the « » and just write Подробнее.
- **Settings:** calm, warm male voice; Stability ~50, Similarity ~80, Style low (0–30, keep it un-salesy), Speaker Boost on. If a Speed control shows, ~1.0 (nudge to 1.05 only if it runs long).

Line 2 «заявки падают вам на телефон» is timed to land exactly as the phone lights up green. The CTA is ~9–10s, so keep the phone recording at ~9–10s (don't over-speed it) — total lands ~20s.

No price, no banned words — clean. Keep the read calm and confident, not hype-y (matches the character: warm, never salesy).

---

## 6. Assembly (Operator — CapCut/ffmpeg)

Canvas **1080×1920, 30fps**. Order:
1. Omni Flash clip (muted) → ~10s
2. phone recording → ~9–10s (ends right after the chatbot greeting)
3. optional end card `ad-c-flat.png` → 2s hold, padded on brand black

Upscale the 720p clip to 1080 wide before placing it. 0.2s crossfades at the joins. Voiceover from §5 across the whole thing; **mute the Omni Flash native audio.** No music unless you add it deliberately (feed autoplays muted — the visual + text carry it). Export H.264, ≤60MB, total ~20–22s.

## 7. Final QC (Operator)

- [ ] Headline letter-exact through the full 10s; character on-model.
- [ ] Dead screen → green-lit screen flip lands; his face flips bored → happy; glow ramps.
- [ ] Omni Flash native audio muted; our voiceover synced to the three beats; no price anywhere.
- [ ] Demo legible at speed: URL shows voronkatm.com, dummy number + «Получить бесплатный аудит» tap visible.
- [ ] 1080×1920, ~20s, no black frames at joins.
- [ ] Test row deleted from the «Заявки» sheet.

## 8. After the batch

- Update `funnel/02-meta-ad.md`: v2 video creative status.
- This becomes the hero ad candidate for the next test alongside the batch-04 demo — A/B the two hooks (static-derived vs dead-phone) once both exist. Don't spend more Veo credits until there's a winner.
