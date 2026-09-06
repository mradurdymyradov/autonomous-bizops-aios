# 07 — Client Instagram access (permission to run their ads)

**Stage:** sits between the close and Day 4 of the build ([06-delivery.md](06-delivery.md)). Must match [00-core.md](00-core.md).

**Status: method chosen 2026-07-28, not yet executed on a live client.** First run is pilot client 1. Update this file DURING that meeting, not after.

**The problem this solves:** in Turkmenistan the western path doesn't exist. Clients have no Facebook, no Business Portfolio, no ad account, and cannot grant partner access. But an Instagram ad must run under *their* handle or it doesn't look like their business. So exactly one permission has to cross, and the whole design is about making that crossing small, visible, and reversible by them.

---

## The model

| Ours | Theirs |
|---|---|
| Business Portfolio, ad account, **card**, pixel | Their Instagram account — always, without exception |
| The Facebook Page we create per client | Their password, their 2FA, their right to disconnect us |

**What actually crosses:** one link between their Instagram and a Page we control. Nothing else. We cannot change their password, cannot take ownership, cannot lock them out.

---

## Ruled out — do not re-research

Each of these cost an evening. They're closed.

| Route | Why it's dead |
|---|---|
| Client creates an ad account / grants partner access | Requires them to have Facebook + a Business Portfolio. The ICP does not. |
| `business.facebook.com` from The phone | Advanced Protection on our FB account forces a passkey; the passkey is device-bound; desktop PC and phone won't pair over Bluetooth for cross-device auth. No laptop, no office. Closed 2026-07-28. |
| Instagram "Shared Access" | Availability is inconsistent and it does not grant Ads Manager identity. |
| Partnership ad codes | Boosts an existing post only. Eligibility gates. No good for a cold campaign with our creative. |
| Holding client passwords in an antidetect browser + proxies | What local agencies actually do at 100+ accounts. Not our method — we don't store credentials. |

---

## The method — Facebook app on The phone

The Facebook app is already logged in, so the passkey wall never appears. This is the whole trick.

### Before the meeting — at the PC

1. Create a **Page per client** inside the Business Portfolio: Настройки бизнеса → Аккаунты → Страницы → Add. Name = their business, their logo.
   **One Page = one Instagram.** Never reuse a Page across clients.
2. Assign the Page to the ad account.
3. Send the client the pre-meeting message below. **A day early, not the same morning.**

### At the meeting — The phone, Facebook app

4. **Their Instagram must be a professional account** — they do this on their own phone: Settings → Account type. One tap, free, reversible.
5. Facebook app → switch to their Page → **Settings → Linked accounts → Instagram → Connect account**.
6. **Hand them the phone. They type their own login.** Operator doesn't watch and doesn't write it down. Decline any save-password prompt.
7. A confirmation code or "Это вы?" check lands on their phone. They clear it sitting right there.
   **This is the entire reason the meeting is in person.** The login originates from our IP through a VPN — Instagram will flag it. Present, they resolve it in ten seconds. Absent, that's the exact scenario where accounts get locked.
8. **Immediately after:** they change their password and switch on two-factor. The link survives — it runs on a token, not on the password. Say this out loud while they do it; it's the moment the fear dies.

### After — at the PC

9. Ads Manager → identity = their Page → their Instagram appears in the list → build the campaign as normal.

### 10. «Confirm your connection» — the prompt to IGNORE (first hit 05.08.2026, Наргиля)

After step 9 works, Ads Manager shows a yellow **«Review this connection to use more features»**
next to the Instagram profile, and the dialog behind it asks to confirm **by logging into
Instagram** — i.e. her password, again, at our PC, over the VPN. That is precisely the path §«Три
варианта» calls the one that gets accounts locked.

**It is not a blocker and it is not part of this method. Do not click Confirm.** Three reasons:

- **The identity already resolved.** The dialog's own first line reads «A Page admin or editor
  connected ngmakeup to @ng_makeup_stylist» — the link from step 5–6 exists. If it didn't, the
  Instagram profile field in Ads Manager would be empty or fall back to the Page. It isn't.
