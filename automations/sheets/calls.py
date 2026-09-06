#!/usr/bin/env python3
"""Rebuild the «Звонки» tab from The real Android call log.

Why this exists
---------------
«Звонки» was designed as an append-only event log fed by buttons in the
Telegram bot: one row per tap. Operator almost never tapped them, so the tab filled
up with «напоминание» rows the Apps Script timer wrote itself, plus a handful
of probe rows on his own number. Reading it, every real lead looked uncalled.
He had in fact called 59 of 60 of them -- the evidence was on his phone, not
in the sheet.

So the truth about calls lives in the phone's call log. This script takes an
SMS Backup & Restore XML export, matches every call to a lead by phone number,
and rewrites «Звонки» as ONE ROW PER LEAD: when he called, how long they
talked, whether they rang back, how long he took to pick the lead up.

The old event-log rows are copied to «Звонки-архив» before anything is
cleared. Nothing is deleted.

Export the XML on the phone: SMS Backup & Restore -> Set up a backup ->
Call logs -> save to Downloads, then copy it to the PC.

Run:  python calls.py --xml ~/Downloads/calls-*.xml            # last 5 days
      python calls.py --xml FILE --days 14
      python calls.py --xml FILE --all
      python calls.py --xml FILE --dry-run    # print the table, write nothing
"""
import argparse
import json
import re
import sys
import time
import urllib.parse as urlparse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import crm  # read side: env, fetch, lead folding. crm.py is read-only by design.

HERE = Path(__file__).parent
API = "https://sheets.googleapis.com/v4/spreadsheets"
WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
OVERRIDES = HERE / "phone-overrides.json"

TAB = "Звонки"
ARCHIVE_TAB = "Звонки-архив"
# The rebuild rewrites «Звонки» wholesale. Everything else in this spreadsheet
# is truth Operator maintains by hand or the webhook appends -- refuse it here so a
# later edit to this file can't quietly widen the blast radius.
GUARDED_TABS = ("Заявки", "Чат-лог", "Профили")

# Ashgabat. The phone, the Meta ad account and GA4 are all on this offset, so
# every timestamp in the funnel lines up day-for-day without conversion.
TZ = timezone(timedelta(hours=5))

# android.provider.CallLog.Calls type codes
INCOMING, OUTGOING, MISSED, VOICEMAIL, REJECTED, BLOCKED, EXTERNAL = range(1, 8)

HEADER = [
    "№", "Lead ID", "Заявка", "Телефон", "Бизнес", "Instagram", "Креатив",
    "Первый звонок", "Через (мин)", "Исходящих", "Дозвонился", "Разговоров",
    "Общий разговор", "Самый долгий", "Перезвонил", "Время перезвона",
    "Пропущено от них", "Последний контакт", "Итог", "Хронология",
    "Комментарий", "JSON",
]
COL = {name: i for i, name in enumerate(HEADER)}
LAST_COL = "V"

OUTCOMES = ["Договорились", "Отказ", "Перезвонить позже", "Думает",
            "Не дозвонился", "Не тот номер"]


# ------------------------------------------------------------------ helpers

def die(msg, fix=""):
    crm.die(msg, fix)


def log(msg):
    print(msg, flush=True)


def phone_key(s):
    """Match on the last 8 digits -- the subscriber part of a Turkmen mobile.
    The sheet writes «+993 61 59 42 38», the phone writes «+99361594238», and
    a lead who typed «61594238» is the same person as both."""
    return re.sub(r"\D", "", s or "")[-8:]


def hhmmss(sec):
    if not sec:
        return ""
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt(dt, with_date=True):
    if not dt:
        return ""
    return dt.strftime("%d.%m.%Y %H:%M" if with_date else "%H:%M")


# ------------------------------------------------------------- the call log

