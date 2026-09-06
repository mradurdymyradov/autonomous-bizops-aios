# Content Batch 04 — video demo ad (hook + LP screen recording + end card)

**For Antigravity (executor).** Execute top to bottom, no planning doc. Deliverable: one vertical video ad `automations/meta-ads/creatives/ad-v-demo.mp4`. Then show Operator and WAIT. Do not post, do not upload to Meta.

**Why:** proven local format. The market has never seen link→LP→form as a CTA; a real screen recording teaches the action inside the ad. The previous campaign with this exact structure: 12 заявок, 7 sales on $20. The video is the hero ad of test-01; statics ad-b/ad-c stay as support.

**Status: SUPERSEDED 2026-07-23.** Operator produced the video himself (Veo, 9:16 720×1280) → `automations/meta-ads/creatives/ad-video.mp4`, running as hero ad in test-01. This spec kept for the round-2 variant (hook-from-static + real LP screen recording demo — still untested).

---

## 0. Inputs

| File | What | Who provides |
|---|---|---|
| `automations/meta-ads/creatives/ad-a-pain.png` | hook source (approved) | exists |
| `automations/meta-ads/creatives/ad-c-flat.png` | end card (approved) | exists |
| `automations/meta-ads/creatives/demo-raw.mp4` | phone screen recording of the LP flow | **Operator records — WAIT until this file exists** |

## 1. The recording spec (Operator, not the agent)

Phone screen recorder, vertical, one continuous take, normal speed (~20–30s raw):
1. Open `voronkatm.com` in the phone browser (page loads fully).
2. Short scroll: hero visible → down to the phone form.
3. Tap the field, type a number (use a dummy, e.g. `65 00 00 00` — NOT your real one).
4. Tap «Получить бесплатный аудит».
5. Let the success + chatbot greeting appear. Stop.

After recording: **delete the test row it creates in the «Заявки» sheet.** Drop the file in as `demo-raw.mp4`.

## 2. Veo 3.1 hook clip (agent)

Image-to-video from `ad-a-pain.png`, **4 seconds, 9:16 if the tool allows, otherwise native and we pad**. Prompt (verbatim):

```
Animate this image with subtle motion only. All Russian text must remain exactly as in the source image — same letters, same position, sharp and unchanged at all times. The character comes alive subtly: he blinks, his smirk widens slightly, the electric lime glow pulses gently, and the camera pushes in very slowly toward him. Dark cinematic atmosphere unchanged. Do not add any new text, objects, characters, logos or camera cuts.
```

QC the clip: every Cyrillic letter sharp and unwarped through the full 4s; face stays on-model; no new elements. Warped text = regenerate. **Budget: max 3 generation attempts, then fall back to a static 4s hold of ad-a-pain.png with a slow ffmpeg zoompan — do not burn all the Veo credits on a hook.** Save as `hook.mp4`.

## 3. Assembly (agent, ffmpeg — CapCut fallback is The call)

Canvas 1080×1920, 30fps. Statics get padded onto brand black `#0A0C0B` (fit width, never crop).

1. `hook.mp4` → scale/pad to 1080×1920, trim to 4.0s.
2. `demo-raw.mp4` → speed **1.5×**, scale/pad to 1080×1920, trim so the segment runs ~8–10s and ends right after the chatbot greeting appears.
3. `ad-c-flat.png` → 2.5s hold, padded.
4. Concatenate 1→2→3 with 0.2s crossfades. No music (feed autoplays muted; the demo is self-explanatory). Keep any natural silence — do NOT add a soundtrack without Operator.
5. Output `automations/meta-ads/creatives/ad-v-demo.mp4`, H.264, ≤60MB, total length ~15–16s.

## 4. QC gate (one fail = fix and re-render)

- [ ] Hook text letter-exact and stable; character on-model (character.md §6 on a frame grab).
- [ ] Demo legible: URL bar shows voronkatm.com, the typed number and the «Получить бесплатный аудит» tap clearly visible at 1.5×.
- [ ] Dummy phone number in the demo, not a real one.
- [ ] End card sharp, text exact.
- [ ] 1080×1920, ~15s, plays start to finish, no black frames at the joins.

## 5. Hand-back

Show Operator the mp4. WAIT. Approved → done; The browser agent adds it to the campaign per `automations/meta-ads/campaign-setup-test-01.md` (ad name `ad-v-demo`, hero ad).