- **Confirm has a destructive side effect, stated on the dialog itself:** «If your Instagram is
  linked to a commerce account, the link needs to be removed before your Facebook Page can be
  connected. **We'll do this for you if you continue.**» Any client tagging products (Наргиля
  works with [@kisti_pudra](https://instagram.com/kisti_pudra)) loses that link silently, and it's
  our fault on their account.
- **«Disconnect account» sits directly beside «Confirm connection».** One misclick undoes the only
  permission that ever crosses, and redoing it costs another in-person session.

What confirming actually buys is cross-surface *management* — IG messages and comments in the Page
inbox, joint Insights, shared settings. None of it is needed to deliver an ad.

**The 30-second test that settles it, before publishing any campaign:** open the ad **Preview** and
switch to an Instagram placement. Her handle and avatar on the post → done, publish. The Page name
`ngmakeup` instead → *then* it's a real blocker, and the fix is still never «get her password» —
it's the «Don't know the password?» dropdown on that same dialog, which hands the confirmation to
the account owner to complete on **her own** device.

---

## Three options, in the order we offer them

1. **In person — the default.** They type, we never learn the password. Costs travel time; buys all the trust.
2. **By phone — only if they refuse the visit.** They dictate the login, we connect *while they are on the line* so they can clear the security check live, they change the password the moment it's done. Offer this only after they push back on the visit — never as the opening proposal.
3. **Partner access — rare.** Only if they already have a Facebook Business Portfolio, i.e. somebody ran ads for them before.

**Never:** take the password and connect later, alone, from our VPN. That is the one path that genuinely gets client accounts locked, and it would be our fault in a market where everyone knows everyone.

---

## Pre-meeting message (Russian, funnel voice — send the day before)

> Здравствуйте! Завтра подключаем рекламу к вашему Instagram.
>
> Две просьбы, чтобы всё заняло 15 минут:
>
> 1. Проверьте, помните ли вы пароль от Instagram. Если нет — сбросьте его **заранее**, до встречи.
> 2. Держите телефон под рукой: на него придёт код подтверждения.
>
> Пароль нам называть не нужно — вы введёте его сами, и сразу после подключения сможете его сменить. Доступ к рекламе от этого не пропадёт.

### The password check — the #1 thing that kills the meeting

Most owners here have been logged in for years and have never typed the password. Worse: the account was often set up by a nephew or a former employee, and **the linked email is theirs**.

They check this themselves, the day before:
Instagram → Settings → Accounts Center → Personal details → **Contact info** — which email and phone are attached?

- Remembers the password → nothing to do.
- Doesn't, but controls the email/phone → **reset before the meeting.** Never at the meeting; a reset can hang, and we're not sitting in their shop waiting for a letter.
- Doesn't control the email → solve this *before* travelling, or the trip is wasted.

---

## What we say about safety — and what we must not claim

**Truth we state plainly:** linking to the Page gives us access to posts and messages, not only to ads. Say it. If they discover it later, we lose a client over something that was never a problem.

Correct wording: «мы видим переписку и можем публиковать; мы этим не пользуемся без вашей просьбы, и вы отключаете нас когда захотите».

**The four sentences at the meeting:**

> Пароль вы вводите сами, мы его не видим. Сразу после подключения смените его — доступ к рекламе останется. Включите двухфакторную защиту, тогда аккаунт защищён даже от нас. Отключить нас можете в любой момент сами, за два нажатия.

**What cannot happen to them:** we can't change their password, can't remove them, can't take ownership. They disconnect us whenever they like, without asking. If an ad breaks Meta's rules, the ad is rejected and it hits **our** ad account — never their profile.

**What we don't promise:** a guarantee. Nobody can give one. The honest offer is that the risk stays under *their* control, and that sells better than a promise they'd be right not to believe.

---

## Failure modes — expect these

- **Client doesn't remember the password.** The most likely cause of a wasted trip. Checked the day before, every time.
- **Linked email belongs to someone else.** Second most likely. Same check catches it.
- **Instagram still on a personal account.** One tap, but do it before step 5, not during.
- **Connection dies mid-flow.** 2–4 Mb/s over VPN. Retry, don't restart from scratch, don't assume it broke.

---

## Open questions — answer on the first live client

- Does the Page link alone put the client's Instagram into our portfolio **as an asset**? Enough for ads either way; needed if we ever want `/check-ig` on client accounts. Verify and record here.
- Does a pilot client with a **registered business** granting us access unblock the Meta business-verification wall? That wall is what stops `campaign.py` finishing a campaign — see [automations/CAPABILITIES.md](../automations/CAPABILITIES.md) §2A. If yes, it's worth asking both pilots whether they're legally registered.