def read_xml(path):
    """SMS Backup & Restore call-log export -> list of calls, oldest first."""
    p = Path(path).expanduser()
    if not p.exists():
        # let the caller pass a glob: calls-*.xml
        hits = sorted(Path(p.parent).glob(p.name))
        if not hits:
            die(f"no call-log XML at {path}",
                "export it from SMS Backup & Restore -> Call logs")
        p = hits[-1]
        log(f"using {p.name}")
    try:
        root = ET.parse(p).getroot()
    except ET.ParseError as exc:
        die(f"{p.name} is not parseable XML: {exc}",
            "re-export from the app -- a truncated transfer looks like this")
    out = []
    for c in root.findall("call"):
        try:
            ts = datetime.fromtimestamp(int(c.get("date")) / 1000, TZ)
        except (TypeError, ValueError):
            continue
        out.append({
            "ts": ts,
            "num": c.get("number") or "",
            "key": phone_key(c.get("number")),
            "dur": int(c.get("duration") or 0),
            "type": int(c.get("type") or 0),
            "name": (c.get("contact_name") or "").strip(),
        })
    out.sort(key=lambda x: x["ts"])
    if not out:
        die(f"{p.name} has no <call> rows", "wrong export type? this wants Call logs")
    return out


def load_overrides():
    """Phones «Заявки» never captured, confirmed by Operator and kept in a file so
    they survive every rebuild. `calls.py` deliberately does not infer these --
    a contact label that happens to fill a gap in the numbering is a guess, and
    a guessed phone in a CRM is worse than a blank one."""
    if not OVERRIDES.exists():
        return {}
    try:
        raw = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"{OVERRIDES.name} is not valid JSON: {e}")
    out = {}
    for lid, v in raw.items():
        if lid.startswith("_"):
            continue
        phone = (v.get("phone") if isinstance(v, dict) else v) or ""
        if phone.strip():
            out[lid] = (phone.strip(), (v.get("why", "") if isinstance(v, dict) else ""))
    return out


def apply_overrides(leads, overrides):
    """Fill in a missing phone, never silently replace a captured one."""
    used = []
    for L in leads:
        hit = overrides.get(L["lead_id"])
        if not hit:
            continue
        phone, why = hit
        if L["phone"] and phone_key(L["phone"]) == phone_key(phone):
            continue                        # already right, nothing to do
        if L["phone"]:
            log(f"  ! {L['lead_id']} already has {L['phone']}, override says "
                f"{phone} — leaving the sheet's value, fix «Заявки» or the file")
            continue
        L["phone"] = phone
        L["phone_digits"] = re.sub(r"\D", "", phone)
        L["_override_why"] = why
        used.append(L["lead_id"])
    return used


def label_of(calls):
    """Operator saves each lead as a contact named L1, L2, ... in submit order.
    That label is how he refers to them out loud, so it goes in column A."""
    for c in calls:
        m = re.match(r"^(L\d+)\b", c["name"])
        if m:
            return m.group(1)
    return ""


# ------------------------------------------------------------ the fold

def attach(leads, calls):
    """Give every call to exactly one lead: the EARLIEST submit on that number
    at or before the call. Two rows sharing a phone are one person submitting
    twice, and crm.py dedups by keeping the earliest -- put the calls on the
    row that survives that, or every duplicate reads as never-called. It is
    also the honest speed-to-lead: measured from the first time they raised
    their hand, not the second."""
    by_key = {}
    for L in leads:
        if L["phone"]:
            by_key.setdefault(phone_key(L["phone"]), []).append(L)
    for v in by_key.values():
        v.sort(key=lambda L: L["ts"] or datetime.min)

    for L in leads:
        L["_calls"] = []
        # Same phone on two rows is one person who submitted twice. Every call
        # lands on one of the two rows, so each needs to know about the other
        # or the empty one reads as "never called".
        L["_siblings"] = [o for o in by_key.get(phone_key(L["phone"]), [])
                          if o is not L] if L["phone"] else []
    unmatched = []
    for c in calls:
        cands = by_key.get(c["key"])
        if not cands:
            unmatched.append(c)
            continue
        naive = c["ts"].replace(tzinfo=None)
        owner = next((L for L in cands if L["ts"] and L["ts"] <= naive), cands[0])
        owner["_calls"].append(c)
    return unmatched


