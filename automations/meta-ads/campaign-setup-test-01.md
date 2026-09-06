# Campaign setup — test-01 ($23–25 traffic test), browser-agent plan

**For the browser agent.** This file IS the plan — execute top to bottom in Meta Ads Manager (adsmanager.facebook.com) in The browser session. He is already logged in; the master ad account is ACTIVE with a card on file.

**HARD STOP RULE: build everything, but DO NOT PUBLISH.** Finish with the campaign in draft (or every ad toggled OFF/paused), screenshot the full review screen, show Operator, and WAIT. Operator presses Publish himself. Never confirm any spend-related dialog on your own.

Other hard rules:
- Copy every Russian string below EXACTLY, letter by letter. Never rewrite, never translate.
- If the UI differs from a step (Meta ships new UIs constantly), match the intent of the step, note the deviation in your final report. If you can't find a setting at all, skip it, flag it, continue — don't stall the whole build.
- If any Advantage+ / AI toggle isn't explicitly listed as ON below → turn it OFF.
- Don't touch anything outside this campaign. No edits to the pixel, page, payment settings, or existing assets.

---

## 0. Assets you'll use

| Asset | Value |
|---|---|
| Ad account | the master account (only active one) |
| Facebook Page | the voronka page |
| Instagram account | @voronka.tm |
| Pixel / dataset | `1397681815558353` («voronka dataset») |
| Destination URL | `https://voronkatm.com` |
| Creatives (local files) | `D:\ai projects\vaios\automations\meta-ads\creatives\ad-video.mp4` (9:16, 720×1280), `ad-b-proof.png`, `ad-c-flat.png` (1:1). `ad-a-pain.png` is NOT in this campaign — its hook is inside the video. |

## 0-bis. PREREQUISITE — do not build until this passes

The LP must fire a **Lead** pixel event on phone submit (Operator adds `fbq('track','Lead')` in the LP's submit handler and deploys). Verify before building: Events Manager → dataset `1397681815558353` → the **Lead** event exists with recent activity. **If there is no Lead event, STOP and report to Operator — the campaign cannot optimize without it.**

## 1. Campaign

1. Ads Manager → Create.
2. Objective: **Leads**. If offered "tailored" vs "manual" setup → **manual**.
3. Campaign name: `voronka-test-01`
4. Buying type: Auction. Special ad categories: **none**.
5. Advantage+ campaign budget: **OFF** (budget will be set on the ad set).
6. Campaign spending limit (if the field exists at campaign level): **$25**. If not available here, set the account-independent alternative in step 2.7.

## 2. Ad set (one only)

1. Ad set name: `ahal-broad-ig`
2. Conversion location: **Website**.
3. Performance goal: **Maximize number of conversions**. Dataset: `1397681815558353`. Conversion event: **Lead** (per prerequisite 0-bis).
4. Budget: **Daily, $6.00**.
5. Schedule: start **now**; end date **4 days from start** (this caps total spend ≈ $24 even if the limit field in 1.6 didn't exist).
6. Audience: if an "Advantage+ audience" panel appears → switch to **original/manual audience options**.
   - Location: search **"Ahal"** → select **Ahal Region, Turkmenistan** (region, people living in). If the region is not selectable in the UI, do NOT substitute anything — flag it in the hand-back and leave location on Turkmenistan.
   - Age: **23–43**. Gender: all. Languages: leave all/default.
   - Detailed targeting: **empty** — fully broad, add nothing.
7. Placements: **Manual placements** (turn Advantage+ placements OFF).
   - Devices: all. Platforms: **Instagram ONLY** (uncheck Facebook, Messenger, Audience Network).
   - Under Instagram keep: **Instagram feed**, **Instagram profile feed**, **Explore** (+ Explore home if listed), **Instagram Stories**, **Instagram Reels**. Uncheck anything else.

## 3. Ads (three, identical settings except creative + name)

| Ad name | Creative | Format |
|---|---|---|
| `ad-video` | `ad-video.mp4` | video 9:16, 720×1280 — the hero ad |
| `ad-b-proof` | `ad-b-proof.png` | image 1:1 |
| `ad-c-flat` | `ad-c-flat.png` | image 1:1 |

Upload originals as-is. Decline any optional crops/extensions Meta offers (1:1 statics will letterbox in Stories/Reels — acceptable, the video covers vertical; never let Meta auto-crop or AI-expand the video). Video thumbnail: first frame (the hook), not an auto-picked mid-video frame, if the option exists.

Shared settings on all three:

1. Identity: Facebook Page = voronka page, Instagram account = **@voronka.tm**.
2. Format: single image.
3. **Advantage+ creative / creative enhancements: ALL OFF** (music, 3D motion, image touch-ups, text improvements, relevant comments — every toggle off). This is critical — enhancements mangle the creative.
4. Primary text (exact):
   «Инстаграм есть, а клиентов нет? Мы настраиваем систему, которая приводит заявки: таргет-реклама → сайт → Telegram-бот → CRM-таблица. Запишитесь на бесплатный аудит — за 10 минут покажем, где ваша реклама теряет клиентов.»
5. Headline (exact): «Бесплатный аудит вашей рекламы»
6. Description: leave empty.
7. Call to action: **Подробнее** (Learn More).
8. Website URL: `https://voronkatm.com`
9. URL parameters (one line, in the dedicated URL-parameters field):
   `utm_source=ig&utm_medium=paid&utm_campaign=test01&utm_content={{ad.name}}`
   If dynamic `{{ad.name}}` is rejected, hardcode per ad: `utm_content=ad-a-pain` etc.
10. Pixel tracking: website events → dataset `1397681815558353` checked.

## 4. Final check before handing back (QC gate)

- [ ] 1 campaign / 1 ad set / 3 ads, names exactly as specified.
- [ ] Objective Leads, performance goal maximize conversions, event **Lead**, dataset selected.
- [ ] $6/day + 4-day end date (and $25 limit if the field existed).
- [ ] Ahal Region only, age 23–43, no detailed targeting.
- [ ] Instagram-only placements, no Stories/Reels.
- [ ] All 3 creatives correct (open each preview — right file on right ad name; video plays with sound in preview).
- [ ] Russian copy letter-exact on all 3. CTA «Подробнее». URL + UTMs on all 3.
- [ ] Every creative-enhancement toggle OFF on all 3 (especially any video enhancement/upscaling on ad-video).
- [ ] **NOTHING PUBLISHED.** Campaign in draft / ads paused.

## 5. Hand-back

Screenshot: campaign review screen + one ad preview per ad (feed placement). Report any step where the UI forced a deviation. Then WAIT for Operator — he publishes.

## After launch (Operator, not the agent)

- Don't touch for 72h. No edits — edits reset learning. Expect the ad set to stay "learning limited" — normal on this budget, ignore the warning.
- Day 3–4: cost per Lead in Ads Manager cross-checked against real заявки in the Telegram bot / Sheet (the Sheet is truth, Ads Manager can over/undercount). Winner = cheapest real заявка.
- Log results in `funnel/02-meta-ad.md`. Winning static → Veo 3.1 image-to-video for round 2.
