# 03 — Landing page (voronkatm.com)

**Stage:** the conversion page — turns a cold ad click into a captured phone + booked audit. Must match [00-core.md](00-core.md).

**Status: v3 LIVE (2026-07-16, tag `v3-live`).** Full «живая витрина» redesign shipped to production; smoke lead verified end-to-end same day (Telegram + Sheet, attempt 1). v1's template look was rejected as "AI slop", v2 (minimal editorial) rejected same-day for feel — v3 is the cinematic premium rebuild. **Verbatim copy source of truth is `D:\ai projects\voronka\site\index.html`** — this file describes structure + key lines; the page is the spec.

---

## What it is

Single-page Russian static site. Mobile-first for cheap Androids on slow TKM data. Agency «мы» voice, 100% Russian UI. One job: cold visitor → understands the offer → leaves phone → chatbot follows up → we call and close. **Sells only the free audit call, never the price.**

- **Live:** https://voronkatm.com (primary, custom domain bought 2026-07-22). Underlying Cloudflare Pages URL https://voronka.pages.dev still serves the same project (`voronka`) as fallback — send all ads/IG/outreach to voronkatm.com.
- **Real source of truth:** `D:\ai projects\voronka\` (The desktop, not in git). Deploy only from there.
- **Read-only snapshot:** old workspace `reference/voronka-lp/site/`.

## SEO / meta / social

- **`<title>`:** «voronka.tm — реклама в Instagram, которая приводит клиентов»
- **Meta description:** «Настроим таргетированную рекламу в Instagram, сделаем сайт с заявкой и подключим Telegram-бота — заявки от клиентов приходят вам прямо в телефон. Бесплатный аудит для бизнеса в Туркменистане.»
- **OG / Twitter title:** «Больше клиентов из Instagram — на автомате»
- **OG / Twitter description:** «Реклама + сайт с заявкой + Telegram-бот. Заявки приходят вам в телефон. Бесплатный аудит для бизнеса в Туркменистане.»
- **OG image:** `og-image.png`. **URL:** https://voronkatm.com/ · lang `ru`. ⚠️ Confirm the page `<head>` canonical + `og:url` point to voronkatm.com (not pages.dev) on next deploy, or Google/social will treat the old URL as canonical.

## Design system v3 «живая витрина» (for consistency across funnel assets — ads, IG)

- **Palette:** deep near-black `#050706`, panels `#0B0F0C`/`#10150F`, ink `#F4F7EC`, muted `#93A093`, lime anchor `#B4FF3A` + **spectral accent gradient** lime→mint→cyan (`#B4FF3A → #5EF2C8 → #3ECBFF`) — the premium-AI signature, used on gradient text («на автомате»), card borders, aurora glow.
- **Fonts:** Unbounded 700 (display, big fluid clamp) + Golos variable (body). Self-hosted subsetted woff2, no CDN.
- **Texture:** site-wide film grain (inline SVG turbulence, opacity .05), aurora hero atmosphere (3 pre-blurred drifting radial gradients, transform-only).
- **Motion:** kinetic word-by-word H1 rise, looping theater demo, lead-feed ticker, gradient process line draw, marquee. Everything transform/opacity-only; full reduced-motion fallback.
- **Core principle: the page performs the product.** It doesn't describe the system — it demos it live. This is the «хочу такую же» moment.

---

## v3 page structure (live section map)

1. **Header** — wordmark `voronka.tm` + pulsing «система активна» chip.
2. **Hero** — aurora + grain atmosphere; kinetic H1 «Больше клиентов из Instagram — **на автомате.**» (spectral gradient on «на автомате»); phone form in gradient-border panel (variant `hero`, mask `+993 6X XX XX XX`, animated ✓ success); below it the **lead-feed ticker** — Telegram-style demo cards sliding in, explicitly captioned «Так будут выглядеть ваши заявки» (demo framing, NOT fake proof).
3. **Театр — «Смотрите, как это работает»** — the centerpiece. CSS phone mockup playing a 4-scene sequence: IG ad → mini-landing with self-typing number → отправлено ✓ → Telegram notification on the owner's phone. **Loops endlessly** (3s pause between runs, pauses off-screen). Step captions light up per scene; CTA button «Хочу такую же систему» scrolls to the form.
4. **«Что изменится»** — before/after split (заявки тонут в директе vs каждая в телефоне).
5. **«Что вы получаете»** — bento grid with live UI fragments (mini ad, mini form, chat bubbles, CRM rows) instead of icons.
6. **«Как мы запускаем»** — process 01–04 with gradient line draw.
7. **«Подойдёт, если вам нужны клиенты»** — business-type marquee (2 rows).
8. **«Частые вопросы»** — slim FAQ accordion.
9. **«Готовы получать больше клиентов?»** — full-gradient final CTA panel, second form (variant `final`).
10. Footer + sticky mini-CTA bar (appears after hero scrolls out) + chat FAB.