def stats(L):
    """Everything column H..T is computed from, in one place."""
    cs = sorted(L["_calls"], key=lambda c: c["ts"])
    out = [c for c in cs if c["type"] == OUTGOING]
    inc = [c for c in cs if c["type"] == INCOMING]
    missed = [c for c in cs if c["type"] in (MISSED, REJECTED)]
    talked = [c for c in cs if c["dur"] > 0]

    first_out = out[0]["ts"] if out else None
    submit = L["ts"]
    mins = None
    if first_out and submit:
        delta = (first_out.replace(tzinfo=None) - submit).total_seconds() / 60
        mins = int(round(delta)) if delta >= 0 else None

    first_back = next((c["ts"] for c in inc if c["dur"] > 0), None)
    if not first_back and missed:
        first_back = missed[0]["ts"]

    return {
        "label": label_of(cs),
        "first_out": first_out,
        "minutes_to_call": mins,
        "outgoing": len(out),
        "reached": bool(talked),
        "conversations": len(talked),
        "talk_total": sum(c["dur"] for c in talked),
        "talk_longest": max((c["dur"] for c in talked), default=0),
        "called_back": any(c["dur"] > 0 for c in inc),
        "first_back": first_back,
        "missed_from_them": len(missed),
        "last_contact": cs[-1]["ts"] if cs else None,
        "chain": cs,
    }


def chain_text(cs):
    """Human-readable call chain. «исх 13:39 · 2:16» reads faster than any
    number of columns, and it is the thing Operator actually scans."""
    bits = []
    day = None
    for c in cs:
        d = c["ts"].strftime("%d.%m")
        stamp = c["ts"].strftime("%H:%M") if d == day else f"{d} {c['ts'].strftime('%H:%M')}"
        day = d
        if c["type"] == OUTGOING:
            bits.append(f"исх {stamp} · {hhmmss(c['dur'])}" if c["dur"]
                        else f"исх {stamp} · не взял")
        elif c["type"] == INCOMING:
            bits.append(f"ВХ {stamp} · {hhmmss(c['dur'])}" if c["dur"]
                        else f"ВХ {stamp} · сброс")
        else:
            bits.append(f"ПРОПУЩЕН {stamp}")
    return "  ·  ".join(bits)


def keep_human(old_rows):
    """`Итог` and `Комментарий` are the two columns a human owns. Everything
    else is derived and safe to regenerate; these would be destroyed by the
    rebuild that regenerates them. Carry them across.

    `Комментарий` is shared: the script writes notes there too. `auto_note` in
    the hidden JSON says what the last run put in the cell, so a note the script
    wrote is regenerated and only a note Operator wrote is preserved. Without that
    comparison a stale generated note outlives the condition it described."""
    header = [str(c).strip() for c in (old_rows[0] if old_rows else [])]
    if "Хронология" not in header and "JSON" not in header:
        return {}                           # old event-log shape: nothing to keep
    idx = {n: i for i, n in enumerate(header)}
    need = ("Lead ID", "Итог", "Комментарий")
    if not all(n in idx for n in need):
        return {}
    out = {}
    for row in old_rows[1:]:
        def at(name):
            if name not in idx:
                return ""
            i = idx[name]
            return str(row[i]).strip() if len(row) > i and row[i] is not None else ""
        if not at("Lead ID"):
            continue
        try:
            blob = json.loads(at("JSON") or "{}")
        except ValueError:
            blob = {}
        note = at("Комментарий")
        if "auto_note" not in blob:
            # Row predates note-tracking (the first rebuild, 2026-07-28). Nothing
            # but this script had written the column yet, so treat it as generated.
            note = ""
        elif note == blob["auto_note"]:
            note = ""
        out[at("Lead ID")] = (at("Итог"), note)
    return out


