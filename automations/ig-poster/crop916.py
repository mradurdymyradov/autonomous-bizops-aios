"""crop916.py — turn square (1:1) generated images into 9:16 story images.

Why: the image generator only outputs 1:1. Two ways to get to 9:16:

--fit  (DEFAULT, use this)  scale the whole square to 1080 wide and extend its
       top and bottom edge rows to fill out 1920 tall. Nothing is ever cut, so
       composition stops mattering and no image can fail. The extended bands are
       the same near-black as the design, so the join is invisible, and the
       content lands exactly in Instagram's story safe zone (IG covers the top
       and bottom of a story with its own UI anyway).

--crop (legacy)  center-crop the middle 9:16 of the square. Needs the generator
       to keep all content inside the middle half of the width. It will not do
       that reliably: told to break a headline into more lines, it just draws
       each line bigger and fills the same width (measured 2026-07-21 across two
       full runs — v4 came in at 59%/67%/50% of width against a 56% window).
       Kept for images deliberately composed narrow. Run --check first.

Usage (from automations/ig-poster/):
    python crop916.py --folder highlights           # fit every .png (default)
    python crop916.py h1s1.png h1s2.png             # specific files
    python crop916.py --folder highlights --crop --check   # legacy dry check

--check (crop mode only) rejects three defects (see brand/content-rules.md §8):
  1. content crossing the 9:16 crop line
  2. content clearing it by less than MIN_CLEARANCE px (passing by a hair is
     luck, not margin)
  3. vertical seams inside the crop window - the generator draws words like
     "column"/"band"/"panel" as a real rectangle whose background-toned edges
     survive the crop as visible stripes. Added 2026-07-21 after a story run
     shipped two stripes down the middle and check 1 alone said "ok".

Output: <same-name>.jpg next to each source (h1s1.png -> h1s1.jpg), quality 95,
transparency flattened to brand near-black #0A0C0B. Sources are never modified.
Post the .jpg files. Covers (c*.png) stay square — do NOT run them through this.
"""

import argparse
import os
import sys

try:
    from PIL import Image, ImageFilter
