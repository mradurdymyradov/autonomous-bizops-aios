# Checking a partner's Business Portfolio — procedure

**Run this when someone offers us access to their Meta Business Portfolio** and the question is whether
it unblocks [CAPABILITIES.md §2A](../CAPABILITIES.md) — the business-verification wall that stops
`campaign.py` from creating ad creatives, `ig_hashtag_search`, and the DM endpoints.

This file is the instruction an agent follows. `partner.py` is the tool it runs.

---

## Read this before running anything

**"Use her account" means two different things and only one of them unblocks anything.**

| What we could get | What it actually does |
|---|---|
| **Partner access to her ad account** | Lets us read and build campaigns *inside her account*. **Does not unblock ad-creative creation.** The block (code 100 / subcode 1885183) lives on **our app `automation_1` being in dev mode**, not on any ad account. Running through her account changes nothing about it — and it mixes her card with our spend. |
| **Her verified portfolio claiming our app** | **This is the unlock.** An app attached to a *verified* Business Portfolio can be published. Published app → creatives → `campaign.py` finishes → §2A closes, all three consequences at once. |

So the only question worth the evening is: **is her portfolio verified, and would she attach our app
to it?** Everything below serves that.

**It is a real ask, not a favour.** Once her business is the verified entity behind `automation_1`,
her legal entity carries Meta's policy liability for what that app does. Say that to her plainly
before asking. She is a friend, not a client with an engagement letter.

---

## Step 1 — get two things from her

1. **Business Portfolio ID.** She finds it at `business.facebook.com` → **Business settings** →
   **Business info**, field "Business portfolio ID" / «ID бизнес-портфеля». It is also in the URL of
   that page as `?business_id=…`. It's a ~15–16 digit number. Not secret.
2. **The verification status itself**, if she'll just look — see Step 2. Faster than anything API.

Do not ask her for a password, a token, or a screenshot of a token. If she offers one, decline.

## Step 2 — the zero-access check (do this first, it takes her 30 seconds)

Ask her to open, on her own device:

`business.facebook.com` → **Business settings** → **Security Centre** (Центр безопасности) →
**Business verification** / «Подтверждение компании».

The label drifts between Meta releases; the same status also appears on **Business info**. What we
need is one word:

| What her screen says | Field value | Verdict |
|---|---|---|
| Verified / Подтверждено | `verified` | **Go to Step 4.** |
| Not verified / Не подтверждено | `not_verified` | Same wall as ours. Stop. |
| In review / На рассмотрении | `pending` | Re-check in a few days. |
| Needs more info | `pending_need_more_info` | Stalled on her, not on us. |
| Started, not submitted | `pending_submission` | She *has* the documents. Worth asking her to finish. |
| Rejected / Failed | `failed` | Treat as not verified. |

A screenshot of that screen is enough. **If she answers here, Step 3 is optional** — it only exists to
put the answer in a script's output instead of a chat.

## Step 3 — the API check (only if we want it verified programmatically)

`verification_status` on the Business node is readable **only by a token with a role in that
portfolio**. We have no such token today, and nothing we currently hold can see her business. That is
expected, not a bug — `partner.py` will say so.

To get one, cheapest first:

**3a. She adds Operator as a person.** Business settings → **Users → People → Add** → his Facebook account
→ role **Admin**. (Employee can usually read the field but cannot do Step 4, so ask for Admin once
rather than twice.)

**3b. Operator generates a user token** at `developers.facebook.com/tools/explorer`, app `automation_1`,
permission `business_management`. Short-lived is fine — this is a one-off read.

**3c. Run the check.** Put it in `partner.env` next to `.env` (gitignored by `*.env`):

```
PARTNER_TOKEN=<the token from 3b>
PARTNER_BUSINESS_ID=<her portfolio id from step 1>
```

```bash
cd "D:/ai projects/vaios/automations/meta-ads" && python partner.py --assets
```

Useful variants:

```bash
python partner.py --list
```

```bash
python partner.py --ours
```

`--list` shows every portfolio the token can see, which is how you confirm the grant landed before
debugging anything else. **It only works with a USER token** — `/me/businesses` returns an empty list
for a SYSTEM_USER token by design, even one that reads its own portfolio fine. Empty there is not a
verdict; Step 2 of the script's output is.

`--ours` runs the same check against our own portfolio as a control. Verified 2026-08-04: it returns
`not_verified` for `833919419654873` «Онлайн продажи • Воронка • Туркменистан», so the field reads
correctly and any difference in her result is real.

**Reading the output:** `verification_status` is the only line that matters. If it comes back `None`,
the token lacks `business_management` or the role is too low — that is an access problem, not an
answer. Never record an empty field as "not verified".

## Step 4 — only if `verified`

Do **not** start clicking. The failure mode here is expensive: the system user `vaios-adsbot`, whose
never-expiring token runs `/check-ads`, `/check-ig`, `/check-crm` profile lookups and the snapshot
pipeline, lives inside our portfolio `META_BUSINESS_ID`. Detaching the app from that portfolio can
kill it.

Order of operations:

1. **Confirm the app's only remaining publish blocker is still verification.** App Dashboard →
   `automation_1` → **Publish**. Privacy URL, data-deletion URL, icon and category were all green as
   of 2026-07-23; re-check, because Meta adds requirements.
2. **Ask her explicitly**, with the liability sentence above said out loud.
3. **Snapshot the escape route first**: run `python verify.py` and save the output. That is the
   known-good state to compare against.
4. **Attach the app**: App Dashboard → **Settings → Basic → Business Portfolio** (this is where the
   "verified business" association lives). Select her portfolio. She approves the claim from her side.
5. **Re-run `python verify.py` immediately.** If the ads token broke, that is the signal to reissue a
   system-user token — from *her* portfolio if the app now lives there — before anything else.
6. **Do NOT press "Remove"** next to a business portfolio on the Publish tab. That is the button that
   detaches without replacing, and it is how the token dies for nothing.
7. Then try Publish, then re-run the blocked call:
   `python campaign.py --image … --headline … --primary-text … --budget 5` (dry run, no `--create`).

Log the outcome in [decisions/log.md](../../decisions/log.md) either way, and update
[CAPABILITIES.md](../CAPABILITIES.md) §2A — that section currently says the unlock arrives with a
paying client, and this route is not that.

## Step 5 — if not verified

Nothing to restructure. Her portfolio is behind the same wall ours is, and partner access to her ad
account buys us a mixed billing relationship and zero API capability. Say no to the offer, thank her,
and leave §2A where it is: **the gate to revenue is traffic and delivered pilots, not tooling.**

One thing is worth asking even then: **does she have a TKM-registered legal entity?** If yes, the
status is `pending_submission` or `not_verified` only because nobody walked the flow — and the flow is
walkable, because she has the documents Operator doesn't (registration certificate, bank statement, tax
document). That's a different conversation from "give us access", and a better one.

---

## What an agent must not do here

- **Do not** change anything in Business Settings, the App Dashboard, or an ad account. Every step
  above that mutates state is The to click, after a conversation with her.
- **Do not** accept her password, a token she pastes into chat, or a login session. If a credential
  reaches us, it goes in `partner.env` and nowhere else, and it gets rotated after.
- **Do not** report an empty or unreadable `verification_status` as a verdict. Inconclusive is
  inconclusive.