def row_for(L, s, nudged, note):
    return [
        s["label"],
        L["lead_id"],
        fmt(L["ts"]) if L["ts"] else "",
        L["phone"],
        (L.get("chat") or {}).get("business", ""),
        (L.get("chat") or {}).get("instagram", ""),
        (L.get("utm") or {}).get("creative", ""),
        fmt(s["first_out"]),
        s["minutes_to_call"] if s["minutes_to_call"] is not None else "",
        s["outgoing"] or "",
        ("Да" if s["reached"] else "Нет") if s["outgoing"] or s["chain"] else "",
        s["conversations"] or "",
        hhmmss(s["talk_total"]),
        hhmmss(s["talk_longest"]),
        "Да" if s["called_back"] else ("Пропущен" if s["missed_from_them"] else ""),
        fmt(s["first_back"]),
        s["missed_from_them"] or "",
        fmt(s["last_contact"]),
        # Only the objectively-known verdict is pre-filled. Whether a lead that
        # actually talked said yes is The call, not the call log's.
        "Не дозвонился" if (s["outgoing"] and not s["reached"]) else "",
        chain_text(s["chain"]),
        note,
        json.dumps({
            "nudged": nudged,
            # What the script itself put in «Комментарий» this run. Next rebuild
            # compares against it to tell its own note from one Operator typed --
            # without it, a stale generated note looks like his work and sticks.
            "auto_note": note,
            "stats": {k: v for k, v in s.items() if k not in ("chain", "first_out",
                                                             "first_back", "last_contact")},
            "calls": [{"ts": c["ts"].isoformat(), "dir": "out" if c["type"] == OUTGOING
                       else "in" if c["type"] == INCOMING else "missed",
                       "dur": c["dur"]} for c in s["chain"]],
        }, ensure_ascii=False),
    ]


# ------------------------------------------------------------ sheet writing

def wtoken(env):
    from google.oauth2 import service_account
    import google.auth.transport.requests as gr
    key = Path(env.get("SHEETS_CREDENTIALS_JSON", ""))
    if not key.is_absolute():
        key = HERE / key
    if not key.exists():
        die(f"key file not found: {key}", "see README.md")
    creds = service_account.Credentials.from_service_account_file(
        str(key), scopes=[WRITE_SCOPE])
    creds.refresh(gr.Request())
    return creds.token


def guard(method, path, body):
    if method == "GET":
        return
    blob = urlparse.unquote(path) + json.dumps(body or {}, ensure_ascii=False)
    for t in GUARDED_TABS:
        if t in blob:
            die(f"refusing to write to «{t}»",
                "calls.py only ever writes «Звонки» and «Звонки-архив»")


def api(env, method, path, body=None, tries=4):
    import requests
    guard(method, path, body)
    url = f"{API}/{env['SHEET_ID']}{path}"
    hdr = {"Authorization": "Bearer " + wtoken(env), "Content-Type": "application/json"}
    last = None
    for attempt in range(tries):
        try:
            r = requests.request(method, url, headers=hdr, json=body, timeout=90)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                die(f"HTTP {r.status_code}: {r.text[:300]}",
                    "the service account needs Редактор on this sheet")
            if r.status_code == 400:
                # A malformed request never becomes well-formed on retry, and
                # burning four attempts on a 2 Mb/s link hides the real message.
                die(f"HTTP 400: {r.text[:400]}", "the request body is wrong, not the link")
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        if attempt < tries - 1:
            time.sleep(2 ** attempt)
    die(f"Sheets unreachable after {tries} tries -- {last}",
        "usually the VPN dropped. Retry before suspecting the code.")


def tab_ids(env):
    meta = api(env, "GET", "?fields=sheets.properties")
    return {s["properties"]["title"]: s["properties"] for s in meta.get("sheets", [])}


