import os
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "highlights")
DEST_DIR = os.path.join(HERE, "compressed highlights")

BG = (10, 12, 11)          # brand near-black #0A0C0B
TARGET = (1080, 1920)      # 9:16 story
FADE = 150

def fit_916(img: Image.Image) -> Image.Image:
    w, h = TARGET
    sq = img.resize((w, w), Image.Resampling.LANCZOS).convert("RGB")

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

def flatten(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        base = Image.new("RGB", img.size, BG)
        rgba = img.convert("RGBA")
        base.paste(rgba, mask=rgba.split()[3])
        return base
    return img.convert("RGB")

def compress_new():
    os.makedirs(DEST_DIR, exist_ok=True)
    all_files = sorted([f for f in os.listdir(SRC_DIR) if f.lower().endswith(".png")])
    existing_jpgs = set(os.listdir(DEST_DIR))

    new_files = []
    for f in all_files:
        jpg_name = os.path.splitext(f)[0] + ".jpg"
        if jpg_name not in existing_jpgs:
            new_files.append(f)

    if not new_files:
        print("No new highlight images to compress.")
        return

    print(f"Found {len(new_files)} new highlight image(s) to compress into '{DEST_DIR}'...")
    
    total_orig = 0
    total_new = 0
    
    for f in new_files:
        src_path = os.path.join(SRC_DIR, f)
        jpg_name = os.path.splitext(f)[0] + ".jpg"
        dest_path = os.path.join(DEST_DIR, jpg_name)
        
        orig_size = os.path.getsize(src_path)
        total_orig += orig_size
        
        with Image.open(src_path) as im:
            rgb_im = flatten(im)
            fitted = fit_916(rgb_im)
            fitted.save(dest_path, "JPEG", quality=95, optimize=True)
            
        new_size = os.path.getsize(dest_path)
        total_new += new_size
        
        reduction = (1 - new_size / orig_size) * 100
        print(f"Compressed: {f} ({orig_size/1024:.1f} KB) -> {jpg_name} ({new_size/1024:.1f} KB, -{reduction:.1f}%)")
        
    print(f"\nFinished compressing {len(new_files)} new file(s).")
    print(f"Total new size: {total_orig/(1024*1024):.2f} MB -> {total_new/(1024*1024):.2f} MB (-{(1 - total_new/total_orig)*100:.1f}%)")

if __name__ == "__main__":
    compress_new()
