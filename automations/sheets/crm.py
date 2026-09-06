#!/usr/bin/env python3
"""Read the voronka Google Sheet CRM as structured data.

The sheet is an append-only EVENT LOG: one row per lead submit, one row per
chat answer, one row per call-button tap. That shape is right for a webhook
and wrong for anything that wants to reason about leads. This script folds it
back into one record per lead -- phone, source, the three chat answers, call
outcome, speed-to-call -- which is what a human or an agent actually wants.

Read-only. Uses spreadsheets.readonly; it cannot write even if asked to.

Run:  python crm.py                 # last 7 days, summary
      python crm.py --days 30
      python crm.py --from 2026-07-23 --to 2026-07-26
      python crm.py --all           # every row ever
      python crm.py --leads         # one line per lead
      python crm.py --calls         # call tracking + speed-to-call
      python crm.py --notes         # what they said on the phone, by outcome
      python crm.py --chat          # chat-log telemetry
      python crm.py --json          # machine-readable, for computing on
      python crm.py --raw Заявки    # untouched rows, when you distrust the parse
      python crm.py --with-tests    # keep the test/probe rows (hidden by default)
"""
import argparse
import json
import re
import sys
import time
import urllib.parse as urlparse
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
ENV = HERE / ".env"
API = "https://sheets.googleapis.com/v4/spreadsheets"
SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

LEADS_TAB = "Заявки"
CALLS_TAB = "Звонки"
CHAT_TAB = "Чат-лог"
# Written by profiles.py, not by the webhook. One row per lead, carrying the
# Instagram account the lead typed into the chat -- follower count and a
# permanent URL to a composite of their profile grid. Optional: the sheet
# works without it, so a missing tab is not an error here.
PROFILES_TAB = "Профили"
# Written by notes.py from «automations/sheets/leads-log.md» -- what the lead actually
# SAID on the phone, plus a category and the objection behind it. «Звонки»
# knows a call lasted four minutes; only this knows it ended in «дорого».
# Optional, like «Профили»: a missing tab degrades, it does not fail.
NOTES_TAB = "Заметки"

# Rows the pipeline generated while it was being built. They are real rows in
# a real sheet, so nothing deletes them -- but counting them as leads would
# inflate every number downstream. Matched on Lead ID, case-insensitive.
TEST_ID_MARKERS = (
    "TEST", "SMOKE", "PROBE", "PHONECHK", "REALFLOW", "CALLTRACK", "DIRECT",
)

# «Звонки» rows the Apps Script timer wrote itself, not a human tapping a
# button. They must not count as "Operator called this lead".
BOT_CALL_EVENTS = ("напоминание", "повтор")

CHAT_FIELD = {
    "На каком языке вам удобнее разговаривать?": "language",
    "Какой у вас бизнес?": "business",
    "Ваш Instagram-профиль": "instagram",
    "Есть ли у вас активный Instagram-профиль?": "has_instagram",
    "Сколько примерно клиентов приходит в день сейчас?": "clients_per_day",
}


def die(msg, fix=""):
    print(f"FAIL  {msg}", file=sys.stderr)
    if fix:
        print(f"      fix: {fix}", file=sys.stderr)
    sys.exit(1)


def load_env():
    if not ENV.exists():
        die(f"no {ENV}", "copy .env.example to .env (see README.md)")
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def token(env):
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests as gr
    except ImportError:
        die("google-auth not installed", "pip install google-auth requests")
    key = Path(env.get("SHEETS_CREDENTIALS_JSON", ""))
    if not key.is_absolute():
        key = HERE / key
    if not key.exists():
        die(f"key file not found: {key}", "see README.md -- the service account key")
    creds = service_account.Credentials.from_service_account_file(
        str(key), scopes=[SCOPE])
    creds.refresh(gr.Request())
    return creds.token


