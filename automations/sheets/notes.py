#!/usr/bin/env python3
"""Put The hand-written call notes into the CRM, as data.

Why this exists
---------------
The richest thing anyone knows about these leads is not in the sheet. It is in
`leads-log.md`, next to this script -- what each person actually SAID on the phone, in
Turkmen and Russian, typed by hand after the call. «Звонки» knows a call lasted
four minutes; only this file knows it ended in «дорого, я подумаю».

This script parses that file, matches each note to a lead, classifies it, and
writes the «Заметки» tab. `crm.py` reads it back, so `/check-crm` answers
«кто ещё в игре», «сколько отвалилось по цене», «кто уже пробовал таргет»
instead of just counting rows.

THE MATCH -- read this before trusting a number
-----------------------------------------------
The log numbers leads L1..L61. Those are NOT the sheet's Lead IDs (which are
`L1784849508353`-style timestamps). `L{n}` is the n-th REAL lead in
chronological order -- test rows and duplicate submits excluded, exactly the
list `crm.py` calls "real leads".

That was verified, not assumed:
  L12 «Наргиля MAKEUP & HAIR»  -> real lead #12 = @ng_makeup_stylist
  L14 «стоматолог, не взял»    -> real lead #14 = @estetic_dental_ag, no answer
  L61 «Не взял»                -> real lead #61, the last one, no answer
and the counts line up: 61 real leads, highest note L61 (L5 was never written).

The mapping is positional, so it drifts if a lead is ever inserted BEFORE an
already-numbered one, or if a new duplicate is detected in the old range. Two
defences: the tab carries each lead's phone and business so Operator can eyeball a
row, and `note-overrides.json` pins any L-number to a Lead ID by hand:

    { "L5": "L1784875363313" }

WRITE ACCESS: writes «Заметки» and nothing else -- see GUARDED_TABS. The tab is
fully derived from the log file, so it is rewritten whole every run. Fix the
log, re-run; never edit the tab by hand.

Run:  python notes.py                 # parse the log, rewrite «Заметки»
      python notes.py --dry-run       # print the table, write nothing
      python notes.py --check         # just show the L-number -> lead match
      python notes.py --json          # structured, for computing on
      python notes.py --file PATH     # a different log file
"""
import argparse
import json
import re
import sys
import time
import urllib.parse as urlparse
from datetime import datetime
from pathlib import Path

import crm  # sibling: load_env, fetch, build, cell. crm.py is read-only by design.

HERE = Path(__file__).parent
API = "https://sheets.googleapis.com/v4/spreadsheets"
WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
LOG_FILE = HERE / "leads-log.md"
OVERRIDES = HERE / "note-overrides.json"

TAB = "Заметки"
# Everything else here is truth someone else owns: the webhook appends «Заявки»
# and «Чат-лог», calls.py rebuilds «Звонки», profiles.py owns «Профили».
GUARDED_TABS = (crm.LEADS_TAB, crm.CALLS_TAB, crm.CHAT_TAB, "Профили",
                "Звонки-архив")

HEADER = [
    "Lead ID", "№", "телефон", "бизнес", "категория", "возражение",
    "перезвонить", "заметка", "оригинал", "обновлено",
]
LAST_COL = "J"

# ---------------------------------------------------------------- classifier
#
# Keyword buckets over the Russian «Перевод / Смысл» line. Everything below is
# a phrase that actually appears in the log -- this is a reader for one file,
# not a general intent model, and it is meant to be extended by pasting in the
# next real phrase rather than by getting cleverer.

NO_ANSWER = ("не взял", "не взяла", "не дозвон", "номер отключен",
             "не поднял", "трубку не")
NOT_A_LEAD = ("ошибл", "случайно отправил", "дети", "не оставлял")
NOT_ICP = ("не наша целевая", "не готова масштаб", "не готов масштаб",
           "не сможет отправить деньги", "другого велаята")
INTERESTED = ("давайте попробуем", "давай попробуем", "готова попробовать",
              "готов попробовать", "обсудим и попробуем", "попробуем")
CONFUSED = ("не понял", "не поняла", "непонятке")
THINKING = ("подумаю", "подумает", "думает", "размышляет", "посоветуюсь",
            "посовещ", "посоветуется", "скажу сестре", "напарник", "с мужем",
            "посмотреть ваши работы", "подумать")
POSTPONED = ("перезвоните через", "через месяц", "через 4 дня", "позже")
WILL_CALL = ("перезвоню", "перезвонит", "созвонюсь", "свяжусь", "свяжет",
             "позвоню", "позвонит", "жаңлаш")
