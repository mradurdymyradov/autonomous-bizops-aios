#!/usr/bin/env python3
"""
generate.py — voronka.tm image generator (character scene + deterministic Russian text)

Why this exists:
  Nano Banana corrupts Cyrillic when asked to render it. So we split the job:
    1. The AI model draws ONLY the character + scene (no text) using the brand refs.
    2. This script composites every Russian word with PIL — pixel-perfect, every time.
  Result: no more regenerating because "клиент" came out "кпиент".

Chain:  spec.json  ->  [AI base scene]  ->  [PIL text overlay]  ->  pNsN.png  ->  post.py

Model:  free tier = gemini-2.5-flash-image (Nano Banana), ~500 img/day, no card.
        Set GEMINI_MODEL=gemini-3.1-flash-image-preview in .env for paid NB2 quality.
API key: put GEMINI_API_KEY=... in automations/ig-poster/.env  (get free at aistudio.google.com)

Usage:
  python generate.py --spec specs/batch-01.json                 # AI + overlay, all images
  python generate.py --spec specs/batch-01.json --only p1s1     # one image
  python generate.py --spec specs/batch-01.json --overlay-only  # skip AI, re-draw text on existing bases
  python generate.py --spec specs/batch-01.json --no-ai         # alias of --overlay-only
  python generate.py --spec specs/batch-01.json --dry-run       # build bases as flat placeholders (no key needed)

Output PNGs land in --out (default: ../ig-poster) named <id>.png, ready for post.py.
"""

import argparse, json, os, sys, io, textwrap

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.exit("Missing dependency: pip install pillow")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))            # automations/
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))     # repo root (vaios/)
ENV_PATH = os.path.join(ROOT, "automations", "ig-poster", ".env")

# ---- brand tokens (content-rules.md §2) ----
COLORS = {
    "bg":       (10, 12, 11),     # #0A0C0B near-black
    "offwhite": (241, 244, 236),  # #F1F4EC
    "muted":    (152, 162, 154),  # #98A29A
    "lime":     (180, 255, 58),   # #B4FF3A

    # ---- client palettes ----
    # Added for client-facing deliverables (reports, one-pagers) that must sit
    # in the CLIENT's brand, not voronka's grid. content-rules.md governs the
    # @voronka.tm feed; a report we hand to a client is not a feed post, and
    # showing her own numbers in our lime-on-black reads as our marketing
    # rather than her report. Additive only — the four tokens above are the
    # feed's and are untouched.
    # ng_* = ng_makeup_stylist, lifted from site/index.html's :root.
    "ng_ivory":    (247, 243, 236),  # #F7F3EC  page ground
    "ng_cream":    (239, 231, 219),  # #EFE7DB  raised panel
    "ng_sand":     (226, 214, 197),  # #E2D6C5  hairlines, empty states
    "ng_gold":     (176, 141,  87),  # #B08D57  the single accent
    "ng_espresso": ( 36,  30,  26),  # #241E1A  primary text
    "ng_taupe":    (138, 125, 112),  # #8A7D70  secondary text
}