def fetch(env, tabs, strict=True):
    """Pull whole tabs in one call. Retries -- the connection here is 2-4 Mb/s VPN.

    strict=False returns {} instead of dying, for tabs that may not exist yet."""
    import requests
    sid = env["SHEET_ID"]
    q = "&".join("ranges=" + urlparse.quote(t) for t in tabs)
    url = (f"{API}/{sid}/values:batchGet?{q}"
           "&valueRenderOption=UNFORMATTED_VALUE"
           "&dateTimeRenderOption=FORMATTED_STRING")
    hdr = {"Authorization": "Bearer " + token(env)}
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, headers=hdr, timeout=90)
            if r.status_code == 200:
                out = {}
                for vr, name in zip(r.json().get("valueRanges", []), tabs):
                    out[name] = vr.get("values", [])
                return out
            if not strict:
                return {}          # tab probably absent; caller degrades quietly
            if r.status_code in (403, 404):
                die(f"HTTP {r.status_code} from Sheets: {r.text[:300]}",
                    "the service account may not be shared on the sheet -- "
                    "run python verify.py")
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # noqa: BLE001 -- VPN drops surface as many types
            last = f"{type(e).__name__}: {e}"
        if attempt < 3:
            time.sleep(2 ** attempt)
    if not strict:
        return {}
    die(f"Sheets unreachable after 4 tries -- {last}",
        "usually the VPN dropped. Retry before suspecting the code.")


def parse_dt(v):
    """Sheet timestamps are DD.MM.YYYY H:MM:SS, sometimes date-only."""
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def cell(row, i):
    return str(row[i]).strip() if len(row) > i and row[i] is not None else ""


def is_test(lead_id):
    u = lead_id.upper()
    return any(m in u for m in TEST_ID_MARKERS)


def parse_utm(page):
    """Pull the ad identity out of the landing URL. utm_content arrives
    percent-encoded as {{ad.video}} etc. -- Meta never substituted it."""
    if not page or "?" not in page:
        return {}
    qs = urlparse.parse_qs(page.split("?", 1)[1])
    out = {}
    for k in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_id"):
        if k in qs:
            out[k[4:]] = urlparse.unquote(qs[k][0])
    creative = out.get("content", "")
    m = re.search(r"\{\{ad\.([\w.]+)\}\}", creative)
    if m:
        out["creative"] = m.group(1)
    elif creative:
        out["creative"] = creative
    return out


def norm_phone(p):
    return re.sub(r"\D", "", p or "")


def fold_calls(leads, rows_calls):
    """«Звонки» has had two shapes. Dispatch on the header, not on a date.

    Until 28.07.2026 it was an append-only event log: one row per button tap in
    the Telegram bot. Almost nobody tapped, so it recorded bot nudges and little
    else. `calls.py` replaced it with one row per lead, rebuilt from the phone's
    own call log -- which is where the truth about calls always was. The old
    rows live on in «Звонки-архив», in the old shape, so this reader still has
    to understand both."""
    header = [str(c).strip() for c in (rows_calls[0] if rows_calls else [])]
    if "Хронология" in header or "JSON" in header:
        fold_calls_per_lead(leads, rows_calls, header)
    else:
        fold_calls_event_log(leads, rows_calls)


def fold_calls_per_lead(leads, rows_calls, header):
    idx = {name: i for i, name in enumerate(header)}

    def at(row, name):
        return cell(row, idx[name]) if name in idx else ""

    for row in rows_calls[1:]:
        lid = at(row, "Lead ID")
        if lid not in leads:
            continue
        L = leads[lid]
        got = at(row, "Дозвонился")
        L["reached"] = True if got == "Да" else False if got == "Нет" else None
        mins = at(row, "Через (мин)")
        L["minutes_to_call"] = int(mins) if str(mins).lstrip("-").isdigit() else None
        L["outcome"] = at(row, "Итог")
        L["call_comment"] = at(row, "Комментарий")
        try:
            blob = json.loads(at(row, "JSON") or "{}")
        except ValueError:
            blob = {}
        L["nudged"] = bool(blob.get("nudged"))
        L["call_stats"] = blob.get("stats", {})
        # One entry per real call off the phone, not per button tap. `event` is
        # kept as a word so anything that printed the old log still reads.
        for c in blob.get("calls", []):
            L["calls"].append({
                "ts": c.get("ts", ""),
                "event": {"out": "исходящий", "in": "входящий"}.get(
                    c.get("dir"), "пропущенный"),
                "outcome": "", "comment": "", "minutes_to_call": None,
                "duration": c.get("dur", 0),
            })