BUSY = ("не могу говорить", "на работе", "занят")
# Answered once, then went silent -- we sent something and nothing came back.
# A different lead from «думает»: the ball was already in their court.
GHOSTED = ("пропал", "ответов не получил", "ответа не получил", "не ответил")

# priority order when several buckets match the same note
BUCKETS = [
    ("не заявка", NOT_A_LEAD),
    ("не ЦА", NOT_ICP),
    ("интерес", INTERESTED),
    ("пропал", GHOSTED),
    ("не понял", CONFUSED),
    ("думает", THINKING),
    ("отложил", POSTPONED),
    ("перезвонит сам", WILL_CALL),
    ("не поговорили", BUSY),
]

# What they pushed back with. Independent of the category and multi-valued --
# «дорого» and «уже пробовал таргет» are usually the same person.
OBJECTIONS = [
    ("цена", ("дорого", "дороговат", "гымм")),
    ("уже пробовал таргет", ("сама запуска", "сам запуска", "делать таргетинг",
                             "какаджан", "из за таргетолог", "из-за таргетолог",
                             "таргетолог")),
    ("уже есть решение", ("уже есть сайт", "сайт есть", "воронка готова",
                          "тикток есть", "саит есть")),
    ("не понял оффер", ("не понял", "не поняла", "непонятке")),
    ("недоверие", ("блокировал", "посмотреть ваши работы")),
    ("регион / оплата", ("не сможет отправить деньги", "другого велаята")),
]

# A lead worth another call. «нет ответа» stays да on purpose -- an unanswered
# phone is the cheapest thing on this list to retry.
DEAD = ("не заявка", "не ЦА")


def die(msg, fix=""):
    print(f"FAIL  {msg}", file=sys.stderr)
    if fix:
        print(f"      fix: {fix}", file=sys.stderr)
    sys.exit(1)


def log(msg):
    print(msg, flush=True)


# --------------------------------------------------------------- log parsing

ENTRY_RE = re.compile(r"\*\*L(\d+)\*\*")


def clean(s):
    """The log is hand-typed markdown: unbalanced backticks, stray asterisks,
    an occasional `*(transliteration)*`. Strip the markup, keep the words."""
    s = re.sub(r"\*\(([^)]*)\)\*", r"(\1)", s)
    s = s.replace("`", "").replace("**", "").replace("*", "")
    return " ".join(s.split()).strip(" .")


def parse_log(path):
    """-> [{'n': 12, 'original': '...', 'meaning': '...'}] in file order."""
    if not path.exists():
        die(f"no log file at {path}",
            "pass --file, or check LOG_FILE -- it should sit next to this script")
    text = path.read_text(encoding="utf-8")

    # Split on the L-headers rather than parsing bullets: several entries are
    # missing a closing backtick or a bullet marker, and a strict parser drops
    # exactly the notes that took the longest to write.
    marks = list(ENTRY_RE.finditer(text))
    if not marks:
        die("no **L<number>** entries found in the log",
            "the parser keys on «* **L12**» headers -- keep that shape")

    out = []
    for i, m in enumerate(marks):
        body = text[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        orig = field(body, "Оригинал")
        mean = field(body, "Перевод / Смысл") or field(body, "Смысл")
        # Strip the «L12.» the original line repeats -- it is the header again.
        orig = re.sub(r"^L\d+\s*[.:]?\s*", "", orig)
        out.append({"n": int(m.group(1)), "original": orig,
                    "meaning": mean or orig})
    return out


def field(body, label):
    m = re.search(rf"{re.escape(label)}\s*:?\s*\*\*\s*(.*?)(?=\n\s*\*\s|\Z)",
                  body, re.S)
    if not m:
        m = re.search(rf"{re.escape(label)}\s*:\s*(.*?)(?=\n\s*\*\s|\Z)", body, re.S)
    return clean(m.group(1)) if m else ""


# ------------------------------------------------------------- classification

def last_hit(text, words):
    """Where the LAST of these phrases appears, or -1. Position matters: «не
    взял трубку сначала, потом посовещавшись завтра позвоню» is a callback, not
    a missed call, and only the ORDER of the two signals says so."""
    return max((text.rfind(w) for w in words), default=-1)


def classify(meaning):
    t = meaning.lower()

    # «не взял» wins only when nothing else happened after it. That single rule
    # is what separates L7 («перезвоните через час» — перезвонил, не взяла →
    # нет ответа) from L27 (не взял сначала, потом «завтра позвоню» → думает).
    na = last_hit(t, NO_ANSWER)
    other = max((last_hit(t, words) for _, words in BUCKETS), default=-1)
    if na >= 0 and na > other:
        return "нет ответа"

    for name, words in BUCKETS:
        if any(w in t for w in words):
            return name
    return "прочее"


def objections(meaning):
    t = meaning.lower()
    return ", ".join(name for name, words in OBJECTIONS
                     if any(w in t for w in words))


# ------------------------------------------------------------------ matching

def load_overrides():
    if not OVERRIDES.exists():
        return {}
    try:
        raw = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"{OVERRIDES.name} is not valid JSON: {e}")
    return {str(k).upper(): str(v).strip()
            for k, v in raw.items() if v and not str(k).startswith("_")}


