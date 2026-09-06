# 04 — Lead capture (phone form + chatbot → Telegram + Sheet)

**Stage:** the capture layer — turns an LP visitor into a recorded lead you can call. Must match [00-core.md](00-core.md).

**Status: LIVE & working.** A real submit lands in BOTH Telegram and the Google Sheet, phone renders clean, chatbot fires. Verified with live test leads.

---

## The flow

```
Browser (site/index.html + app.js)
   │  POST /api/lead  { type, phone, phoneFmt, leadId, source, variant, page, ts }
   ▼
Cloudflare Pages Function  functions/api/lead.js
   ├─► Telegram Bot API sendMessage → @voronka_leadsbot (chat 1882381627)
   └─► Google Apps Script /exec webhook → Google Sheet, tab «Заявки»
```

## The scripted chatbot (verbatim from `app.js`, 2026-07-05)

Scripted MVP, quick-reply buttons (no free typing). Two entry paths:

**Path A — after a phone submit** (auto-opens the chat):
- «Спасибо! Заявку получили — скоро свяжемся.»
- «Чтобы аудит был точнее, ответьте на 3 коротких вопроса.»
- **Q1 «Какой у вас бизнес?»** → quick replies: Магазин · Кафе / ресторан · Салон красоты · Услуги
- **Q2 «Есть ли у вас активный Instagram-профиль?»** → Да, веду активно · Есть, но не веду · Пока нет
- **Q3 «Сколько примерно клиентов приходит в день сейчас?»** → Меньше 5 · 5–20 · Больше 20
- Close: «Спасибо! Всё записали. Подготовим бесплатный аудит и свяжемся с вами.»

Each answer POSTs `type:'chat_answer'` (with `leadId`, `step`, `question`, `answer`) → same lead record.

**Path B — floating FAB opened before any submit** (funnels toward the phone):
- Greeting: «Здравствуйте! Мы — команда voronka.tm. Чем можем помочь?»
- Quick replies + canned answers:
  - **«Как это работает?»** → «Настроим рекламу в Instagram, сделаем сайт с заявкой и подключим Telegram-бота — заявки приходят вам в телефон. Всё покажем на бесплатном аудите.»
  - **«Сколько стоит?»** → «Стоимость зависит от задач вашего бизнеса. Начнём с бесплатного аудита — разберём ситуацию и предложим решение. Оставьте номер телефона.»
  - **«Записаться на аудит»** → «Отлично! Оставьте номер в форме выше — перезвоним и всё разберём. Это бесплатно.»

Later optional upgrade → Claude API (haiku) via CF Function proxy so the key stays server-side.

**Consistency note:** the 3 qualifying questions (business type / active IG / clients-per-day) are what actually feed the audit call — keep [05-audit-call](05-audit-call.md) in sync with these, not with the old planned questions (the old "what ads have you tried" / "send IG handle" wording is NOT what's live).

## Phone form

- One field only: телефон. Mask `+993 6_ __ __ __` (`+993` locked prefix, TM mobile).
- Light validation (plausible TM number), no other required fields.
- Button: «Получить бесплатный аудит».

## Config / identifiers

| Thing | Value |
|---|---|
| Telegram bot | **@voronka_leadsbot**, chat id `1882381627` |
| Google Sheet ID | `19v4oqQ-l2-aibrUCZ_t9960CP6DSPzPUN-X6xvikEIA` (sheet «voronka», tab «Заявки») |
| Sheet webhook | `google-apps-script.gs` — Apps Script Web App, `openById(SHEET_ID)`, appends each lead/chat answer. Routes by `type`: `chat_log` → «Чат-лог», `call` → «Звонки», everything else → «Заявки» |
| Sheet tabs | «Заявки» (CRM) · «Чат-лог» (telemetry) · «Звонки» (one row per lead, rebuilt from The phone call log by `automations/sheets/calls.py` — 2026-07-28) · «Профили» (lead's Instagram, by `profiles.py`) · «Звонки-архив» (the retired button-tap log) |

**Webhook URL changed 2026-07-22.** A *new* Apps Script deployment was created (rather than editing the existing one), which mints a new `/exec` URL. `SHEETS_WEBHOOK_URL` was updated in both Cloudflare and `.dev.vars`, then redeployed — a secret change alone does not take effect. Verified end-to-end after the switch. **Always use Manage deployments → ✏️ Edit → New version to keep the URL stable.**

**Secrets** (never commit): `TG_BOT_TOKEN`, `TG_CHAT_ID`, `SHEETS_WEBHOOK_URL` — set as CF Pages env vars + mirrored in `.dev.vars` (gitignored).

## Smoke-test the live pipeline (no browser)

```bash
curl -s -X POST "https://voronkatm.com/api/lead?debug=1" \
  -H "Content-Type: application/json" \
  -d '{"type":"lead","leadId":"SMOKE","phone":"+99361000000","phoneFmt":"+993 61 00-00-00","source":"smoke"}'
# expect: {"ok":true,"sinks":[{"sink":"telegram","status":"sent"},{"sink":"sheets","status":"appended",...}]}
```

## Editing the Sheet webhook

Sheet → Extensions → Apps Script → paste `google-apps-script.gs` → Save → Deploy → Manage deployments → (active) → ✏️ Edit → New version → Deploy. Editing the SAME deployment keeps the `/exec` URL identical. A *new* deployment = new URL = must update `SHEETS_WEBHOOK_URL` secret + redeploy.

## The CRM

The Google Sheet «Заявки» IS the CRM. It's a leads log, not a revenue ledger — revenue tracking is separate/manual (cash). See [06-delivery](06-delivery.md).

**Reading it: `/check-crm`** (`automations/sheets/crm.py`, read-only). The sheet is an append-only *event log* — one row per submit, one per chat answer, one per call tap, joined only by `Lead ID`. The script folds that back into one record per lead. Never eyeball the raw rows to count leads; duplicates and bot rows will fool you.

**Live lead counts come from `/check-crm`, never from a file.**

## To-do

- [x] Delete leftover test rows (`DIRECT-TEST-1`, `PROBE-NEW`, `PHONECHK-*`, `LIVE-TEST-1`, `REALFLOW-*`, etc.). «Заявки» starts 2026-07-24 and holds no test rows; the old call rows including `L-CALLTRACK-TEST` moved to «Звонки-архив» when «Звонки» was rebuilt 2026-07-28, so the live tabs no longer disagree. The archive still carries 22–23.07 leads whose «Заявки» rows were cleared — read it as history, not as leads.
- [x] **Call tracking turned off on our bot, 2026-07-27.** 1 logged `итог` against 41 «напоминание» nudges — the metric was decorative and the nudge was noise. Buttons, outcome question, comment prompt, 30-min nudge and 2h retry are all behind off-by-default flags now (`CALL_TRACKING` in Cloudflare, `CALL_NUDGES_ENABLED` in Apps Script). Kept intact as a **client-build feature** — see [06-delivery](06-delivery.md). Lead cards are now plain: phone, source, id, time.
- [ ] **Run `disableCallTracking` in Apps Script** — the 5-minute trigger is still installed and is the thing that pings. Operator only (Google UI).

## Consistency notes

Chatbot lines are Russian, warm, no jargon → aligned with core. The 3 qualifying questions feed the audit call (see [05-audit-call](05-audit-call.md)) — keep them in sync with what the call actually needs.