def fold_calls_event_log(leads, rows_calls):
    for row in rows_calls[1:]:
        lid, ev = cell(row, 1), cell(row, 3).lower()
        if lid not in leads:
            continue
        L = leads[lid]
        mins = cell(row, 7)
        L["calls"].append({
            "ts": (parse_dt(cell(row, 0)) or datetime.min).isoformat(),
            "event": ev, "outcome": cell(row, 4), "comment": cell(row, 5),
            "minutes_to_call": int(mins) if str(mins).isdigit() else None,
            "duration": 0,
        })
        if ev in BOT_CALL_EVENTS:
            L["nudged"] = True
            continue                        # bot row: never counts as contact
        if ev == "дозвонился":
            L["reached"] = True
        elif ev == "не взял трубку" and L["reached"] is None:
            L["reached"] = False
        elif ev == "итог" and cell(row, 4):
            # The verdict Operator picked after the call -- Договорились / Отказ /
            # Перезвонить. This, not «дозвонился», is what closes a lead.
            L["outcome"] = cell(row, 4)
        elif ev == "комментарий" and cell(row, 5):
            L["call_comment"] = cell(row, 5)
        if str(mins).isdigit() and L["minutes_to_call"] is None:
            L["minutes_to_call"] = int(mins)


def build(rows_leads, rows_calls, rows_profiles=None, rows_notes=None):
    """Event log -> one record per lead: chat answers, calls, profile, notes."""
    leads, order = {}, []

    for row in rows_leads[1:]:
        ts, typ, lid = parse_dt(cell(row, 0)), cell(row, 1), cell(row, 2)
        if not lid:
            continue
        if lid not in leads:
            leads[lid] = {
                "lead_id": lid, "ts": None, "phone": "", "phone_digits": "",
                "source": "", "variant": "", "page": "", "utm": {},
                "chat": {}, "chat_raw": [], "calls": [], "profile": {},
                "note": {},
                "is_test": is_test(lid), "is_duplicate_phone": False,
                "reached": None, "minutes_to_call": None, "nudged": False,
                "outcome": "", "call_comment": "", "call_stats": {},
            }
            order.append(lid)
        L = leads[lid]
        if typ == "lead":
            # First 'lead' row wins; a re-submit is the same person, not a new one.
            if L["ts"] is None:
                L["ts"] = ts
                L["phone"] = cell(row, 3)
                L["phone_digits"] = norm_phone(L["phone"])
                L["source"] = cell(row, 6)
                L["variant"] = cell(row, 7)
                L["page"] = cell(row, 8)
                L["utm"] = parse_utm(L["page"])
        elif typ == "chat_answer":
            q, a = cell(row, 4), cell(row, 5)
            if not a:
                continue
            L["chat_raw"].append({"ts": ts.isoformat() if ts else None,
                                  "question": q, "answer": a})
            key = CHAT_FIELD.get(q)
            if key:
                L["chat"][key] = a          # last answer wins -- he corrected it
            if L["ts"] is None:
                L["ts"] = ts                # chat-only lead: no phone row landed

    fold_calls(leads, rows_calls)

    # «Профили» — what profiles.py found on the handle the lead typed in chat.
    # `screenshot_url` is the point of the whole tab: an API reader gets a URL
    # it can open, where the `=IMAGE()` cell next to it is only pixels for Operator.
    for row in (rows_profiles or [])[1:]:
        lid = cell(row, 0)
        if lid not in leads:
            continue                        # manual --handle rows have no lead

        def n(i):
            v = cell(row, i)
            return int(v) if v.isdigit() else None

        p = {
            "handle": cell(row, 1).lstrip("@"),
            "followers": n(2), "following": n(3), "posts": n(4),
            "name": cell(row, 10), "bio": cell(row, 11), "website": cell(row, 12),
            "status": cell(row, 13), "checked": cell(row, 14),
            "screenshot_url": cell(row, 16),
            "stats": {}, "recent_posts": [],
        }
        # Column R is the machine payload: derived stats plus one entry per
        # recent post, captions included. The visible columns are a rendering
        # of the same thing for Operator -- read this, not them.
        try:
            blob = json.loads(cell(row, 17) or "{}")
            p["stats"] = blob.get("stats", {})
            p["recent_posts"] = blob.get("posts", [])
        except ValueError:
            p["status"] = (p["status"] or "") + " (данные не распарсились)"
        leads[lid]["profile"] = p

    # «Заметки» — The own words about the call, keyed by Lead ID. This is the
    # only surface in the whole sheet that says WHY a lead went the way it did.
    for row in (rows_notes or [])[1:]:
        lid = cell(row, 0)
        if lid not in leads:
            continue
        leads[lid]["note"] = {
            "n": cell(row, 1),
            "category": cell(row, 4),
            "objections": [o for o in cell(row, 5).split(", ") if o],
            "follow_up": cell(row, 6) == "да",
            "text": cell(row, 7),
            "original": cell(row, 8),
        }

    # Same phone submitted twice = one person, counted once. Keep the earliest.
    seen = {}
    for lid in order:
        d = leads[lid]["phone_digits"]
        if not d:
            continue
        if d in seen:
            leads[lid]["is_duplicate_phone"] = True
        else:
            seen[d] = lid

    out = [leads[l] for l in order]
    out.sort(key=lambda x: x["ts"] or datetime.min)
    return out