def real_leads(env):
    """The same list `crm.py` calls "real leads", in the same order: no test
    rows, no duplicate submits, oldest first. The note numbering indexes THIS."""
    data = crm.fetch(env, [crm.LEADS_TAB, crm.CALLS_TAB])
    leads = crm.build(data[crm.LEADS_TAB], data[crm.CALLS_TAB])
    return [L for L in leads if not L["is_test"] and not L["is_duplicate_phone"]]


def match(entries, leads, overrides):
    """Attach a lead to every note. Unmatched notes are kept and reported --
    silently dropping one loses the only record of that conversation."""
    by_id = {L["lead_id"]: L for L in leads}
    highest = max(e["n"] for e in entries)
    if highest > len(leads):
        die(f"the log goes up to L{highest} but the sheet has only "
            f"{len(leads)} real leads",
            "the positional match is not safe. Either «Заявки» lost rows, or "
            "the log is ahead of the sheet -- check before writing anything.")

    for e in entries:
        pin = overrides.get(f"L{e['n']}")
        if pin:
            e["lead"] = by_id.get(pin)
            e["how"] = "pinned" if e["lead"] else "pinned to a missing Lead ID"
        else:
            e["lead"] = leads[e["n"] - 1] if e["n"] <= len(leads) else None
            e["how"] = "positional"
    return entries


# ------------------------------------------------------------- sheet writing

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
    """The credential can edit every tab. This script owns exactly one, and the
    refusal lives in code rather than in whoever edits this file next."""
    if method == "GET":
        return
    blob = urlparse.unquote(path) + json.dumps(body or {}, ensure_ascii=False)
    for t in GUARDED_TABS:
        if t in blob:
            die(f"refusing to write to «{t}» — not this script's tab",
                "notes.py only ever writes «Заметки»")


def sheets_call(env, method, path, body=None, tries=4):
    import requests
    guard(method, path, body)
    url = f"{API}/{env['SHEET_ID']}{path}"
    hdr = {"Authorization": "Bearer " + wtoken(env),
           "Content-Type": "application/json"}
    last = None
    for attempt in range(tries):
        try:
            r = requests.request(method, url, headers=hdr, json=body, timeout=90)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                die(f"HTTP {r.status_code}: {r.text[:300]}",
                    "the service account needs Редактор on the sheet — "
                    "voronka-reader@voronka-data.iam.gserviceaccount.com")
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as exc:  # noqa: BLE001 -- VPN drops surface many ways
            last = f"{type(exc).__name__}: {exc}"
        if attempt < tries - 1:
            time.sleep(2 ** attempt)
    die(f"Sheets unreachable after {tries} tries -- {last}",
        "usually the VPN dropped. Retry before suspecting the code.")


def ensure_tab(env):
    meta = sheets_call(env, "GET", "?fields=sheets.properties")
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == TAB:
            return s["properties"]["sheetId"]
    log(f"creating tab «{TAB}»")
    res = sheets_call(env, "POST", ":batchUpdate", {"requests": [{"addSheet": {
        "properties": {"title": TAB, "gridProperties": {
            "rowCount": 1000, "columnCount": len(HEADER),
            "frozenRowCount": 1}}}}]})
    sid = res["replies"][0]["addSheet"]["properties"]["sheetId"]
    sheets_call(env, "POST", ":batchUpdate", {"requests": [
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}}
        for i, px in ((0, 140), (1, 40), (2, 130), (3, 150), (4, 120),
                      (5, 160), (6, 90), (7, 420), (8, 320), (9, 120))
    ]})
    return sid


