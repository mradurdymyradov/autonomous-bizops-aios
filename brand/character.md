# The voronka.tm character — canonical bible

**This file is law for the character.** Every image with him must match this file. Both agents obey it:
- **Claude (AIOS):** when writing image prompts for any batch file, pull the prompt block from here verbatim and reference this file.
- **Antigravity (executor):** before generating any character image, read this file and load the reference images below into Nano Banana 2 as character references. Never generate him from text alone.

*Created 2026-07-17. No name yet — he's "the voronka guy" for now. When we name him, update here first, then everywhere.*

---

## 1. Reference images (the source of truth)

Located in `brand/character-refs/`:

| File | What it is | Use for |
|---|---|---|
| `ref-01-head-body-turnaround.png` | Head turnaround (5 angles) + seated poses + full-body turnaround | Face identity, body proportions, any new angle |
| `ref-02-hero-closeup-flag-jacket.png` | Hero close-up, hands behind head, **canonical jacket with glowing flag patch** | The definitive look: face + wardrobe + flag patch |
| `ref-03-full-sheet-poses-expressions.png` | Full character sheet: standing turnaround, 5 expressions, scene shots | Expressions, poses, scene compositions |

**Workflow rule:** every generation = text prompt + at least `ref-02` and `ref-03` attached as reference images, with the instruction: *"Use the exact same character from the reference images — same face, same hair, same proportions, same outfit. Do not redesign him."* This is what keeps the face identical across the whole grid.

**Known flaw in refs:** backgrounds in ref-02/ref-03 contain a blue neon sign "TRADING" (leftover from the style reference). **Never reproduce it.** Background signage, if any, is always "voronka.tm" in lime. Also ignore/never reproduce: Atlético Madrid crest, Nike logo, "Plus500" text from ref-01 — that jacket branding is replaced by the flag patch (ref-02 is canonical wardrobe).

### 1b. He also talks (HeyGen Avatar IV)

Set up 2026-08-23 so he can front Reels, not just static posts. Full method in
[references/heygen-avatar-iv.md](../references/heygen-avatar-iv.md).

**You do not need to create an avatar.** Upload a cleaned reference as an asset and call
`create_video_from_image`. No group, no look, no training wait.

**Canonical source: `ref-02` at its native 1086×1448** — best resolution, canonical wardrobe, flag
patch visible. It must be prepped once before use:

- **Paint out the "TRADING" neon** (top-right, bright-blue pixels around x 866–1069, y 30–98).
  Patch it with a mirrored, blurred strip of the wall below and feather the seam.
- `ref-01` is unusable at any size — Atlético crest, Nike swoosh, "Plus500", and no flag patch.
- Crops off the `ref-03` sheet work but cap out around 270×365 before upscaling.

Note his hands sit behind his head in `ref-02`, so motion prompts must stay head-and-expression only.
Reached over the **OAuth/MCP** path only — the API key cannot spend subscription credits
(`automations/CAPABILITIES.md` §B3).

A trained photo-avatar look also exists (`eb52a36403ab17341c78435f9e2eae89`, group
`voronka-character`) built from a `ref-03` crop. Lower quality than the `ref-02` route — keep it only
if a clip needs the library entry.

## 2. Who he is

A young Turkmen guy, early 20s energy (drawn youthful, Pixar-style). The friendly, sharp junior partner of the agency — the face cold traffic learns to recognize. He's confident but warm, never smug, never salesy. He demonstrates the system: holds the phone with заявки coming in, points at the CRM screen, celebrates a client's first sale. The glowing Turkmenistan flag on his chest is his identity mark — one look and you know: this is Turkmen, this is voronka.tm.

## 3. Locked visual traits (never change)

- **Style:** premium 3D Pixar-style animation render, soft cinematic lighting, glossy finish. Never flat vector, never anime, never photoreal.
- **Face:** warm tan skin, big brown eyes, thick dark eyebrows, soft rounded features, short fluffy brown hair (textured crop, slightly swept), friendly closed-mouth smirk as default expression.
- **Build:** slim, slightly stylized proportions (biggish head, expressive hands).
- **Wardrobe (canonical, from ref-02):**
  - Dark olive-green track jacket, high collar, zip, single muted khaki stripe on each sleeve
  - **Glowing neon Turkmenistan flag patch on the left chest** — green field, crescent + five stars, red ornament stripe with göls; the glow is bright green leaning lime. This is his "I ❤ TRADING" equivalent — it appears in EVERY image where his chest is visible.
  - Darker olive-green tee underneath with subtle diagonal stripe texture
  - Dark olive joggers, white sneakers with green stripes
- **Allowed variation:** pose, expression (see ref-03: smile, laugh, thinking, serious), camera angle, scene, props (phone, laptop, CRM screen, trophy, tea cup). Seasonal props fine (Novruz, winter jacket over the same fit) — flag patch stays visible.
- **Never:** change hair color/style, eye color, jacket color, remove the flag patch, add other logos, age him up/down, give him glasses/beard/hat unless a deliberate one-off we approve first.

## 4. Prompt block (copy-paste, verbatim)

Claude: paste this into every character prompt after the scene description. Antigravity: expect it, don't strip it.

```
Use the exact same character as in the attached reference images: a young Turkmen guy in premium 3D Pixar-style — warm tan skin, big brown eyes, thick dark eyebrows, short fluffy brown hair, friendly confident smirk, slim stylized build. He wears his signature dark olive-green track jacket with a high collar and a single khaki sleeve stripe, with a glowing neon Turkmenistan flag patch (green field, crescent and five stars, red ornament stripe) on the left chest, over a darker olive tee, olive joggers and white sneakers with green stripes. Same face, same hair, same proportions, same outfit as the references — do not redesign him. Cinematic dark scene: near-black background #0A0C0B with deep green tint, electric lime #B4FF3A rim lighting and glow accents, soft depth of field, glossy premium 3D render, dark moody atmosphere. Background neon signage, if any, reads "voronka.tm" in lime. No other logos, no watermarks, no English text.
```

## 5. Scene vocabulary (what he does on the grid)

Rotate these; they map to what we sell (система: таргет → сайт → бот → CRM):

- Holding a phone showing a Telegram notification with a new заявка (green glow from screen)
- Pointing at a dark dashboard/CRM table with lime accents
- Standing arms-crossed in a dark modern office, lime "voronka.tm" neon behind
- Selfie-style with a happy shop-owner client (generic, non-real person)
- Celebrating: small lime confetti, trophy, "первая продажа" energy
- Thinking pose (chin hand) for "разбор ошибок" educational posts
- With tea (чай) — local touch, casual advice-style posts
- Night city (Ashgabat vibe: white marble buildings ok, no real landmarks reproduced exactly)

## 6. QC checklist for every character image (antigravity: mandatory)

- [ ] Face matches refs (eyes, brows, hair) — zoom in and compare with `ref-02`
- [ ] Flag patch present, correct (crescent + 5 stars + red ornament stripe), glowing
- [ ] No "TRADING" sign, no Nike/Atlético/Plus500, no invented logos
- [ ] Any background text says only "voronka.tm" (or approved Russian from the batch file, spelled exactly)
- [ ] Lime #B4FF3A is the accent; no blue accent leaking in from the style reference
- [ ] Correct aspect ratio per batch file; no watermarks

One failed check = regenerate. Face drift is the #1 brand killer — when in doubt, regenerate with stronger reference weighting.