def in_window(lead, start, end):
    if lead["ts"] is None:
        return start is None
    if start and lead["ts"] < start:
        return False
    if end and lead["ts"] > end:
        return False
    return True


def jsonable(leads):
    out = []
    for L in leads:
        d = dict(L)
        d["ts"] = L["ts"].isoformat() if L["ts"] else None
        out.append(d)
    return out


def resolved(p):
    """A profile row that actually carries data. The статус is «ok», or
    «исправлен из «...»» when the handle the lead typed had to be repaired --
    both mean the lookup worked."""
    return (p.get("status") or "").startswith(("ok", "исправлен"))


def fmt_ts(ts):
    return ts.strftime("%d.%m %H:%M") if ts else "        —"


def print_summary(leads, label, hid):
    real = [L for L in leads if not L["is_test"] and not L["is_duplicate_phone"]]
    dupes = [L for L in leads if L["is_duplicate_phone"] and not L["is_test"]]
    withphone = [L for L in real if L["phone_digits"]]
    reached = [L for L in real if L["reached"] is True]
    missed = [L for L in real if L["reached"] is False]
    uncalled = [L for L in real if L["reached"] is None]
    speeds = [L["minutes_to_call"] for L in real if L["minutes_to_call"] is not None]

    print("=" * 72)
    print(f"CRM — Google Sheet «{LEADS_TAB}»   ({label})")
    print("=" * 72)
    print(f"\n  real leads          {len(real)}")
    print(f"  with a phone        {len(withphone)}")
    print(f"  duplicate submits   {len(dupes)}  (same phone, counted once)")
    if hid:
        print(f"  test/probe rows     {hid}  (hidden — --with-tests to show)")

    print(f"\n  called & reached    {len(reached)}")
    print(f"  no answer           {len(missed)}")
    print(f"  no call on record   {len(uncalled)}", end="")
    print("   <-- not in the phone's call log either" if uncalled else "")
    stats = [L["call_stats"] for L in real if L["call_stats"]]
    if stats:
        back = sum(1 for s in stats if s.get("called_back"))
        talk = sum(s.get("talk_total", 0) for s in stats)
        print(f"  they called back    {back}")
        print(f"  total talk time     {hhmmss(talk)}")
    if len(speeds) == 1:
        print(f"\n  speed to call       {speeds[0]} min (one sample — not a median)")
    elif speeds:
        speeds.sort()
        print(f"\n  speed to call       median {speeds[len(speeds)//2]} min"
              f"  ·  fastest {speeds[0]}  ·  slowest {speeds[-1]}"
              f"  (n={len(speeds)})")

    outcomes = {}
    for L in real:
        if L["outcome"]:
            outcomes[L["outcome"]] = outcomes.get(L["outcome"], 0) + 1
    if outcomes:
        print("\n  logged outcomes")
        for k, n in sorted(outcomes.items(), key=lambda x: -x[1]):
            print(f"    {n:>3}  {k}")
    print(f"\n  no outcome logged   {sum(1 for L in real if not L['outcome'])}"
          f" of {len(real)}")

    def tally(get, title):
        counts = {}
        for L in real:
            v = get(L) or "—"
            counts[v] = counts.get(v, 0) + 1
        if len(counts) <= 1 and "—" in counts:
            return
        print(f"\n  {title}")
        for k, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {n:>3}  {k}")

    tally(lambda L: L["utm"].get("creative"), "by ad creative")
    tally(lambda L: L["utm"].get("source"), "by utm_source")
    tally(lambda L: L["variant"], "by form position")
    tally(lambda L: L["chat"].get("business"), "business type (chat answer)")
    tally(lambda L: L["chat"].get("language"), "language (chat answer)")

    # What was actually said on the phone. This outranks every counter above
    # it: «reached» says a call connected, this says whether there is a deal in
    # it. Blank means no note written yet, NOT a lead that went nowhere.
    noted = [L for L in real if L["note"]]
    if noted:
        cats, objs = {}, {}
        for L in noted:
            c = L["note"]["category"] or "—"
            cats[c] = cats.get(c, 0) + 1
            for o in L["note"]["objections"]:
                objs[o] = objs.get(o, 0) + 1
        print(f"\n  по итогу разговора ({len(noted)} из {len(real)} с заметкой)")
        for k, n in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {n:>3}  {k}")
        if objs:
            print("\n  возражения")
            for k, n in sorted(objs.items(), key=lambda x: -x[1]):
                print(f"    {n:>3}  {k}")
        hot = [L for L in noted if L["note"]["category"] == "интерес"]
        if hot:
            print(f"\n  сказали «давайте попробуем» ({len(hot)})")
            for L in hot:
                print(f"    {L['phone'] or '—':<20} "
                      f"{(L['chat'].get('business') or '—')[:20]:<20} "
                      f"{L['note']['text'][:44]}")
        if len(noted) < len(real):
            print(f"\n  без заметки        {len(real) - len(noted)}"
                  f"  (дописать в «leads log», затем python notes.py)")

    igs = [L for L in real if L["chat"].get("instagram")]
    if igs:
        print(f"\n  instagram accounts given ({len(igs)})")
        for L in igs:
            p = L["profile"]
            if resolved(p):
                s = p.get("stats", {})
                print(f"    @{p['handle']:<24} {str(p.get('followers') or '?'):>7} подп."
                      f"  {str(p.get('posts') or '?'):>4} постов   {p.get('name', '')[:28]}")
                dead = s.get("days_since_last")
                line = (f"      последний пост {s.get('last_post') or '?'}"
                        f" ({dead if dead is not None else '?'} дн. назад)"
                        f"  ·  {s.get('posts_per_month') or '?'}/мес"
                        f"  ·  ER {s.get('er_pct') if s.get('er_pct') is not None else '?'}%"
                        f"  ·  медиана {s.get('median_likes') if s.get('median_likes') is not None else '?'} лайков")
                if s.get("reels_share_pct"):
                    line += f"  ·  Reels {s['reels_share_pct']}%"
                print(line)
                # Say the thing out loud rather than making him read the number.
                if dead is not None and dead > 60:
                    print(f"      ↳ аккаунт заброшен — это продажа «ведём аккаунт», "
                          f"а не «приводим трафик»")
                # Below 1000 followers a thin ER is just a small sample, so the
                # накрутка claim needs size behind it. The engagement is still
                # bad news at any size, and saying so is the point.
                if (s.get("er_pct") or 99) < 1:
                    if (p.get("followers") or 0) >= 1000:
                        print(f"      ↳ {p['followers']} подписчиков при ER "
                              f"{s.get('er_pct')}% — аудитория мёртвая или накручена")
                    else:
                        print(f"      ↳ ER {s.get('er_pct')}% — аудитория не реагирует")
            elif p.get("status"):
                print(f"    {L['chat']['instagram']:<26} — {p['status']}")
            else:
                print(f"    {L['chat']['instagram']:<26} — not looked up yet"
                      f"  (python profiles.py)")
    print()


