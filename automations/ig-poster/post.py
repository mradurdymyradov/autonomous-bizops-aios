#!/usr/bin/env python3
"""
post.py — Instagram poster for @voronka.tm

Chain: local image -> imgbb (public URL) -> Graph API media container -> publish.
Config lives in ig-poster/.env. Handles feed + stories, single + carousel.
Built for a flaky 2-4 Mb/s VPN: every network call retries with backoff.

Usage:
  python post.py --image path/to/pic.jpg --caption "Hello world"
  python post.py --image a.jpg --caption "..." --type stories
  python post.py --image a.jpg b.jpg c.jpg --caption "..." --type carousel
  python post.py --folder outbox                 # post oldest image(s) in a folder
  python post.py --folder outbox --type stories  # scheduled/story use

Caption sources (in priority order):
  1) --caption "text"
  2) a .txt file next to the image with the same stem (pic.jpg -> pic.txt)
  3) empty caption

After a successful publish, source files are moved to ig-poster/posted/.
"""

import argparse
import os
import sys
import time
import glob
import shutil
import mimetypes
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
POSTED_DIR = os.path.join(HERE, "posted")
LOG_PATH = os.path.join(HERE, "post.log")

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


# ---------- config ----------

def load_env(path=ENV_PATH):
    """Minimal .env parser (no external dep)."""
    cfg = {}
    if not os.path.exists(path):
        sys.exit(f"No .env found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


CFG = load_env()
GRAPH = f"https://graph.facebook.com/{CFG.get('GRAPH_VERSION', 'v21.0')}"
IG_USER_ID = CFG.get("IG_USER_ID")
TOKEN = CFG.get("IG_ACCESS_TOKEN")
IMGBB_KEY = CFG.get("IMGBB_API_KEY")


def log(msg):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        # Fallback for Windows consoles that do not support certain characters (like emojis)
        try:
            print(line.encode(sys.stdout.encoding or 'ascii', errors='replace').decode(sys.stdout.encoding or 'ascii'))
        except Exception:
            pass
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ---------- resilient HTTP ----------

def request(method, url, retries=5, backoff=3, **kwargs):
    """HTTP with retry/backoff for a dropping VPN. Raises on final failure."""
    kwargs.setdefault("timeout", 120)
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(f"{r.status_code}: {r.text[:300]}")
            return r
        except (requests.RequestException, requests.HTTPError) as e:
            last = e
            if attempt < retries:
                wait = backoff * attempt
                log(f"  net retry {attempt}/{retries} in {wait}s ({e})")
                time.sleep(wait)
    raise SystemExit(f"Network failed after {retries} tries: {last}")


# ---------- steps ----------

def upload_to_imgbb(image_path):
    if not IMGBB_KEY:
        sys.exit("IMGBB_API_KEY is empty in .env. Get a free key at https://api.imgbb.com")
    log(f"Uploading to imgbb: {os.path.basename(image_path)}")
    mime = mimetypes.guess_type(image_path)[0] or "image/png"
    with open(image_path, "rb") as f:
        content = f.read()
    r = request(
        "POST",
        "https://api.imgbb.com/1/upload",
        params={"key": IMGBB_KEY},
        files={"image": (os.path.basename(image_path), content, mime)},
    )
    data = r.json()
    if not data.get("success"):
        sys.exit(f"imgbb upload failed: {data}")
    url = data["data"]["url"]
    log(f"  -> {url}")
    return url


def create_container(image_url, caption, media_type, is_carousel_item=False):
    payload = {"image_url": image_url, "access_token": TOKEN}
    if is_carousel_item:
        payload["is_carousel_item"] = "true"
    else:
        if media_type == "stories":
            payload["media_type"] = "STORIES"
        if caption:
            payload["caption"] = caption
    r = request("POST", f"{GRAPH}/{IG_USER_ID}/media", data=payload)
    data = r.json()
    if "id" not in data:
        sys.exit(f"Container create failed: {data}")
    return data["id"]


def create_carousel_container(child_ids, caption):
    payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "access_token": TOKEN,
    }
    if caption:
        payload["caption"] = caption
    r = request("POST", f"{GRAPH}/{IG_USER_ID}/media", data=payload)
    data = r.json()
    if "id" not in data:
        sys.exit(f"Carousel container failed: {data}")
    return data["id"]


