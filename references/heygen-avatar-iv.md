# HeyGen Avatar IV — how to drive it properly

Researched 2026-08-23 against HeyGen's own docs, then **measured on our account**. Where the two
disagree, the measurement wins and is marked ⚠️.

Access is **OAuth/MCP only** — the API key bills a $0.00 wallet and 402s on every generate. See
[automations/CAPABILITIES.md](../automations/CAPABILITIES.md) §B3.

---

## 1. You do not need to create an avatar

The biggest time-waster. `create_video_from_image` animates **any uploaded image** directly — no
avatar, no group, no look, no training wait. This mirrors what the web UI does when you drop a photo
into Avatar IV.

| Tool | Use when |
|---|---|
| `create_video_from_image` | One-off, or the character's framing/pose changes per clip. **Default choice.** |
| `create_video_from_avatar` | You'll reuse one identical look across many clips and want it in the dashboard library |

Upload is three calls: `create_asset_upload` → `PUT` the bytes to the returned presigned URL (send
the `x-amz-server-side-encryption: AES256` header) → `complete_asset_upload`. Then pass
`{"type": "asset_id", "asset_id": "..."}`.

## 2. What Avatar IV is good at

It analyses vocal tone, rhythm and emotion to drive facial movement — head tilts, pauses, cadence,
micro-expressions. HeyGen states it is **the best engine for cartoonish, animated, or non-human
subjects** (3D models, illustrated characters, animals), which is exactly our case.

Avatar V is the sibling engine: better realism and smoother hands, and it exposes Expression /
Gesture / Gaze presets in the UI. It rejects `expressiveness`.

## 3. Motion prompts

**Formula:** `[Body part] + [Action] + [Emotion or intensity]`

> "Right arm raises in a wave, enthusiastic and friendly."

Rules that actually matter:

- **One gesture per prompt.** You may pair it with one facial expression. Two short clauses is the ceiling.
- **Concrete, not abstract.** ✅ "rapidly typing lines of code" ❌ "attempting to bypass security"
- **Describe, don't converse.** ✅ "a cat walking away from her kittens" ❌ "can you make me a video about…"
- **Never phrase negatively.** ✅ "Fixed camera. The shot stays steady." ❌ "No motion. The scene remains unchanged."
- **Don't restate the image.** It already sees the outfit, the room, the pose.
- **Don't fight the source pose.** Our `ref-02` has both hands behind his head — asking for a hand
  gesture there produces artifacts. Head and expression only.
- **Non-deterministic.** Small wording changes swing the result. Re-roll rather than over-engineer.

**You cannot control:** camera movement, scene or location changes, props, walking, background, lighting.

**Length:** HeyGen recommends custom motion for clips **under 10s**, and default motion for longer
scenes, intercutting custom gestures for pacing. Our Reels run 25s, so default motion is the safer
baseline — see §5.

## 4. Credits

Documented rates:

| Path | Rate |
|---|---|
| Photo look avatar | 16 credits / minute |
| Video look avatar | 31 credits / minute |
| Photo-to-video **with custom motion** | 2:1 ratio (30s → 20 credits) |

⚠️ **The 2:1 custom-motion surcharge did not apply on our account.** Measured 2026-08-23 via
`create_video_from_image`: a 25.2s clip with no motion prompt and a 24.5s clip with one both cost
**8 credits** — 16 for the pair, exactly the 16 cr/min photo rate. Budget at **~8 credits per 25–30s
Reel** and treat motion prompts as free until a bill says otherwise.

Credits **reset**, they do not roll over. `get_current_user` → `subscription.credits.premium_credits.resets_at`
is the real deadline.

## 5. Our working config

```
aspectRatio  9:16
resolution   720p
fit          cover        # source is portrait; centred subject survives the side crop
expressiveness medium     # Avatar IV only — rejected on avatar_v
caption      {"file_format": "srt"}   # sidecar, so captions get styled to match the grid
```

`caption.style` burns captions into the render instead; the sidecar still ships either way.

Render time is roughly 1.5–5 minutes for a 25s clip. Poll `get_video` — `bulk_video_statuses`
mangles a JSON array into two malformed ids, so just call `get_video` per video.

## 6. Source-image prep for our character

HeyGen publishes no resolution or framing spec — support says ask them. What we established:

- `ref-02` at its native 1086×1448 is the best source: canonical wardrobe, flag patch visible,
  front-facing, and ~4× the pixels of any crop off the `ref-03` sheet.
- **The "TRADING" neon must be painted out first** (`brand/character.md` §1 forbids reproducing it).
  Detect it as bright-blue pixels in the top-right, then patch with a mirrored, blurred strip of the
  wall below it and feather the seam — the background is out of focus, so it is invisible.
- `ref-01` is unusable at any size: Atlético crest, Nike swoosh and "Plus500" on the jacket, all
  forbidden, and no flag patch.

## Sources

- [Fine-Tune Avatar Gestures with Custom Motion Prompts (Avatar IV & V)](https://help.heygen.com/en/articles/12805098-fine-tune-avatar-gestures-and-movements-with-custom-motion-prompts-avatar-iv-v)
- [HeyGen Avatar IV Complete Guide](https://help.heygen.com/en/articles/11269603-heygen-avatar-iv-complete-guide)
- [Prompting best practices for adding Motion](https://community.heygen.com/public/resources/prompting-best-practices-for-adding-motion)
- [Avatar & Voice FAQ: Troubleshooting, Best Practices, and Credits](https://help.heygen.com/en/articles/15544929-avatar-voice-faq-troubleshooting-best-practices-and-credits)