# Brand fonts are Manrope (sans) + JetBrains Mono. If the TTFs are present in
# ./fonts they are used; otherwise we fall back to DejaVu (full Cyrillic, always
# installed). Drop Manrope-Bold.ttf / JetBrainsMono-Regular.ttf into ./fonts for
# brand-accurate type — no code change needed.
FONT_DIR = os.path.join(HERE, "fonts")
# Windows fallbacks (Segoe UI / Consolas) are listed too — all carry full
# Cyrillic. Without them this script cannot run on The machine at all.
FONT_CANDIDATES = {
    "sans_bold": ["Manrope-Bold.ttf", "Manrope-ExtraBold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"],
    "sans":      ["Manrope-Medium.ttf", "Manrope-Regular.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                  r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
    "mono":      ["JetBrainsMono-Regular.ttf", "JetBrainsMono-Medium.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                  r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf"],
}


def load_env(path=ENV_PATH):
    cfg = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def resolve_font_path(kind):
    for cand in FONT_CANDIDATES[kind]:
        p = cand if os.path.isabs(cand) else os.path.join(FONT_DIR, cand)
        if os.path.exists(p):
            return p
    raise SystemExit(f"No font found for '{kind}'. Install DejaVu or add TTFs to {FONT_DIR}")


_FONT_CACHE = {}
def font(kind, size):
    key = (kind, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(resolve_font_path(kind), size)
    return _FONT_CACHE[key]


# ---------- AI scene generation (Gemini) ----------

def generate_base(spec_img, cfg, out_size):
    """Return a PIL base image for this slide (character/scene, NO text)."""
    ai = spec_img.get("ai")
    if not ai:
        return solid_base(out_size, spec_img.get("base", "bg"))
    key = cfg.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set in ig-poster/.env — get a free key at aistudio.google.com "
                 "(or use --dry-run to build placeholder bases).")
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("Missing dependency: pip install google-genai")

    client = genai.Client(api_key=key)
    model = cfg.get("GEMINI_MODEL", "gemini-2.5-flash-image")

    parts = [ai["prompt"]]
    for rel in ai.get("refs", []):
        rp = os.path.join(ROOT, rel)
        if not os.path.exists(rp):
            sys.exit(f"Reference image missing: {rp}")
        parts.append(types.Part.from_bytes(data=shrink_ref(rp), mime_type="image/jpeg"))

    # The link here is a 2-4 Mb/s VPN that drops mid-upload (WinError 10054).
    # Retry the whole call a few times before giving up on the slide.
    last = None
    for attempt in range(1, REF_RETRIES + 1):
        try:
            resp = client.models.generate_content(model=model, contents=parts)
        except Exception as e:
            last = e
            print(f"    [{spec_img['id']}] attempt {attempt}/{REF_RETRIES} failed: "
                  f"{type(e).__name__}: {str(e)[:120]}")
            continue
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                img = Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                return fit_cover(img, out_size)
        last = RuntimeError("model returned no image part (check quota / prompt)")
        print(f"    [{spec_img['id']}] attempt {attempt}/{REF_RETRIES}: no image returned")
    sys.exit(f"[{spec_img['id']}] gave up after {REF_RETRIES} attempts: {last}")


REF_MAX_PX = 900      # vision tiles at ~768px; more bytes buy no fidelity
REF_QUALITY = 88
REF_RETRIES = 4


def shrink_ref(path):
    """Reference PNGs are ~2MB each. Downscale + JPEG them so the upload
    survives a slow VPN — the model sees the same character either way."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = min(1.0, REF_MAX_PX / max(w, h))
    if scale < 1.0:
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=REF_QUALITY)
    return buf.getvalue()


def solid_base(size, color="bg"):
    """Flat base. Defaults to the feed's near-black; a spec may name any token
    via "base". Client decks sit on a light ground, and a --dry-run preview that
    is always near-black renders their dark text invisible — which made the
    no-API-key preview useless for exactly the specs that need it most."""
    return Image.new("RGB", size, COLORS.get(color, COLORS["bg"]))


def fit_cover(img, size):
    """Crop-to-fill to exact target size (never distort, never letterbox)."""
    tw, th = size
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    img = img.resize((round(iw * scale), round(ih * scale)), Image.LANCZOS)
    iw, ih = img.size
    left, top = (iw - tw) // 2, (ih - th) // 2
    return img.crop((left, top, left + tw, top + th))


# ---------- deterministic text overlay ----------

def _wrap_to_width(text, fnt, max_px):
    if max_px is None:
        return [text]
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if fnt.getbbox(trial)[2] <= max_px or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _line_height(fnt):
    a, d = fnt.getmetrics()
    return a + d


def draw_text_layer(base, layer, W, H):
    draw = ImageDraw.Draw(base)
    fnt = font(layer.get("font", "sans_bold"), layer["size"])
    color = COLORS[layer.get("color", "offwhite")]
    hl = layer.get("highlight")
    hl_color = COLORS[layer.get("hl_color", "lime")]
    align = layer.get("align", "left")
    max_px = int(layer["max_w"] * W) if layer.get("max_w") else None
    lh = int(_line_height(fnt) * layer.get("leading", 1.12))
    lines = _wrap_to_width(layer["text"], fnt, max_px)

    block_w = max(fnt.getbbox(ln)[2] for ln in lines)
    block_h = lh * len(lines)
    ax, ay = layer["xy"]
    x0, y0 = ax * W, ay * H
    anchor = layer.get("anchor", "lt")  # l/c/r + t/m/b
    hx, vy = anchor[0], anchor[1]
    if hx == "c": x0 -= block_w / 2
    elif hx == "r": x0 -= block_w
    if vy == "m": y0 -= block_h / 2
    elif vy == "b": y0 -= block_h

    for i, ln in enumerate(lines):
        lw = fnt.getbbox(ln)[2]
        if align == "center": lx = x0 + (block_w - lw) / 2
        elif align == "right": lx = x0 + (block_w - lw)
        else: lx = x0
        ly = y0 + i * lh
        if hl and hl in ln:
            # split the line so the key word renders in lime, rest in base color
            pre, _, post = ln.partition(hl)
            cx = lx
            for seg, c in ((pre, color), (hl, hl_color), (post, color)):
                if seg:
                    draw.text((cx, ly), seg, font=fnt, fill=c)
                    cx += fnt.getbbox(seg)[2] - fnt.getbbox(seg)[0]
        else:
            draw.text((lx, ly), ln, font=fnt, fill=color)


def draw_rect_layer(base, layer, W, H):
    draw = ImageDraw.Draw(base, "RGBA")
    x, y, w, h = layer["rect"]
    box = [x * W, y * H, (x + w) * W, (y + h) * H]
    fill = layer.get("fill")
    outline = COLORS[layer["outline"]] if layer.get("outline") else None
    r = layer.get("radius", 24)
    fill_rgba = (*COLORS[fill], layer.get("fill_alpha", 255)) if fill else None
    draw.rounded_rectangle(box, radius=r, fill=fill_rgba, outline=outline,
                           width=layer.get("width", 3))
    if layer.get("label"):
        inner = dict(layer["label"])
        inner["xy"] = [x + w / 2, y + h / 2]
        inner["anchor"] = "cm"
        draw_text_layer(base, inner, W, H)


def _find_base(dir_, id_):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(dir_, id_ + ext)
        if os.path.exists(p):
            return p
    return None


def render(spec_img, cfg, out_dir, dry_run=False, overlay_only=False, bases_dir=None):
    W, H = spec_img.get("size", [1080, 1350])
    out_path = os.path.join(out_dir, f"{spec_img['id']}.png")

    if bases_dir:
        # manual flow: you generated a textless scene in Gemini web and dropped it here
        src = _find_base(bases_dir, spec_img["id"])
        if not src:
            sys.exit(f"[{spec_img['id']}] no base found in {bases_dir} "
                     f"(save your download as {spec_img['id']}.png)")
        base = fit_cover(Image.open(src).convert("RGB"), (W, H))
    elif overlay_only or (dry_run and not spec_img.get("ai")):
        base = fit_cover(Image.open(out_path).convert("RGB"), (W, H)) if os.path.exists(out_path) else solid_base((W, H), spec_img.get("base", "bg"))
    elif dry_run:
        base = solid_base((W, H), spec_img.get("base", "bg"))
    else:
        base = generate_base(spec_img, cfg, (W, H))

    base = base.convert("RGB")
    for layer in spec_img.get("layers", []):
        t = layer.get("type", "text")
        if t == "text": draw_text_layer(base, layer, W, H)
        elif t == "rect": draw_rect_layer(base, layer, W, H)
    base.save(out_path, "PNG")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", default=os.path.join(REPO, "ig-poster"))
    ap.add_argument("--only", help="render a single image id")
    ap.add_argument("--overlay-only", action="store_true", help="skip AI, redraw text on existing bases")
    ap.add_argument("--no-ai", dest="overlay_only", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="flat placeholder bases, no API key needed")
    args = ap.parse_args()

    spec_path = args.spec if os.path.isabs(args.spec) else os.path.join(HERE, args.spec)
    spec = json.load(open(spec_path, encoding="utf-8"))
    cfg = load_env()
    os.makedirs(args.out, exist_ok=True)

    imgs = spec["images"]
    if args.only:
        imgs = [i for i in imgs if i["id"] == args.only] or sys.exit(f"id {args.only} not in spec")

    for im in imgs:
        p = render(im, cfg, args.out, dry_run=args.dry_run, overlay_only=args.overlay_only)
        print(f"  OK {im['id']:6s} -> {p}")   # ASCII: Windows console is cp1251
    print(f"Done. {len(imgs)} image(s) written to {args.out}")


if __name__ == "__main__":
    main()