def archive(env, props, old_rows):
    """Copy the event log out before the tab is cleared. Append, never replace:
    re-running must not lose an earlier archive.

    Only the old event-log shape is worth archiving. On every rerun after the
    first, «Звонки» already holds a rebuild -- which this run is about to
    regenerate from the same source, so copying it would just grow the archive
    with duplicates of derived data."""
    if not old_rows:
        return
    head_row = [str(c).strip() for c in old_rows[0]]
    if "Хронология" in head_row or "JSON" in head_row:
        log("«Звонки» already rebuilt — nothing new to archive")
        return
    if ARCHIVE_TAB not in props:
        log(f"creating «{ARCHIVE_TAB}»")
        api(env, "POST", ":batchUpdate", {"requests": [{"addSheet": {"properties": {
            "title": ARCHIVE_TAB,
            "gridProperties": {"rowCount": max(1000, len(old_rows) + 50),
                               "columnCount": 10, "frozenRowCount": 1}}}}]})
        head = [old_rows[0]]
        body = old_rows[1:]
    else:
        head, body = [], old_rows[1:]
    stamp = [[f"— архив событий на {datetime.now(TZ).strftime('%d.%m.%Y %H:%M')} —"]]
    api(env, "POST", f"/values/{urlparse.quote(ARCHIVE_TAB)}!A1:append"
                     "?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
        {"values": head + stamp + body})
    # INSERT_ROWS pushes rows in at row 1, which is inside the frozen band, and
    # Sheets grows the band to match -- leaving the whole archive frozen. Pin it
    # back to the header afterwards.
    sid = tab_ids(env)[ARCHIVE_TAB]["sheetId"]
    api(env, "POST", ":batchUpdate", {"requests": [{"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"}}]})
    log(f"archived {len(body)} event rows to «{ARCHIVE_TAB}»")


def format_tab(env, sid):
    grey = {"red": 0.945, "green": 0.949, "blue": 0.957}
    green = {"red": 0.851, "green": 0.918, "blue": 0.827}
    red = {"red": 0.957, "green": 0.800, "blue": 0.800}
    amber = {"red": 0.988, "green": 0.910, "blue": 0.733}

    def band(col, text, colour):
        return {"addConditionalFormatRule": {"rule": {
            "ranges": [{"sheetId": sid, "startRowIndex": 1,
                        "startColumnIndex": col, "endColumnIndex": col + 1}],
            "booleanRule": {
                "condition": {"type": "TEXT_EQ",
                              "values": [{"userEnteredValue": text}]},
                "format": {"backgroundColor": colour}}}, "index": 0}}

    widths = {COL["№"]: 46, COL["Lead ID"]: 120, COL["Заявка"]: 120,
              COL["Телефон"]: 130, COL["Бизнес"]: 170, COL["Instagram"]: 150,
              COL["Креатив"]: 80, COL["Первый звонок"]: 120,
              COL["Через (мин)"]: 78, COL["Исходящих"]: 78,
              COL["Дозвонился"]: 90, COL["Разговоров"]: 88,
              COL["Общий разговор"]: 105, COL["Самый долгий"]: 100,
              COL["Перезвонил"]: 90, COL["Время перезвона"]: 120,
              COL["Пропущено от них"]: 100, COL["Последний контакт"]: 120,
              COL["Итог"]: 130, COL["Хронология"]: 420,
              COL["Комментарий"]: 220, COL["JSON"]: 40}

    reqs = [
        {"updateSheetProperties": {
            "properties": {"sheetId": sid, "gridProperties": {
                "frozenRowCount": 1, "frozenColumnCount": 2}},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}},
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": grey,
                "textFormat": {"bold": True, "fontSize": 10},
                "verticalAlignment": "MIDDLE",
                "wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,wrapStrategy)"}},
        # Chain and comment are prose; everything else stays on one line so the
        # grid keeps its shape when a lead has fourteen call attempts.
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": len(HEADER)},
            "cell": {"userEnteredFormat": {"wrapStrategy": "CLIP"}},
            "fields": "userEnteredFormat.wrapStrategy"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": COL["JSON"], "endIndex": COL["JSON"] + 1},
            "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}},
        {"setDataValidation": {
            "range": {"sheetId": sid, "startRowIndex": 1,
                      "startColumnIndex": COL["Итог"], "endColumnIndex": COL["Итог"] + 1},
            "rule": {"condition": {"type": "ONE_OF_LIST",
                                   "values": [{"userEnteredValue": o} for o in OUTCOMES]},
                     "showCustomUi": True, "strict": False}}},
        band(COL["Дозвонился"], "Да", green),
        band(COL["Дозвонился"], "Нет", red),
        band(COL["Перезвонил"], "Да", green),
        band(COL["Перезвонил"], "Пропущен", amber),
        band(COL["Итог"], "Договорились", green),
        band(COL["Итог"], "Отказ", red),
        band(COL["Итог"], "Не дозвонился", amber),
        # Speed-to-lead. Over an hour and the lead has moved on; that is the
        # single number this tab exists to make impossible to ignore.
        {"addConditionalFormatRule": {"rule": {
            "ranges": [{"sheetId": sid, "startRowIndex": 1,
                        "startColumnIndex": COL["Через (мин)"],
                        "endColumnIndex": COL["Через (мин)"] + 1}],
            "booleanRule": {
                "condition": {"type": "NUMBER_GREATER",
                              "values": [{"userEnteredValue": "60"}]},
                "format": {"backgroundColor": amber}}}, "index": 0}},
    ]
    for c, px in widths.items():
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": c, "endIndex": c + 1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    api(env, "POST", ":batchUpdate", {"requests": reqs})