def rows_for(entries):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    rows = []
    for e in sorted(entries, key=lambda x: x["n"]):
        L = e["lead"]
        cat = classify(e["meaning"])
        rows.append([
            L["lead_id"] if L else "",
            e["n"],
            (L["phone"] if L else "") or "",
            ((L["chat"].get("business") if L else "") or "")[:60],
            cat,
            objections(e["meaning"]),
            "нет" if cat in DEAD else "да",
            e["meaning"][:900],
            e["original"][:900],
            now,
        ])
    return rows


def write(env, sid, rows):
    # The tab is derived from the log file in full, so it is replaced in full.
    # An append would double every note the next time the log grows.
    sheets_call(env, "POST",
                f"/values/{urlparse.quote(TAB)}!A2:{LAST_COL}:clear", {})
    sheets_call(env, "PUT",
                f"/values/{urlparse.quote(TAB)}!A1:{LAST_COL}1"
                "?valueInputOption=RAW", {"values": [HEADER]})
    if rows:
        sheets_call(env, "PUT",
                    f"/values/{urlparse.quote(TAB)}!A2:{LAST_COL}{len(rows) + 1}"
                    "?valueInputOption=RAW", {"values": rows})
    log(f"wrote {len(rows)} note(s) to «{TAB}»")


# ------------------------------------------------------------------- driver

def print_table(entries):
    print(f"{'№':<4} {'Lead ID':<16} {'телефон':<18} {'категория':<16} "
          f"{'возражение':<22} заметка")
    print("-" * 130)
    for e in sorted(entries, key=lambda x: x["n"]):
        L = e["lead"]
        print(f"L{e['n']:<3} {(L['lead_id'] if L else '—'):<16} "
              f"{((L['phone'] if L else '') or '—'):<18} "
              f"{classify(e['meaning']):<16} "
              f"{(objections(e['meaning']) or '—')[:22]:<22} "
              f"{e['meaning'][:60]}")

    cats = {}
    for e in entries:
        c = classify(e["meaning"])
        cats[c] = cats.get(c, 0) + 1
    print("\n  по категориям")
    for k, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {n:>3}  {k}")
    objs = {}
    for e in entries:
        for o in filter(None, objections(e["meaning"]).split(", ")):
            objs[o] = objs.get(o, 0) + 1
    if objs:
        print("\n  возражения")
        for k, n in sorted(objs.items(), key=lambda x: -x[1]):
            print(f"    {n:>3}  {k}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(LOG_FILE))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="show the L-number -> lead match and stop")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")

    env = crm.load_env()
    entries = parse_log(Path(a.file))
    leads = real_leads(env)
    entries = match(entries, leads, load_overrides())

    missing = [L for i, L in enumerate(leads, 1)
               if i not in {e["n"] for e in entries}]
    # stderr under --json: this line is for a human, and one stray word on
    # stdout makes the whole payload unparseable for whatever piped it.
    print(f"{len(entries)} note(s) · {len(leads)} real lead(s) · "
          f"{len(missing)} lead(s) with no note",
          file=sys.stderr if a.json else sys.stdout, flush=True)

    if a.check:
        for e in sorted(entries, key=lambda x: x["n"]):
            L = e["lead"]
            print(f"L{e['n']:<3} -> {(L['lead_id'] if L else 'НЕ НАЙДЕН'):<16} "
                  f"{((L['phone'] if L else '') or '—'):<18} "
                  f"{((L['chat'].get('business') if L else '') or '—')[:22]:<22} "
                  f"{e['meaning'][:44]}")
        if missing:
            print("\nno note yet:")
            for L in missing:
                print(f"     {L['lead_id']:<16} {L['phone'] or '—':<18} "
                      f"{(L['chat'].get('business') or '—')[:30]}")
        return

    if a.json:
        print(json.dumps([{
            "n": e["n"], "lead_id": e["lead"]["lead_id"] if e["lead"] else None,
            "phone": e["lead"]["phone"] if e["lead"] else None,
            "match": e["how"],
            "category": classify(e["meaning"]),
            "objections": [o for o in objections(e["meaning"]).split(", ") if o],
            "note": e["meaning"], "original": e["original"],
        } for e in sorted(entries, key=lambda x: x["n"])],
            ensure_ascii=False, indent=2))
        return

    rows = rows_for(entries)
    if a.dry_run:
        print_table(entries)
        log("\n-- dry run, sheet untouched.")
        return

    sid = ensure_tab(env)
    write(env, sid, rows)
    print_table(entries)


if __name__ == "__main__":
    main()