def print_notes(leads):
    """One line per lead, ordered by what to do about it. The категория comes
    from notes.py; the text under it is The own, untouched."""
    order = ["интерес", "думает", "отложил", "перезвонит сам", "не поговорили",
             "нет ответа", "не понял", "пропал", "не ЦА", "не заявка"]
    noted = [L for L in leads if L["note"]]
    noted.sort(key=lambda L: (order.index(L["note"]["category"])
                              if L["note"]["category"] in order else 99,
                              L["ts"] or datetime.min))
    cur = None
    for L in noted:
        c = L["note"]["category"]
        if c != cur:
            cur = c
            print(f"\n— {c} —")
        obj = ", ".join(L["note"]["objections"])
        print(f"  {L['phone'] or '—':<20} "
              f"{(L['chat'].get('business') or '—')[:18]:<18} "
              f"{('[' + obj + ']' if obj else ''):<38} {L['note']['text'][:58]}")
    blank = [L for L in leads if not L["note"]]
    if blank:
        print(f"\n— без заметки ({len(blank)}) —")
        for L in blank:
            print(f"  {L['phone'] or '—':<20} "
                  f"{(L['chat'].get('business') or '—')[:18]:<18} "
                  f"{fmt_ts(L['ts'])}")


def print_leads(leads):
    print(f"{'when':<14} {'phone':<20} {'creative':<12} {'business':<22} "
          f"{'call':<10} {'instagram':<26} flags")
    print("-" * 128)
    for L in leads:
        flags = " ".join(f for f, on in (
            ("TEST", L["is_test"]), ("DUPE", L["is_duplicate_phone"]),
            ("nudged", L["nudged"])) if on)
        call = {True: "reached", False: "no answer", None: "—"}[L["reached"]]
        if L["minutes_to_call"] is not None:
            call += f" {L['minutes_to_call']}m"
        p = L["profile"]
        if resolved(p):
            ig = f"@{p['handle']} · {p.get('followers') or '?'}п"
        else:
            ig = L["chat"].get("instagram") or "—"
        print(f"{fmt_ts(L['ts']):<14} {L['phone'] or '—':<20} "
              f"{L['utm'].get('creative', '—'):<12} "
              f"{(L['chat'].get('business') or '—')[:22]:<22} {call:<10} "
              f"{ig[:26]:<26} {flags}")