def clear_rules(env, sid, props):
    """Conditional-format rules survive a values clear and stack up on every
    rerun. Drop them from the top; the list re-indexes as each one goes."""
    meta = api(env, "GET",
               f"?fields=sheets(properties(sheetId),conditionalFormats)")
    for s in meta.get("sheets", []):
        if s["properties"]["sheetId"] != sid:
            continue
        n = len(s.get("conditionalFormats", []))
        if n:
            api(env, "POST", ":batchUpdate", {"requests": [
                {"deleteConditionalFormatRule": {"sheetId": sid, "index": 0}}
                for _ in range(n)]})


def write_tab(env, props, rows):
    p = props[TAB]
    sid = p["sheetId"]
    grid = p.get("gridProperties", {})
    need_rows, need_cols = len(rows) + 20, len(HEADER)
    if grid.get("rowCount", 0) < need_rows or grid.get("columnCount", 0) < need_cols:
        api(env, "POST", ":batchUpdate", {"requests": [{"updateSheetProperties": {
            "properties": {"sheetId": sid, "gridProperties": {
                "rowCount": max(need_rows, grid.get("rowCount", 0)),
                "columnCount": max(need_cols, grid.get("columnCount", 0))}},
            "fields": "gridProperties.rowCount,gridProperties.columnCount"}}]})
    clear_rules(env, sid, props)
    api(env, "POST", f"/values/{urlparse.quote(TAB)}:clear", {})
    api(env, "PUT",
        f"/values/{urlparse.quote(TAB)}!A1?valueInputOption=RAW", {"values": rows})
    format_tab(env, sid)


# ------------------------------------------------------------------- output

