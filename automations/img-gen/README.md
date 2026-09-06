# img-gen — voronka.tm image generator

Turns a batch spec into finished IG images: the AI draws the **character + scene**, this tool draws the **Russian text**. Text is composited deterministically, so Cyrillic never corrupts and we stop regenerating over one broken letter. Output PNGs drop straight into `../ig-poster/` for `post.py` to publish.

## Why it's split this way

Nano Banana mangles Cyrillic, especially at the sizes we use. So we never ask it to. The model gets prompts that end in *"render NO text anywhere"* and only produces the scene. Every headline, label, number and the CTA button is drawn by `generate.py` with PIL, pixel-perfect, using the exact Russian from the spec.

## One-time setup

1. **Free Gemini API key** — go to https://aistudio.google.com → get API key (no credit card, ~500 images/day free). Paste it into `../ig-poster/.env`:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Note: your Google AI **Pro subscription is not an API key** — it only raises limits inside the Gemini app. This key is separate and free.
2. **Install deps** (on The Windows machine):
   ```
   pip install -r requirements.txt
   ```
3. **(Optional) brand fonts** — drop `Manrope-Bold.ttf`, `Manrope-Medium.ttf`, `JetBrainsMono-Regular.ttf` into `fonts/`. If absent, DejaVu is used (full Cyrillic, ships with the OS). Free downloads: Manrope + JetBrains Mono on Google Fonts.

## Run

```
cd automations/img-gen

# preview the text layout with no key, no AI (flat black bases):
python generate.py --spec specs/batch-01.json --dry-run --out _preview

# full generate (AI scenes + text) into the poster folder:
python generate.py --spec specs/batch-01.json

# one image only:
python generate.py --spec specs/batch-01.json --only p1s1

# already have good bases, just redo the text:
python generate.py --spec specs/batch-01.json --overlay-only
```

Then publish as before:
```
cd ../ig-poster
python post.py --image p1s1.png p1s2.png p1s3.png p1s4.png p1s5.png p1s6.png --caption "..." --type carousel
```

## Model / cost

- Default `gemini-2.5-flash-image` (Nano Banana) — **free tier**, ~500/day.
- Set `GEMINI_MODEL=gemini-3.1-flash-image-preview` in `.env` for Nano Banana 2 (better refs/detail, ~$0.07/img, no free tier) when a hero shot needs it.
- Either way, text quality is identical — it's drawn here, not by the model.

## The spec (`specs/batch-01.json`)

One JSON per batch. Each image has:
- `ai.prompt` — scene only, character block pasted verbatim from `brand/character.md` §4, ends with "no text".
- `ai.refs` — ref-02 + ref-03 for every character image (mandatory, keeps his face consistent).
- `layers[]` — text/rect elements with normalized `xy` (0..1), `anchor` (h=l/c/r + v=t/m/b), `font` (sans_bold/sans/mono), `size`, `color` (offwhite/muted/lime/bg), optional `highlight` word rendered in lime, `max_w` for wrapping.

To add a post: copy an image block, swap the prompt + text, done. Colors and fonts come from `content-rules.md` §2 automatically.

## QC (matches content-rules.md §9 + character.md §6)

- Character face matches refs; flag patch present; no "TRADING"/other logos.
- Russian text is correct by construction (it comes from the spec) — but still eyeball wrapping/overlap on the character.
- Lime is the only accent; wordmark present; 1080×1350 (4:5); no watermarks.
- `post.py --dry-run` first if anything in the publish chain changed.