def hhmmss(sec):
    if not sec:
        return ""
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def print_calls(leads):
    print(f"{'when':<14} {'phone':<20} {'event':<16} {'talk':<8} {'min':<6} comment")
    print("-" * 92)
    for L in leads:
        for c in sorted(L["calls"], key=lambda x: x["ts"]):
            when = c["ts"][5:16].replace("T", " ") if c["ts"] else "—"
            talk = hhmmss(c.get("duration")) or ("не взял" if c["event"] == "исходящий"
                                                 else "")
            print(f"{when:<14} {L['phone'] or '—':<20} {c['event']:<16} "
                  f"{talk:<8} {str(c['minutes_to_call'] or '—'):<6} {c['comment']}")

    stats = [L["call_stats"] for L in leads if L["call_stats"]]
    if not stats:
        return
    talked = sum(s.get("talk_total", 0) for s in stats)
    back = sum(1 for s in stats if s.get("called_back"))
    missed = sum(s.get("missed_from_them", 0) for s in stats)
    print(f"\nнаговорено {hhmmss(talked)} · перезвонили сами {back} · "
          f"пропущено от них {missed}")


def print_chat(rows, start, end):
    print(f"{'when':<12} {'session':<24} {'sec':<5} {'event':<16} details")
    print("-" * 90)
    kept = 0
    for row in rows[1:]:
        ts = parse_dt(cell(row, 0))
        if start and ts and ts < start - timedelta(days=1):
            continue
        if end and ts and ts > end:
            continue
        kept += 1
        print(f"{cell(row, 0):<12} {cell(row, 1):<24} {cell(row, 2):<5} "
              f"{cell(row, 3):<16} {cell(row, 4)}")
    print(f"\n{kept} events. Session-level telemetry — one row per interaction, "
          f"not per lead.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--from", dest="dfrom")
    ap.add_argument("--to", dest="dto")
    ap.add_argument("--all", action="store_true", help="no date window")
    ap.add_argument("--with-tests", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--leads", action="store_true")
    ap.add_argument("--calls", action="store_true")
    ap.add_argument("--chat", action="store_true")
    ap.add_argument("--notes", action="store_true",
                    help="what each lead said on the phone, grouped by outcome")
    ap.add_argument("--raw", metavar="TAB")
    a = ap.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    env = load_env()

    if a.raw:
        data = fetch(env, [a.raw])
        for row in data.get(a.raw, []):
            print(row)
        return

    data = fetch(env, [LEADS_TAB, CALLS_TAB] + ([CHAT_TAB] if a.chat else []))
    # Separate, tolerant call: «Профили» is optional and a missing tab must not
    # take the whole CRM read down with a 400.
    profiles = fetch(env, [PROFILES_TAB], strict=False).get(PROFILES_TAB, [])
    notes = fetch(env, [NOTES_TAB], strict=False).get(NOTES_TAB, [])
    leads = build(data[LEADS_TAB], data[CALLS_TAB], profiles, notes)

    if a.all:
        start = end = None
        label = "all time"
    elif a.dfrom or a.dto:
        start = datetime.strptime(a.dfrom, "%Y-%m-%d") if a.dfrom else None
        end = (datetime.strptime(a.dto, "%Y-%m-%d") + timedelta(days=1)
               if a.dto else None)
        label = f"{a.dfrom or 'start'} → {a.dto or 'now'}"
    else:
        start = datetime.now() - timedelta(days=a.days)
        end = None
        label = f"last {a.days} days"

    if a.chat:
        print_chat(data[CHAT_TAB], start, end)
        return

    leads = [L for L in leads if in_window(L, start, end)]
    hidden = 0
    if not a.with_tests:
        before = len(leads)
        leads = [L for L in leads if not L["is_test"]]
        hidden = before - len(leads)

    if a.json:
        # `count` is ROWS, not leads -- it always was, and reading it as a lead
        # count overstates the number by the duplicate submits. The real figure
        # is computed here once, so no consumer has to know the flag logic.
        real = [L for L in leads
                if not L["is_test"] and not L["is_duplicate_phone"]]
        by_creative = {}
        for L in real:
            k = (L.get("utm") or {}).get("creative") or "(none)"
            by_creative[k] = by_creative.get(k, 0) + 1
        print(json.dumps({
            "window": label,
            "sheet": env["SHEET_ID"],
            "tabs": {"leads": LEADS_TAB, "calls": CALLS_TAB, "chat": CHAT_TAB,
                     "profiles": PROFILES_TAB, "notes": NOTES_TAB},
            "hidden_test_rows": hidden,
            "count": len(leads),
            "summary": {
                "leads_real": len(real),          # <- THE number. Truth for заявки.
                "rows": len(leads),               # same as `count`
                "duplicate_phones": sum(1 for L in leads if L["is_duplicate_phone"]),
                "tests_hidden": hidden,
                "no_phone": sum(1 for L in real if not L.get("phone_digits")),
                "by_creative": by_creative,
            },
            "leads": jsonable(leads),
        }, ensure_ascii=False, indent=2))
    elif a.notes:
        print_notes(leads)
    elif a.calls:
        print_calls(leads)
    elif a.leads:
        print_leads(leads)
    else:
        print_summary(leads, label, hidden)


if __name__ == "__main__":
    main()