## Chat (messenger-style, the second lead engine)

- **Notification:** page loads clean → at 6s (if no lead, chat untouched) the FAB gets a red «1» badge + soft WebAudio blip + wiggle; wiggle repeats every 10s until opened. Never auto-opens.
- **Flow:** welcome → ask for number. Quick options: **«📞 Оставить номер»** (in-chat phone input, tel keypad, +993 mask → real lead, `variant:'chat'`) / «Узнать больше» / «Как это работает?» / «Сколько стоит?». Informational options are **ask-once** — answered → button disappears; everything converges on the number.
- **Free typing on every step:** input row always visible; typed message containing a full 8-digit number becomes a lead automatically; random questions get steered to the audit + number.
- **After the lead** (from chat OR page form — both merge): «На каком языке вам удобнее разговаривать?» [Туркменский/Русский] → «Какой у вас бизнес?» → Instagram username (typed, «У меня нет Instagram» escape). Answers → Telegram + Sheet as `chat_answer`.
- **Raw telemetry:** every interaction (badge shown, open/close, each quick-reply tap, invalid phone, typed text, lead source) batches to Sheet tab **«Чат-лог»** — one row per event with session id + seconds-since-load. Sheets-only, never Telegram. **This is the optimization dataset:** after a few weeks of traffic, feed the tab to the AIOS for drop-off analysis before considering the Claude-API chat upgrade.
- Keyboard handling is solved (viewport meta `interactive-widget=resizes-content` + visualViewport lift) — don't re-debug hidden-input reports without checking those first.

## Keyboard handling on the two PAGE forms (fixed 2026-07-21)

The chat sheet got the visualViewport treatment in v2.1; the hero + final-CTA forms never did — they leaned on the `interactive-widget` meta tag alone. Fixed in `app.js`, block `Keyboard-safe phone fields`. **Two paths, because there are two kinds of browser:**

**1. Honest browsers (Chrome, iOS Safari).** The keyboard shrinks the visual (or layout) viewport, so we measure exactly what's left and slide the field in with an 18px pad. Verified: field pinned to 18px above the visible edge every time.

**2. ⚠️ INSTAGRAM'S ANDROID IN-APP WEBVIEW — this is ~100% of our traffic.** Its keyboard opens and **nothing** changes: `innerHeight` unchanged, `visualViewport.height` unchanged, `offsetTop` 0, no resize event ever fires. Measurement reports "the whole screen is visible" while half of it is under a keyboard, so any measurement-based fix computes a **zero correction** and the field stays buried. This is exactly why v1 of the fix worked in Chrome and failed in Instagram.
   → Fallback: when the viewport refuses to move, stop trusting it. Park the field at **28% from the top**, blind, no measurement. An Android keyboard eats 45–55%; at 28% the input *and* the submit button under it both stay clear. A real viewport signal always wins over the guess.