def wait_ready(container_id, tries=20, delay=4):
    """Poll container status until FINISHED before publishing."""
    for _ in range(tries):
        r = request("GET", f"{GRAPH}/{container_id}",
                    params={"fields": "status_code", "access_token": TOKEN})
        status = r.json().get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            sys.exit(f"Container {container_id} processing ERROR")
        time.sleep(delay)
    log("  container not FINISHED yet, publishing anyway")
    return False


def publish(container_id):
    r = request("POST", f"{GRAPH}/{IG_USER_ID}/media_publish",
                data={"creation_id": container_id, "access_token": TOKEN})
    data = r.json()
    if "id" not in data:
        sys.exit(f"Publish failed: {data}")
    return data["id"]


# ---------- caption / files ----------

def resolve_caption(images, caption_arg):
    if caption_arg is not None:
        return caption_arg
    stem = os.path.splitext(images[0])[0]
    txt = stem + ".txt"
    if os.path.exists(txt):
        with open(txt, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def folder_images(folder):
    files = [p for p in sorted(glob.glob(os.path.join(folder, "*")))
             if p.lower().endswith(IMAGE_EXTS)]
    return files


def move_posted(paths):
    os.makedirs(POSTED_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for p in paths:
        base = os.path.basename(p)
        dest = os.path.join(POSTED_DIR, f"{ts}_{base}")
        try:
            shutil.move(p, dest)
        except OSError as e:
            log(f"  could not move {base}: {e}")
        # also move sidecar .txt
        txt = os.path.splitext(p)[0] + ".txt"
        if os.path.exists(txt):
            try:
                shutil.move(txt, os.path.join(POSTED_DIR, f"{ts}_{os.path.basename(txt)}"))
            except OSError:
                pass


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Post images to Instagram @voronka.tm")
    ap.add_argument("--image", nargs="+", help="one or more image paths")
    ap.add_argument("--folder", help="post image(s) from this folder (oldest first)")
    ap.add_argument("--caption", help="caption text (overrides sidecar .txt)")
    ap.add_argument("--type", choices=["feed", "stories", "carousel"], default="feed")
    ap.add_argument("--dry-run", action="store_true", help="upload only, do not publish")
    args = ap.parse_args()

    if not IG_USER_ID or not TOKEN:
        sys.exit("IG_USER_ID or IG_ACCESS_TOKEN missing in .env")

    # collect images
    if args.image:
        images = args.image
    elif args.folder:
        images = folder_images(args.folder)
        if not images:
            log(f"No images in {args.folder}. Nothing to post.")
            return
        # feed/stories = single post of the oldest; carousel = all
        if args.type != "carousel":
            images = images[:1]
    else:
        sys.exit("Provide --image or --folder")

    for p in images:
        if not os.path.exists(p):
            sys.exit(f"Image not found: {p}")

    caption = resolve_caption(images, args.caption)
    log(f"Posting {len(images)} image(s) as {args.type}. Caption: {caption[:60]!r}")

    if args.type == "carousel" and len(images) > 1:
        child_ids = []
        for p in images:
            url = upload_to_imgbb(p)
            cid = create_container(url, "", "feed", is_carousel_item=True)
            child_ids.append(cid)
        container = create_carousel_container(child_ids, caption)
    else:
        url = upload_to_imgbb(images[0])
        container = create_container(url, caption, args.type)

    if args.dry_run:
        log(f"DRY RUN — container {container} created, not publishing.")
        return

    wait_ready(container)
    post_id = publish(container)
    log(f"PUBLISHED SUCCESS  media id: {post_id}")
    move_posted(images)
    log("Source file(s) moved to posted/.")


if __name__ == "__main__":
    main()
