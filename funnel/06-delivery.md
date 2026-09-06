# 06 — Delivery + retainer (post-sale execution)

**Stage:** fulfillment — what we build and run after a client says yes. Must match [00-core.md](00-core.md).

**Status: FIRST EXECUTION LIVE (2026-07-24).** Two pilot clients closed off ad test-01 (see [02-meta-ad](02-meta-ad.md)). Pilot slots 1 and 2 of 3 are now used. This file stops being theory today — **update it DURING the builds, not after.**

**Before Day 1 of any build, confirm per client (this is what makes the free build convert):**
- [ ] **Price named out loud** — **$500 + 3 бесплатные рекламные кампании**, repeated back. **Do NOT mention $100/мес** (revised 2026-07-29): one number at the close, retainer later against their own data. **This is the whole mechanism** now that the N trigger is gone.
- [ ] **The 3 campaigns defined at the same time** — 3 setups (creative + audience + budget each), **not** counting the 5-day pilot test, valid 3 months. Undefined, it becomes unlimited free work; defined, its expiry is the retainer conversation.
- [ ] **$25 due at the day-5 meeting** — their money, 100% to Meta.
- [ ] **Same-day answer obligation** — stated, with the call-tracking bot named as the evidence.
- [ ] **Infra stays on our accounts** until the $500 clears.

If any of these weren't set on the call, set them now, before building. After a free system is already built and delivered, there is no leverage left to convert it.

**Capacity note:** builds run **one at a time, start to finish** — spec → questions → build → meeting. Not in parallel, not off a shared template. Per-client folders, stages and the spec contract: [`clients projects/README.md`](../clients%20projects/README.md).

---

## Terms recap (law lives in [00-core.md](00-core.md))

- **Pilot (clients 1–7, revised 2026-07-28/29):** price named out loud **before** Day 1 — **$500 + 3 free campaign setups, retainer not mentioned** → free 5-day build → day-5 meeting: **$25 cash** + Instagram connected → 5-day test at ~$5/day → they see the numbers and decide. Yes → **$500 cash**. **No N, no threshold, no guarantee.** The $100/mo is introduced later, when the free campaigns run out and there's data to optimise on.
- **Standard (client 4+):** $250 cash → build → $250 on live. Promise 7 days, build in 3–4.
- Infra (LP, bot, CRM, ad account) runs on **our** accounts until paid in full. That's the collection leverage — never hand over access before the $500 clears.

## Onboarding — what we need from the client (collect at the close meeting, ONE sitting)

Checklist — walk it with the client in person, leave with everything:

- [ ] **$25 cash** (pilot ad budget) — or $250 (standard tier).
- [ ] Business name, точка/адрес, working hours.
- [ ] **Товары/услуги + цены** — the 3–5 things they most want to sell (these drive LP copy + ad).
- [ ] **Instagram handle** — and **book the access meeting**. The ad runs under their handle, so their Instagram has to be connected to a Page we own. Procedure, safety script and the day-before message: [07-client-ig-access.md](07-client-ig-access.md). Don't improvise this at the table.
- [ ] ~~**Telegram account** that will receive leads~~ — **not asked as of 2026-08-01.** We create a
  **Telegram group per client** and add them to it; the lead bot posts into that group. One thread
  for заявки and for the whole build, and we see everything they see. Just add them at the meeting.
- [ ] ~~**Who answers leads**~~ — **read off their Instagram** (bio phone / WhatsApp). They answer
  their own leads; we only need the number the page dials. Correct it at the meeting if it's wrong.
- [ ] **Creative material to our spec:** we tell them exactly what to shoot on their phone — e.g. «3 фото товара при дневном свете, 1 вертикальное видео 15 сек: товар в руках, без монтажа». We do the rest.
- [ ] **Price repeated back** — $500 + 3 бесплатные кампании, so the day-5 decision isn't an ambush. **No $100/мес at this stage.**
- [ ] **Capacity** — how many customers a day they can actually serve. 5 days of ads can out-run a solo master, and 26 unanswered заявки is worse than none.
- [ ] Launch date agreed (build day 5) + how we contact them during the test (their TG).

No их карты, no payments from them, no ad account of their own — everything runs on our infra and our card. That's the pitch, not a limitation.

**One exception, and we state it upfront: Instagram.** The ad has to appear under their handle or it doesn't look like their business, so their Instagram gets connected to a Page we own. They type their own password, change it straight after, and can disconnect us whenever they like. Never sell this as "no access needed" — that was the old line, it's no longer true, and being caught softening it costs more than the objection itself. Full procedure and what we may and may not claim: [07-client-ig-access.md](07-client-ig-access.md).

## Build SOP — 5 days (clone our own stack)