Supporting details: temporary `body` padding-bottom of 80% viewport height (the final form sits near the document end and otherwise physically can't be scrolled that high); sticky CTA bar hides while typing; **scroll forced instant** because `html{scroll-behavior:smooth}` would animate each correction and the re-fits would stack against a moving target.

Verified at 375×812 (blind path → field 227/812, submit button clears a 50% keyboard with 68px spare) and 375×400 (honest path → field pinned to 382 = edge − 18).

**Page forms confirmed fixed on a real device in the IG in-app browser, 2026-07-21.**

### Chat sheet — same bug, fixed 2026-07-22

Confirmed broken in the IG in-app browser (predicted, then verified on device): the chat bottom sheet used the same `kb = innerHeight - vv.height` maths, which is 0 in that WebView, so the sheet stayed at `bottom:0` with its input row under the keyboard.

Same two-path fix. Blind mode assumes the keyboard owns the bottom **62%** and lifts the sheet to a 35%-tall band above it. 62% is deliberately past the 45–55% a real Android keyboard takes: measured at 56%, the input row cleared a 55% keyboard by **1px**, which is no margin at all. At 62% it clears by 68px, and still by 28px against an absurd 60% keyboard. Cost of overshooting is a dimmed gap under the sheet; cost of undershooting is the lead. Restores to `bottom:''` / 82vh on blur.

---

## Config / identifiers

| Thing | Value |
|---|---|
| CF Pages project | `voronka` |
| Live URL | https://voronkatm.com (Pages URL https://voronka.pages.dev = fallback) |
| CF Account ID | `fe56143223792ccebd96a7205ffc129b` |
| GA4 | property `voronka.tm`, ID `G-LVK4PKT4C2` (lazy-loaded, `generate_lead` fires on submit) |

Backend wiring, secrets, and deploy runbook live in [04-lead-capture](04-lead-capture.md).

## To-do

- [x] **Meta Pixel** — DONE 2026-07-21. Pixel ID `1397681815558353`, in `index.html` head as a lazy loader (same first-interaction-or-idle schedule as GA4, so `fbevents.js` costs nothing at first paint). `trackLead()` fires `fbq('track','Lead')` on every submit. Verify in Events Manager → Test Events with one real submit.
- [ ] **Meta: verify `voronkatm.com`** in Business Settings → Brand Safety → Domains (DNS TXT or meta-tag), then configure Aggregated Event Measurement events for it. Ads point here now — do this BEFORE ad spend. (pages.dev couldn't be verified — shared domain; the custom domain is the fix.)
- [ ] Confirm page `<head>` canonical + `og:url` = voronkatm.com on next deploy.
- [ ] GA4 (optional): update the data stream's default URL to voronkatm.com — collection already works, this is cosmetic.
- [ ] Verify GA4 Realtime with one live test submit, then delete the test row.
- [ ] Delete leftover test rows from «Заявки» (incl. `L-SMOKE-v3` / +993 60 00 00 01 from the 2026-07-16 cutover).
- [ ] Regenerate `og-image.png` to match v3 brand (scraper-only, off-budget; optional).
- [ ] After first weeks of traffic: export «Чат-лог» → AIOS analysis → chat flow optimization.

## Solved bugs (don't re-debug)

1. Pages secret needs a redeploy to take effect.
2. Apps Script `/exec` returns 302 for both success AND error — "got a 302" ≠ row written; only trust parsed `ok:true`.
3. `getActiveSpreadsheet()` bound wrong file → use `openById(SHEET_ID)`.
4. Phone shown as `#ERROR!` — Sheets reads leading `+` as formula → `sheetSafe()` prefixes a space.

## Later / optional

- ~~Custom domain~~ **DONE 2026-07-22** — bought `voronkatm.com` on Namecheap (~$7/yr), nameservers moved to Cloudflare, attached to the `voronka` Pages project. `.tm` was gated/expensive, so went with `.com`.
- Upgrade scripted chatbot → real Claude-API conversation (haiku, via CF Function proxy).

## Consistency notes

**The live LP is the source of truth for the funnel's copy and angle.** Other assets (ads, IG) should match *it*:
- **Hook is outcome-first:** «Больше клиентов из Instagram — на автомате». The pain-first angle («Инстаграм есть, а клиентов нет?») lives in the *Problem* section, not the hero. `02-meta-ad.md` copy should echo the outcome-first hero.
- **No proof number on the page — by design.** The page sells the *system* generically («система, доведённая до звонка»). The ~$2 CAC number is ammo for the call / outreach / IG post only. Core reflects this (see [00-core.md](00-core.md)).
- Aligned with core throughout: Russian, agency «мы», no price shown, single conversion = free audit, no banned jargon.
