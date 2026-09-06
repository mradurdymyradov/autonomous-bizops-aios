---
name: ig-post
description: >
  Post images to Instagram @voronka.tm from plain language. Use whenever Operator
  says things like "post this pic with caption X", "put these in my stories",
  "post a carousel of these", or asks to schedule daily story/feed posts.
  Handles feed posts, stories, and carousels. Runs the local tool ig-poster/post.py.
---

# Instagram poster — @voronka.tm

Publishes to Instagram via the Meta Graph API. The tool lives in
`automations/ig-poster/`; run everything from that directory. The Meta app and a
permanent (non-expiring) Page token are already configured in its `.env`. Images
are uploaded to imgbb to get a public URL, then published through the Graph API
in two steps (create container → publish).

## IMPORTANT: where this runs
The tool must run on **The Windows machine** (D:\), NOT in an agent sandbox.
Sandboxes cannot reach `graph.facebook.com` / `api.imgbb.com`. Only The VPN
connection can. So run `post.py` via his local Python / terminal / Task Scheduler.

## Prerequisites (one-time)
- Python 3 with `requests` (`pip install -r requirements.txt`).
- `automations/ig-poster/.env` filled in: `IG_USER_ID`, `IG_ACCESS_TOKEN`,
  `GRAPH_VERSION`, `IMGBB_API_KEY`. Already done — don't re-run setup.

## How to run

Feed post, explicit caption:
```
python post.py --image "C:\path\pic.jpg" --caption "Your caption here"
```

Story:
```
python post.py --image "C:\path\pic.jpg" --type stories
```

Carousel (multiple images, one caption):
```
python post.py --image a.jpg b.jpg c.jpg --caption "..." --type carousel
```

Post from a watched folder (oldest file first — good for scheduling):
```
python post.py --folder outbox               # feed
python post.py --folder outbox --type stories
```

Test without publishing (uploads to imgbb, creates container, stops):
```
python post.py --image pic.jpg --caption "test" --dry-run
```

## Captions
Caption is taken from, in order: `--caption` → a sidecar `.txt` with the same
name as the image (`pic.jpg` → `pic.txt`) → empty. Sidecar `.txt` is the clean
way to queue posts in a folder.

## What happens on success
Published media id is logged to `post.log`, and the source image (+ its `.txt`)
is moved into `posted/` with a timestamp so it isn't posted twice. Log the media
id in `decisions/log.md` when a batch ships.

## Queue workflow (for scheduling)
1. Drop images (and optional matching `.txt` captions) into `outbox/`.
2. A scheduled run of `python post.py --folder outbox --type stories` posts the
   oldest one and moves it to `posted/`.
3. Empty folder = the run logs "nothing to post" and exits cleanly.

## Scheduling on Windows (daily 8am stories)
Use Windows Task Scheduler → Create Basic Task → Daily 8:00 →
Action: Start a program → `python` with arguments
`"D:\ai projects\vaios\automations\ig-poster\post.py" --folder outbox --type stories`
and "Start in" = `D:\ai projects\vaios\automations\ig-poster`.

## Constraints & Best Practices

- **VPN is required:** Meta Graph API and imgbb are blocked in Turkmenistan. The VPN must be turned ON before posting, or the script will raise `WinError 10061` (Connection refused).
- **Image Compression for Slow Networks:** The VPN connection is slow (2-4 Mb/s) and unstable. Uploading raw PNG files (especially 2K carousels) causes timeouts. **Always compress images to optimized JPEG format (quality=85) before posting.**
  * *Pillow snippet to compress:*
    ```python
    from PIL import Image
    with Image.open("img.png") as im:
        im.convert("RGB").save("img.jpg", "JPEG", quality=85, optimize=True)
    ```
- **Windows Console Encoding:** Emojis (like `✅`) can crash Russian Windows terminals (`cp1251`). Keep stdout output free of complex emojis or handle `UnicodeEncodeError` in logs.
- **Rate limit:** 100 posts / 24h (irrelevant at current volume).
- **Security:** Never commit `.env` (it holds the permanent token). It is git-ignored.
- **Tone:** This is infra, not brand voice. Caption text still follows `funnel/00-core.md` when the caption is client-facing.