def print_table(rows, unmatched, notes):
    head = ("№    заявка          телефон             первый звонок  через  "
            "исх  дозв  разгов  перезв  пропущ")
    print(head)
    print("-" * len(head))
    for r in rows[1:]:
        print(f"{r[0]:<4} {r[2][:5] + ' ' + r[2][11:16]:<15} {r[3]:<19} "
              f"{(r[7][:5] + ' ' + r[7][11:16]) if r[7] else '—':<14} "
              f"{str(r[8]):>5}  {str(r[9]):>3}  {r[10] or '—':<5} "
              f"{r[12] or '—':<7} {r[14] or '—':<7} {str(r[16]) or ''}")
    called = sum(1 for r in rows[1:] if r[9])
    reached = sum(1 for r in rows[1:] if r[10] == "Да")
    back = sum(1 for r in rows[1:] if r[14] == "Да")
    mins = [r[8] for r in rows[1:] if isinstance(r[8], int)]
    talk = sum(int(json.loads(r[21])["stats"]["talk_total"]) for r in rows[1:])
    print(f"\n{len(rows)-1} лидов · набрал {called} · поговорил {reached} · "
          f"перезвонили {back}")
    if mins:
        mins.sort()
        print(f"скорость до звонка: медиана {mins[len(mins)//2]} мин · "
              f"быстрее часа {sum(1 for m in mins if m <= 60)}/{len(mins)}")
    print(f"наговорено всего: {hhmmss(talk)}")
    for n in notes:
        print("  ! " + n)
    if unmatched:
        print(f"\n{len(unmatched)} звонков за период не совпали ни с одним лидом "
              "(личные / другие каналы)")


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml", required=True, help="SMS Backup & Restore call-log export")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--all", action="store_true", help="every lead in the sheet")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    env = crm.load_env()
    log("reading the sheet…")
    data = crm.fetch(env, [crm.LEADS_TAB, crm.CALLS_TAB, crm.CHAT_TAB])
    old_rows = data[crm.CALLS_TAB]
    leads = crm.build(data[crm.LEADS_TAB], old_rows)
    leads = [L for L in leads if not L["is_test"]]

    if not a.all:
        start = datetime.now() - timedelta(days=a.days)
        leads = [L for L in leads if L["ts"] and L["ts"] >= start]
    if not leads:
        die("no leads in that window", "widen with --days or --all")

    # Whether the bot ever nudged this lead is the one thing worth carrying
    # out of the old event log; it survives in the JSON column.
    nudged = {L["lead_id"]: L["nudged"] for L in leads}

    restored = apply_overrides(leads, load_overrides())
    if restored:
        log(f"phone-overrides.json filled {len(restored)} missing "
            f"{'phone' if len(restored) == 1 else 'phones'}: {', '.join(restored)}")

    log(f"reading {a.xml}…")
    calls = read_xml(a.xml)
    earliest = min(L["ts"] for L in leads) - timedelta(days=1)
    calls = [c for c in calls if c["ts"].replace(tzinfo=None) >= earliest]
    unmatched = attach(leads, calls)

    # Numbers he saved as a lead contact (L57, ...) that no row in «Заявки»
    # carries. Usually a lead whose phone never made it through the form and
    # that he chased another way -- worth surfacing, never worth guessing at.
    orphan_labels = sorted({
        (re.match(r"^L\d+", c["name"]).group(0), c["num"])
        for c in unmatched if re.match(r"^L\d+", c["name"])})

    human = keep_human(old_rows)
    kept = {"Итог": 0, "Комментарий": 0}
    notes, rows = [], [HEADER]
    for L in leads:
        s = stats(L)
        note = ""
        if L.get("_override_why"):
            note = ("телефон не записался формой, восстановлен вручную "
                    "(phone-overrides.json)")
        elif not L["phone"]:
            note = "телефон не записался при отправке формы"
            if orphan_labels:
                note += " · в журнале есть " + ", ".join(
                    f"«{lab}» {num}" for lab, num in orphan_labels) + " — это он?"
            notes.append(f"{L['lead_id']}: заявка без телефона")
        elif L["_siblings"]:
            other = L["_siblings"][0]
            where = fmt(other["ts"])
            note = ("дубль номера — тот же человек отправил форму дважды; "
                    + ("звонки сведены сюда, на первую заявку" if s["chain"]
                       else f"звонки сведены на первую заявку {where}"))
        elif not s["chain"]:
            notes.append(f"{L['phone']} — ни одного звонка в журнале")
        row = row_for(L, s, nudged.get(L["lead_id"], False), note)
        was_outcome, was_note = human.get(L["lead_id"], ("", ""))
        if was_outcome and was_outcome != row[COL["Итог"]]:
            kept["Итог"] += 1
            row[COL["Итог"]] = was_outcome
        if was_note and was_note != row[COL["Комментарий"]]:
            kept["Комментарий"] += 1
            row[COL["Комментарий"]] = was_note
        rows.append(row)

    for lab, num in orphan_labels:
        notes.append(f"контакт «{lab}» {num} есть в телефоне, но не в «Заявки»")
    if any(kept.values()):
        notes.append(f"сохранено из старой таблицы: «Итог» ×{kept['Итог']}, "
                     f"«Комментарий» ×{kept['Комментарий']}")

    print_table(rows, unmatched, notes)

    if a.dry_run:
        log("\n--dry-run: sheet untouched")
        return

    props = tab_ids(env)
    if TAB not in props:
        die(f"«{TAB}» not found in the sheet", "check SHEET_ID in .env")
    archive(env, props, old_rows)
    props = tab_ids(env)
    write_tab(env, props, rows)
    log(f"\n«{TAB}» rebuilt: {len(rows)-1} leads, one row each")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