**The page is built individually per client; only the plumbing is copied** (`functions/api/lead.js`, `functions/_shared.js`, `google-apps-script.gs` from `D:\ai projects\voronka\`). No shared LP template — decided 2026-07-28. Folder layout, stages and the `spec.md` contract: [`clients projects/README.md`](../clients%20projects/README.md).

**Day 0 — Spec.** Write `clients projects/<ig-handle>/spec.md` from the `/check-crm` dossier and their IG grid. If §8 «Вопросы» has entries, call the client and fill them before Day 1.
**Day 1 — LP.** Build the page for this business — their palette off their own grid, their photos, their words. **Voice note: the client's LP speaks as THEIR business** («Оставьте номер — [бизнес] перезвонит»), not as voronka.tm — agency «мы» is OUR funnel's voice only, and near-black + lime is OUR brand. New CF Pages project `[client]`.
**Day 2 — Capture.** New Telegram bot (BotFather) → leads to client's TG AND ours (we see everything). New Google Sheet from template: tabs «Заявки», «Звонки», «Чат-лог». Apps Script webhook (remember: `openById`, same-deployment edits, `sheetSafe()` for phones — solved bugs in [03](03-landing-page.md)/[04](04-lead-capture.md) apply verbatim).
**Day 3 — Tracking + QC.** Meta Pixel (new pixel in our Business Manager) + GA4 property. Full smoke test: curl the API, real submit from a cheap Android, verify Telegram + Sheet + pixel fires. Same checklist we ran on voronka.
**Day 4 — Ad.** Build creative from client materials, or reuse what's already on their account (brand rules: their look, not our lime). Campaign in our master account: geo TKM, **$25/5 days = $5/day**, objective leads/traffic (copy whatever our own test-01 proved). Client-facing ad copy mirrors their LP hook.
**Day 5 — Launch.** Client reviews LP on their phone (10 min, in person or TG screen-recording). Fix nits. Launch ads. Message client: «Запустили. Заявки начнут приходить вам в Telegram. Отвечайте в тот же день — договорённость.»

**QC gate before launch (all must pass):** form submits → TG arrives in <10 sec → Sheet row clean → pixel Lead event fires → LP loads fast on slow mobile data → all text Russian, no jargon, no price.

## Test protocol — 5 days (pilot)

- **Daily, 10 min:** spend, clicks, заявки count, cost per заявка. Log one line per day in the client's sheet.
- **Client side:** every lead notification carries the call-tracking buttons (below). If leads sit unanswered >1 day → message the client same day: «У вас 3 заявки без звонка — люди остывают. Договорённость была отвечать в тот же день.» With no N to defend, this is the only thing protecting the result from the client's own slowness.
- **Day 3 check:** if CTR is dead or cost per заявка is 3x expectation → swap creative/hook once. One swap, not endless fiddling.
- **Day 5 — decision meeting, no drift.** There is no threshold now, so the meeting is the mechanism. Show the sheet: заявки, timestamps, what their own calls produced.
  - **Yes →** collect **$500 cash** same day, retainer + ad budget start immediately. Ads DON'T continue between "yes" and cash in hand.
  - **No →** stop ads, infra off, part politely: «Спасибо, что попробовали — вы потеряли только 25.» Internally: post-mortem (niche, creative, CPM, где сломалось) — that data is the payment we got.
  - **«Подумаю» →** that's what the price-named-upfront rule exists to prevent. Set a date before leaving the table; an open-ended «подумаю» with our infra still running is a free client.

## Retainer ops ($100/mo)

**When it gets sold (2026-07-29):** not at the close. After the $500 clears, once the account has
run real campaigns and has numbers of its own. **Trigger: the third free campaign is used up.**
The pitch is optimisation off their own data — «вот что мы видим по вашим заявкам, вот что можно
улучшить» — not «платите за поддержку». That conversation is only possible because we held the
number back; it is also the conversation that turns $500 once into $1 200 a year, so it does not
get skipped. Track which of the 3 campaigns are spent per client in their sheet.

- **Collect:** $100 + ad budget top-up, cash, first days of each month. No cash → ads pause. Simple.
- **Monthly report** — 6 lines, sent in Telegram, plain Russian, no jargon:
  1. Потрачено на рекламу: $X
  2. Заявок пришло: Y
  3. Одна заявка обошлась примерно в: $Z
  4. Что мы меняем в рекламе в этом месяце: …
  5. Что стоит сделать вам: … (one action, e.g. «перезванивайте быстрее — 4 заявки ждали больше суток»)
  6. План на месяц: …
- Line 5 comes straight from the call-tracking data. This is the retainer's visible value — «мы переводим цифры в действия».

## Call-tracking Telegram bot — **CLIENT-ONLY. Switched off on our own bot 2026-07-27.**

**Status:** built, deployed, and then turned off for voronka. It worked; it just nagged Operator every 30 minutes about leads he had already called, and the buttons went untapped (1 outcome in 42 rows). Nothing was deleted — this is a **delivery feature we sell**, and it stays wired for pilot/client builds where the whole point is forcing *the client* to pick up the phone fast.

**Both switches must be on to run it** (default is off in both places):

| Where | Switch | On = |
|---|---|---|
| Cloudflare Pages env | `CALL_TRACKING` | `on` → lead cards get buttons, `/api/tg` logs taps |
| `google-apps-script.gs` | `CALL_NUDGES_ENABLED` | `true` + run `setupCallTracking` → 30-min nudge, 2h retry |

Off-switch on an existing install: run `disableCallTracking` once in Apps Script (deletes the timer), unset `CALL_TRACKING`, redeploy. Runbook: `voronka/STATUS.md`.

**Why we sell it:** nobody fills a spreadsheet; everyone taps a button in TG. Tracks speed-to-call + call outcomes. Uses: (1) client test-week enforcement/evidence, (2) retainer report line 5. Our own audit calls were the third use and it's the one that failed — Operator calls his leads within minutes anyway, so the nudge only ever arrived after the work was done.

**v1 spec — extend the existing lead bot, not a new bot:**
- Every «Новая заявка» notification arrives with inline buttons: **«📞 Дозвонился»** / **«Не взял трубку»**.
- «Дозвонился» → second row: **«Договорились» / «Думает» / «Отказ» / «Неверный номер»** → optional free-text/voice comment («Можете добавить пару слов — что сказал клиент?», skippable).
- «Не взял трубку» → bot re-asks in 2h (mirrors our own retry rule).
- **No tap in 30 min → one nudge:** «Позвонили по заявке? Нажмите результат 👇». One nudge only, not spam.
- Every tap → row in Sheet tab **«Звонки»**: leadId, timestamps (lead-arrival vs first tap = **speed-to-call, measured automatically**), outcome, comment.
- **Dogfood order:** wire it to OUR lead bot first, use it on our own audit calls, then it's already client-ready for the first pilot build.

### v1 build status — DEPLOYED 2026-07-21/22, DISABLED 2026-07-27

Cloudflare side went live 2026-07-21 (prod deployed, `TG_WEBHOOK_SECRET` set, webhook registered on @voronka_leadsbot, verified with a smoke lead); the Apps Script half landed 2026-07-22. Both halves are now behind the off-by-default flags above. The code below is the client-build reference.

| Piece | File | What it does |
|---|---|---|
| Buttons on the lead card | `functions/api/lead.js` | Every «Новая заявка» ships with the two-button keyboard |
| Tap handler | `functions/api/tg.js` **(new)** | Telegram webhook: taps → «Звонки» rows, outcome row, comment prompt |
| Shared helpers | `functions/_shared.js` **(new)** | Telegram + Sheets calls, keyboards. Underscore = library, not a route (verified in the Pages build) |
| Tab + timers | `google-apps-script.gs` | «Звонки» tab, speed-to-call, 30-min nudge, 2h retry |

**Design notes worth keeping:**
- **No state store.** The leadId rides in `callback_data`; the comment prompt tags itself `#<leadId>` so a reply maps back by parsing `reply_to_message`. No KV, no D1, nothing to provision or pay for.
- **Apps Script is the scheduler.** Pages Functions have no cron, and the sheet already holds both halves of the state (leads + taps). A 5-minute time-driven trigger sends the nudge and the retry — so a "30-minute" nudge really fires at 30–35 min. Fine.
- **Speed-to-call excludes bot rows.** The nudge writes its own «напоминание» row; it's filtered out of the first-tap calculation, or every slow lead — the ones that matter — would lose its measurement.
- Webhook **fails closed** without `TG_WEBHOOK_SECRET`: «Звонки» is what the retainer report is built on, so an open endpoint that anyone could poison isn't acceptable.

**Remaining step to actually stop the pings** (runbook in `voronka/STATUS.md`): paste the updated `google-apps-script.gs` → Save → run `disableCallTracking` once. Flipping `CALL_NUDGES_ENABLED` alone isn't enough — the installed trigger keeps waking up, it just no-ops.

**Test rows to delete:** `L-CALLTRACK-TEST` / +993 60 00 00 02 in «Заявки».

## Revenue tracking

$0 to date. On the first dollar: tab **«Деньги»** in our own sheet — date · client · what (setup / retainer / ad budget) · amount · where the cash sits. No new tools.

## Post-relocation money (unchanged)

Cash-in-hand now. After Bali: trusted TKM contact collects cash, small commission, transfers via card/crypto.

## Consistency notes

Delivery scope = exactly what LP + call promise: LP + Pixel/GA4 + TG bot + Sheets CRM + ads management. Pilot terms verbatim from core. If core's offer changes, update the promise (upstream files) AND this scope together — most dangerous drift point in the funnel.

## Open items (close during first delivery)

- [x] ~~Client LP template extracted from voronka codebase~~ — **decided against 2026-07-28.** Pages are individual; only the plumbing is copied. See [`clients projects/README.md`](../clients%20projects/README.md) §4.
- [ ] Creative-spec one-pager for clients (what to shoot; write at first onboarding).
- [x] Call-tracking bot v1 — **code done 2026-07-21**, pending deploy + webhook registration (see build status above). Dogfood on our own leads once live.
- [ ] Retainer report template file (write when first retainer starts; structure above).