except ImportError:
    import subprocess
    print("Pillow not found, installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageFilter

BG = (10, 12, 11)          # brand near-black #0A0C0B
TARGET = (1080, 1920)      # 9:16 story
# a pixel is "content" if it differs from near-black background more than this
CONTENT_TOLERANCE = 28
# adjacent-column background jump that means a rectangle edge was drawn.
# Measured 2026-07-21: real seams scored 16-24, image noise stayed under 5.
SEAM_TOLERANCE = 8
# bright content must clear each crop line by at least this much; passing by a
# few px is luck, not margin (h1s4 cleared by 12 and still looked cramped).
MIN_CLEARANCE = 30
# px over which the square's top and bottom fade out into the dark bands
FADE = 150


def flatten(img: Image.Image) -> Image.Image:
    """Remove alpha onto brand background; return RGB."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        base = Image.new("RGB", img.size, BG)
        rgba = img.convert("RGBA")
        base.paste(rgba, mask=rgba.split()[3])
        return base
    return img.convert("RGB")


def crop_box_916(w: int, h: int):
    """Centered 9:16 box inside w x h."""
    target_w = h * 9 / 16
    if target_w <= w:
        left = round((w - target_w) / 2)
        return (left, 0, left + round(target_w), h)
    # image already narrower than 9:16 -> crop top/bottom instead
    target_h = w * 16 / 9
    top = round((h - target_h) / 2)
    return (0, top, w, top + round(target_h))


def content_touches_edges(img: Image.Image, box) -> bool:
    """True if non-background pixels sit on the left/right crop lines."""
    left, top, right, bottom = box
    px = img.load()
    for x in (left, right - 1):
        if x < 0 or x >= img.width:
            continue
        for y in range(top, bottom, 4):
            r, g, b = px[x, y][:3]
            if abs(r - BG[0]) + abs(g - BG[1]) + abs(b - BG[2]) > CONTENT_TOLERANCE:
                return True
    return False


def content_clearance(img: Image.Image, box):
    """Px of empty space between the outermost bright content and each crop line.

    Negative = content already past the line. Uses a brighter threshold than
    content_touches_edges so faint background tinting doesn't count as content.
    """
    left, top, right, bottom = box
    px = img.load()
    lo, hi = None, None
    for x in range(img.width):
        for y in range(0, img.height, 4):
            if max(px[x, y][:3]) > 90:
                if lo is None:
                    lo = x
                hi = x
                break
    if lo is None:
        return None, None
    return lo - left, (right - 1) - hi


def find_seams(img: Image.Image):
    """X positions where background tone jumps between adjacent columns.

    The generator renders words like "column"/"band"/"panel" as a real drawn
    rectangle. Its edges are background-toned, so content_touches_edges never
    sees them — but they survive the crop as visible vertical stripes. We look
    in the top and bottom strips, which every story prompt keeps empty.
    """
    w, h = img.size
    px = img.load()
    def strip_seams(rows):
        prof = []
        for x in range(w):
            s = 0
            for y in rows:
                r, g, b = px[x, y][:3]
                s += r + g + b
            prof.append(s / (len(rows) * 3.0))
        found, run = [], False
        for x in range(1, w):
            jump = abs(prof[x] - prof[x - 1]) > SEAM_TOLERANCE
            if jump and not run:
                found.append(x)
            run = jump
        return found

    top = strip_seams(range(int(h * 0.02), int(h * 0.12)))
    bottom = strip_seams(range(int(h * 0.88), int(h * 0.98)))

    # A drawn container runs the full height, so its edge shows up in BOTH
    # strips. Requiring both keeps character shoulders and props (which only
    # touch the bottom strip) from raising false alarms.
    return [x for x in top if any(abs(x - b) <= 4 for b in bottom)]


def fit_916(img: Image.Image) -> Image.Image:
    """Keep the 1:1 design intact, fade its top and bottom into the dark, and
    centre it in a 9:16 story canvas.

    Nothing is ever cropped, so composition cannot fail. The square's top and
    bottom edges fade to brand black over FADE px, so there is no hard line
    where the design stops — it just dissolves into the dark bands, which sit
    exactly where Instagram lays its own dark chrome (username top, reply box
    bottom). Reads as one continuous dark story, not a pasted-in square.
    """
    w, h = TARGET
    sq = img.resize((w, w), Image.Resampling.LANCZOS).convert("RGB")

    # vertical alpha ramp: transparent at the square's very edge -> opaque
    mask = Image.new("L", (w, w), 255)
    mpx = mask.load()
    for y in range(FADE):
        v = int(255 * (y / FADE))
        for x in range(w):
            mpx[x, y] = v
            mpx[x, w - 1 - y] = v

    out = Image.new("RGB", (w, h), BG)
    out.paste(sq, (0, (h - w) // 2), mask)
    return out


def process(path: str, check_only: bool, mode: str) -> bool:
    """Returns True on success/clean, False if content would be cut."""
    with Image.open(path) as im:
        img = flatten(im)
    name = os.path.basename(path)

    if mode == "fit":
        out_path = os.path.splitext(path)[0] + ".jpg"
        if check_only:
            print(f"ok       {name}: fit mode never cuts content, nothing to check.")
            return True
        fit_916(img).save(out_path, "JPEG", quality=95)
        print(f"fitted   {name} -> {os.path.basename(out_path)}  "
              f"{TARGET[0]}x{TARGET[1]}")
        return True

    box = crop_box_916(*img.size)
    left, _, right, _ = box
    clipped = content_touches_edges(img, box)
    cl, cr = content_clearance(img, box)
    seams = [x for x in find_seams(img) if left <= x < right]

    if clipped:
        print(f"WARNING  {name}: content touches the 9:16 crop line — REGENERATE "
              f"with more empty dark space left and right and shorter headline "
              f"lines. Not safe to crop.")
    elif cl is not None and min(cl, cr) < MIN_CLEARANCE:
        print(f"WARNING  {name}: content clears the crop line by only "
              f"{min(cl, cr)}px (want {MIN_CLEARANCE}+). Too tight — regenerate "
              f"with shorter headline lines.")
        clipped = True
    if seams:
        print(f"WARNING  {name}: vertical seam(s) at x={seams} inside the crop "
              f"window — the generator drew a container rectangle. These become "
              f"visible stripes in the story. REGENERATE: never name a 'column', "
              f"'band', 'strip' or 'panel' in the prompt.")
        clipped = True

    if check_only:
        if not clipped:
            print(f"ok       {name}: crop clean, clearance {cl}/{cr}px, no seams.")
        return not clipped

    out = img.crop(box).resize(TARGET, Image.Resampling.LANCZOS)
    out_path = os.path.splitext(path)[0] + ".jpg"
    out.save(out_path, "JPEG", quality=95)
    status = "CROPPED (with warning!)" if clipped else "cropped"
    print(f"{status}  {name} -> {os.path.basename(out_path)}  {TARGET[0]}x{TARGET[1]}")
    return not clipped


def main():
    ap = argparse.ArgumentParser(description="Turn 1:1 images into 9:16 stories (1080x1920 jpg).")
    ap.add_argument("images", nargs="*", help="image file(s)")
    ap.add_argument("--folder", help="process every .png in this folder")
    ap.add_argument("--check", action="store_true", help="check only, write nothing")
    ap.add_argument("--crop", dest="mode", action="store_const", const="crop",
                    default="fit",
                    help="legacy: center-crop instead of fitting (can cut content)")
    args = ap.parse_args()

    paths = list(args.images)
    if args.folder:
        paths += sorted(
            os.path.join(args.folder, f)
            for f in os.listdir(args.folder)
            if f.lower().endswith(".png")
        )
    if not paths:
        ap.error("give image files or --folder")

    ok = True
    for p in paths:
        if not os.path.exists(p):
            print(f"missing  {p}")
            ok = False
            continue
        ok = process(p, args.check, args.mode) and ok

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
