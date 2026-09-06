#!/usr/bin/env python3
"""Enrich CRM leads with the facts about their Instagram account.

The lead types their handle into the landing chat («Ваш Instagram-профиль»).
This script takes that handle, pulls the account through Meta's
`business_discovery`, derives the numbers that decide how the account gets
sold to, and writes a row into the «Профили» tab of the CRM sheet.

WHAT IT WRITES, AND WHY THOSE FIELDS:

  последний пост / постов/мес   The strongest qualifier there is. A shop that
                                hasn't posted in four months is a different
                                sale ("we'll run the account") from one posting
                                daily ("we'll bring you traffic"). Today Operator
                                learns this four minutes into a call.
  медиана лайков / ER%          Median, never mean -- one post that took off
                                invents engagement the account doesn't have.
                                Read against follower count it catches bought
                                audiences: 6k followers on 30 likes is exactly
                                why they get no заявки.
  доля Reels                    What format they already work in.
  данные (JSON)                 stats + per-post {permalink, type, likes,
                                comments, views, caption}. Captions are the
                                richest signal in the whole row -- what they
                                sell, whether prices and a CTA are there, what
                                language they write in. No number holds that.

The columns are for The eyes; the `данные` cell is for an agent, and crm.py
unpacks it straight back into the lead record.

WHY NOT A SCREENSHOT: an earlier version composited the profile grid into an
image. Pixels buy an agent nothing a counter doesn't say better, and the grid
cost twelve image downloads per lead on a 2-4 Mb/s VPN. `permalink` replaces
it -- it never expires (unlike media_url), so one specific post can be pulled
on demand instead of twelve up front. `--grid` still builds the image when the
visual actually matters.

WHY A SEPARATE TAB: «Заявки» is an append-only event log written by a webhook
-- one row per submit, per chat answer. Per-lead enrichment does not belong on
an event row. «Профили» is keyed by Lead ID, exactly how crm.py already joins
«Звонки».

WRITE ACCESS: this is the ONLY script here that writes. It needs the service
account shared as Редактор and takes the full `spreadsheets` scope. crm.py
keeps `spreadsheets.readonly` and physically cannot write. Nothing here ever
touches «Заявки» or «Звонки» -- see GUARDED_TABS.

Run:  python profiles.py                 # leads of the last 7 days missing a profile
      python profiles.py --days 30
      python profiles.py --all           # every lead that ever gave a handle
      python profiles.py --refresh       # re-fetch leads already in «Профили»
      python profiles.py --handle x      # one account, ad hoc, no lead needed
      python profiles.py --dry-run       # print what it would write, write nothing
      python profiles.py --grid          # also build + upload the profile grid
      python profiles.py --json          # everything, structured, for computing on
"""
import argparse
import importlib.util
import io
import json
import re
import sys
import time
import urllib.parse as urlparse
from datetime import datetime, timedelta
from pathlib import Path

import crm  # sibling: load_env, fetch, build, parse_dt, cell

HERE = Path(__file__).parent
API = "https://sheets.googleapis.com/v4/spreadsheets"
WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
POSTER_ENV = HERE.parent / "ig-poster" / ".env"
OVERRIDES = HERE / "handle-overrides.json"

TAB = "Профили"
# Tabs this script must never write to, whatever a future flag says. «Заявки»
# and «Звонки» are truth for заявки; the credential can now technically edit
# them, so the refusal lives in code rather than in a habit.
GUARDED_TABS = (crm.LEADS_TAB, crm.CALLS_TAB, crm.CHAT_TAB)

HEADER = [
    "Lead ID", "@профиль", "подписчики", "подписки", "постов", "последний пост",
    "постов/мес", "медиана лайков", "ER%", "доля Reels", "имя", "био", "сайт",
    "статус", "обновлено", "скрин", "url скрина", "данные",
]
COL_JSON = 17         # R -- the machine column: stats + per-post rows
COL_SCREEN = 15       # P -- =IMAGE(), only filled by --grid
COL_URL = 16          # Q
LAST_COL = "R"

# Twelve posts, not six: the stats below are medians and a rate, and six
# samples make both noise. One extra field on the same call costs nothing.
MEDIA_LIMIT = 12
# IG captions run to 2200 chars. Twelve of them can approach the 50k-per-cell
# ceiling, and the tail of a caption never carries the signal -- what they
# sell, whether prices and a CTA are there, is in the opening lines.
CAPTION_CHARS = 600

# Instagram usernames are ASCII letters, digits, dot, underscore, <=30 chars.
# Anything else in that chat field is prose («нет», «студия интерьеров»), not
# a handle, and must not be sent to the Graph API as one.
HANDLE_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")

# «нет Instagram», «yok», «no» -- the lead is declining, and every word left in
# the string after that is noise, not a username.
NEGATIVE_RE = re.compile(r"(^|\s)(нет|ныт|жок|ýok|yok|no|none|yoq)(\s|$)", re.I)
# Words that are real Instagram accounts but are never THIS lead's account.
BLOCKED = {"instagram", "instagramm", "insta", "inst", "ig", "reklama"}

GRID_W = 640
CELL = 210
GAP = 5
HEAD_H = 140


# ------------------------------------------------------------------ helpers

def die(msg, fix=""):
    print(f"FAIL  {msg}", file=sys.stderr)
    if fix:
        print(f"      fix: {fix}", file=sys.stderr)
    sys.exit(1)


def log(msg):
    print(msg, flush=True)


def load_module(path, name):
    """Import a script by path. ga4/, meta-ads/ and ig-insights/ all ship a
    `report.py`; importing by name would pick whichever landed on sys.path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_env_file(path):
    d = {}
    if not path.exists():
        return d
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def norm_handle(raw):
    """Chat answers arrive as @name, a full URL, or prose. Return a bare
    username, or "" if what the lead typed was never a handle."""
    if not raw:
        return ""
    s = str(raw).strip()
    if "instagram.com" in s.lower():
        path = urlparse.urlparse(s if "//" in s else "//" + s).path
        s = path.strip("/").split("/")[0]
    s = s.split("?")[0].rstrip("/")
    s = "".join(s.split()).strip("@").lower()
    return s if HANDLE_RE.match(s) else ""


def ovkey(raw):
    """Key for handle-overrides.json: the raw chat answer, loosely normalised
    so a stray capital or double space in the sheet still matches the file."""
    return " ".join(str(raw or "").strip().lstrip("@").lower().split())


def load_overrides():
    """Character-level typos («owadanexpress» for «owadanexpresss») cannot be
    generated -- only a human who searched Instagram knows the answer. This
    file is where those answers are kept so they survive a re-run."""
    if not OVERRIDES.exists():
        return {}
    try:
        raw = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"{OVERRIDES.name} is not valid JSON: {e}")
    return {ovkey(k): str(v).strip().lstrip("@").lower()
            for k, v in raw.items() if v and not k.startswith("_")}


def candidates(raw):
    """Handles worth trying for one chat answer, best guess first.

    Everything here is a repair for a mistake we have actually seen in the
    sheet, not a general fuzzy search -- Meta has no username-search endpoint,
    so a wrong guess costs one cheap read and nothing else."""
    s = str(raw or "").strip()
    if "instagram.com" in s.lower():
        s = urlparse.urlparse(s if "//" in s else "//" + s).path.strip("/").split("/")[0]
    # Lowercase is not cosmetic: business_discovery is CASE-SENSITIVE even
    # though Instagram handles are not. «Lmd_brend_shop_tm» → Invalid user id,
    # «lmd_brend_shop_tm» → 32,820 followers. Verified 2026-07-28.
    # strip("@") both ends, not lstrip: «aynaorazmyradowa@» is a real answer.
    s = s.split("?")[0].rstrip("/").strip().strip("@").lower()
    if not s:
        return []

    # «нет Instagram» is an ANSWER, not a handle. An earlier version tokenised
    # it, found the word «instagram», and wrote Instagram Inc.'s own account —
    # 685 million followers — into five leads' rows. Refuse the whole string.
    if NEGATIVE_RE.search(s):
        return []

    out = []

    def add(h):
        # Strip «@» and edge dots only. A TRAILING UNDERSCORE IS LEGAL and
        # common here -- «mira_kapriznaya_», «inleilashfiller_». Stripping it
        # silently turned four working handles into Invalid user id.
        h = h.strip("@.")
        if HANDLE_RE.match(h) and h not in BLOCKED and h not in out:
            out.append(h)

    # The handle is often already sitting inside prose: «Принимаю товары из
    # Китая. " GunChina_tm». A token only counts as one when it carries a `_`
    # or a `.`; on plain length, ordinary words qualify («atash», «avezow»)
    # and each one is a lookup that can land on a stranger's real account.
    for tok in re.split(r"\s+", s):
        tok = tok.strip('.,;:"\'()[]')
        if HANDLE_RE.match(tok) and ("_" in tok or "." in tok):
            add(tok)

    words = s.split()
    joined, under, dotted = "".join(words), "_".join(words), ".".join(words)
    for base in (joined, under, dotted):
        add(base)
        add(base.replace(".", "_"))     # globalwork.tm → globalwork_tm
        add(base.replace("_", "."))     # bmwshoptm-style → dotted
    for base in (joined, under):
        add(base + "_tm")               # the suffix leads drop most often
    # Eight is the ceiling: past that we are inventing accounts, not repairing
    # a typo, and every extra call is a read against a handle nobody typed.
    return out[:8]


def resolve_profile(raw, overrides):
    """Try the override, then the candidates, stop at the first that resolves.
    Returns (profile, handle_used, tried)."""
    ov = overrides.get(ovkey(raw))
    order = ([ov] if ov else []) + [c for c in candidates(raw) if c != ov]
    tried = []
    for h in order:
        prof = fetch_profile(h)
        tried.append(h)
        if prof.get("rate_limited"):
            return prof, h, tried       # stop dead; caller aborts the run
        if not prof.get("error"):
            return prof, h, tried
    return ({"error": "не найден" if tried else "не похоже на ник"},
            order[0] if order else "", tried)


# ------------------------------------------------------- instagram profile

def fetch_profile(username):
    """business_discovery: any PUBLIC business/creator account. A personal or
    private account returns an error, and that is a fact about the lead's
    setup, not a bug -- it lands in the статус column as «не бизнес-аккаунт»."""
    ig = load_module(HERE.parent / "ig-insights" / "report.py", "ig_report")
    token, _page_tok, ig_id = ig.load_env()
    # view_count is the prize here: Meta blocks it on OUR media (§2B in
    # CAPABILITIES.md) but hands it over through business_discovery. We can see
    # a prospect's real Reels reach when we can't see our own.
    fields = (
        f"business_discovery.username({username})"
        "{username,name,biography,website,followers_count,follows_count,"
        "media_count,profile_picture_url,"
        f"media.limit({MEDIA_LIMIT})"
        "{id,media_type,media_product_type,media_url,thumbnail_url,permalink,"
        "like_count,comments_count,view_count,caption,timestamp}}"
    )
    r = ig.get(ig_id, token, {"fields": fields})
    e = ig.err(r)
    if e:
        # «(#4) Application request limit reached» is the app's hourly budget,
        # not a verdict on this account. It MUST NOT be written to the sheet:
        # a transient limit once overwrote 30 good rows with «не найден».
        if "request limit" in str(e).lower() or "#4" in str(e):
            return {"error": str(e), "rate_limited": True}
        # code 110 / "User is not a business account" is the common one.
        return {"error": str(e)}
    bd = r.get("business_discovery")
    if not bd:
        return {"error": "no business_discovery in response"}
    return bd


def median(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else None


def post_ts(m):
    """business_discovery timestamps are ISO with a +0000 offset."""
    try:
        return datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
    except (KeyError, TypeError, ValueError):
        return None


def derive_stats(prof):
    """The facts that change how Operator sells, computed from the last posts.

    Nothing here is on the profile object -- Meta returns raw counters and we
    turn them into the four things that actually decide the pitch."""
    media = prof.get("media", {}).get("data") or []
    followers = prof.get("followers_count") or 0
    st = {"posts_sampled": len(media), "last_post": None, "days_since_last": None,
          "posts_per_month": None, "median_likes": None, "median_views": None,
          "er_pct": None, "reels_share_pct": None}
    stamps = sorted(t for t in (post_ts(m) for m in media) if t)
    if not media or not stamps:
        return st

    newest = stamps[-1]
    st["last_post"] = newest.strftime("%d.%m.%Y")
    st["days_since_last"] = (datetime.now(newest.tzinfo) - newest).days

    # Cadence over the sampled window, not over the account's whole life --
    # what they do NOW is the question, not what they did in 2023.
    span = (newest - stamps[0]).days
    if span > 0 and len(stamps) > 1:
        st["posts_per_month"] = round(len(stamps) / (span / 30.0), 1)

    # Median, never mean: one post that took off rewrites a mean and invents
    # engagement the account does not have.
    st["median_likes"] = median([m.get("like_count") or 0 for m in media])
    views = [m["view_count"] for m in media if isinstance(m.get("view_count"), int)]
    st["median_views"] = median(views)
    if followers:
        inter = [(m.get("like_count") or 0) + (m.get("comments_count") or 0)
                 for m in media]
        # Read this against followers, not alone: 6k followers on 30 likes is a
        # bought audience, and that is the whole reason they get no заявки.
        st["er_pct"] = round(median(inter) / followers * 100, 2)

    reels = sum(1 for m in media
                if m.get("media_product_type") == "REELS"
                or m.get("media_type") in ("VIDEO", "REELS"))
    st["reels_share_pct"] = round(reels / len(media) * 100)
    return st


def pack_posts(prof):
    """Per-post rows for the machine column. `permalink` is what makes the
    pixels optional -- it never expires, unlike media_url, so a specific post
    can be pulled later on demand instead of downloading twelve up front."""
    out = []
    for m in prof.get("media", {}).get("data") or []:
        cap = " ".join((m.get("caption") or "").split())
        out.append({
            "permalink": m.get("permalink"),
            "type": m.get("media_product_type") or m.get("media_type"),
            "ts": (m.get("timestamp") or "")[:10],
            "likes": m.get("like_count"), "comments": m.get("comments_count"),
            "views": m.get("view_count"),
            "caption": cap[:CAPTION_CHARS] + ("…" if len(cap) > CAPTION_CHARS else ""),
        })
    return out


def download(url, tries=3):
    import requests
    last = None
    for attempt in range(tries):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                return r.content
            last = f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001 -- VPN drops surface many ways
            last = f"{type(exc).__name__}: {exc}"
        if attempt < tries - 1:
            time.sleep(2 ** attempt)
    log(f"    skip image ({last})")
    return None


def build_grid(prof):
    """Avatar + header line + up to six post thumbnails, one PNG.

    This is the thing that makes the cell worth looking at: a handle and a
    follower count don't tell Operator whether the account is worth a call, and the
    avatar alone is a 40px circle. The grid is what a profile page looks like."""
    from PIL import Image, ImageDraw, ImageFont

    media = (prof.get("media", {}).get("data") or [])[:6]
    rows = max(1, (len(media) + 2) // 3) if media else 0
    grid_h = rows * CELL + (rows + 1) * GAP if rows else 0
    canvas = Image.new("RGB", (GRID_W, HEAD_H + grid_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    def font(size, bold=False):
        name = "arialbd.ttf" if bold else "arial.ttf"
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            return ImageFont.load_default()

    # avatar, circle-masked
    av_url = prof.get("profile_picture_url")
    if av_url:
        blob = download(av_url)
        if blob:
            try:
                av = Image.open(io.BytesIO(blob)).convert("RGB").resize((100, 100))
                mask = Image.new("L", (100, 100), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 99, 99), fill=255)
                canvas.paste(av, (20, 20), mask)
            except Exception as exc:  # noqa: BLE001
                log(f"    avatar unreadable: {exc}")

    x = 140
    draw.text((x, 26), (prof.get("name") or "")[:38], font=font(22, True), fill=(17, 17, 17))
    draw.text((x, 58), "@" + prof.get("username", ""), font=font(18), fill=(90, 90, 90))
    stats = (f"{prof.get('followers_count', 0):,} подписчиков   ·   "
             f"{prof.get('media_count', 0):,} постов").replace(",", " ")
    draw.text((x, 84), stats, font=font(17), fill=(17, 17, 17))
    bio = " ".join((prof.get("biography") or "").split())
    if bio:
        draw.text((x, 110), bio[:52] + ("…" if len(bio) > 52 else ""),
                  font=font(15), fill=(120, 120, 120))
    draw.line((0, HEAD_H - 1, GRID_W, HEAD_H - 1), fill=(230, 230, 230))

    for i, m in enumerate(media):
        # VIDEO/REELS media_url is the video file itself -- PIL cannot open it.
        url = (m.get("thumbnail_url")
               if m.get("media_type") in ("VIDEO", "REELS") else None) or m.get("media_url")
        if not url:
            continue
        blob = download(url)
        if not blob:
            continue
        try:
            im = Image.open(io.BytesIO(blob)).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            log(f"    thumb unreadable: {exc}")
            continue
        # square centre-crop, the way the profile grid shows them
        s = min(im.size)
        im = im.crop(((im.width - s) // 2, (im.height - s) // 2,
                      (im.width + s) // 2, (im.height + s) // 2)).resize((CELL, CELL))
        col, row = i % 3, i // 3
        canvas.paste(im, (GAP + col * (CELL + GAP), HEAD_H + GAP + row * (CELL + GAP)))

    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=88)
    return out.getvalue()


def upload_imgbb(blob, name):
    """Permanent public URL. The Meta CDN link this replaces expires in days."""
    import requests
    key = parse_env_file(POSTER_ENV).get("IMGBB_API_KEY", "")
    if not key:
        die("IMGBB_API_KEY empty in ../ig-poster/.env",
            "the poster already uses this key -- check that file, don't make a new one")
    last = None
    for attempt in range(4):
        try:
            r = requests.post("https://api.imgbb.com/1/upload",
                              params={"key": key},
                              files={"image": (name, blob, "image/jpeg")},
                              timeout=120)
            data = r.json()
            if data.get("success"):
                return data["data"]["url"]
            last = str(data)[:200]
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        if attempt < 3:
            time.sleep(2 ** attempt)
    log(f"    imgbb failed after 4 tries: {last}")
    return ""


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
    """The credential can edit every tab. Each writer here owns exactly one --
    this one owns «Профили», `calls.py` owns «Звонки» -- so the refusal is
    enforced in code rather than left to whoever edits it next."""
    if method == "GET":
        return
    blob = urlparse.unquote(path) + json.dumps(body or {}, ensure_ascii=False)
    for t in GUARDED_TABS:
        if t in blob:
            die(f"refusing to write to «{t}» — not this script's tab",
                "profiles.py only ever writes «Профили»")


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
                    "the service account is still Читатель. Share the sheet with "
                    "voronka-reader@voronka-data.iam.gserviceaccount.com as "
                    "Редактор — this script writes.")
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        if attempt < tries - 1:
            time.sleep(2 ** attempt)
    die(f"Sheets unreachable after {tries} tries -- {last}",
        "usually the VPN dropped. Retry before suspecting the code.")


def ensure_tab(env):
    """Create «Профили» with a frozen header if it isn't there. Returns sheetId."""
    meta = sheets_call(env, "GET", "?fields=sheets.properties")
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == TAB:
            return s["properties"]["sheetId"]
    log(f"creating tab «{TAB}»")
    res = sheets_call(env, "POST", ":batchUpdate", {"requests": [{"addSheet": {
        "properties": {"title": TAB, "gridProperties": {
            "rowCount": 1000, "columnCount": len(HEADER), "frozenRowCount": 1}}}}]})
    sid = res["replies"][0]["addSheet"]["properties"]["sheetId"]
    sheets_call(env, "PUT",
                f"/values/{urlparse.quote(TAB)}!A1:{LAST_COL}1?valueInputOption=RAW",
                {"values": [HEADER]})
    sheets_call(env, "POST", ":batchUpdate", {"requests": [
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": COL_SCREEN, "endIndex": COL_SCREEN + 1},
            "properties": {"pixelSize": 190}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": COL_URL, "endIndex": COL_URL + 1},
            "properties": {"pixelSize": 240}, "fields": "pixelSize"}},
        # The JSON cell is for crm.py, not for reading. Keep it narrow so it
        # doesn't push everything human off the screen.
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": COL_JSON, "endIndex": COL_JSON + 1},
            "properties": {"pixelSize": 90}, "fields": "pixelSize"}},
    ]})
    return sid


def read_existing(env):
    """Lead ID -> (row number, row values). Row numbers are 1-based with the
    header at 1, which is what an A1 update range needs."""
    data = crm.fetch(env, [TAB]) if TAB in tab_titles(env) else {TAB: []}
    out = {}
    for i, row in enumerate(data.get(TAB, [])[1:], start=2):
        lid = crm.cell(row, 0)
        if lid:
            out[lid] = (i, row)
    return out


def tab_titles(env):
    meta = sheets_call(env, "GET", "?fields=sheets.properties.title")
    return [s["properties"]["title"] for s in meta.get("sheets", [])]


def row_for(lead_id, handle, prof, screen_url, repaired_from=""):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    blank = [""] * len(HEADER)
    if prof.get("error"):
        row = list(blank)
        row[0], row[1] = lead_id, "@" + (handle or "?")
        row[13] = ("не бизнес-аккаунт" if "business" in prof["error"].lower()
                   else prof["error"][:60])
        row[14] = now
        return row
    # Say so when the handle in this row is not what the lead typed -- an
    # unexplained correction in a CRM is worse than none.
    status = f'исправлен из «{repaired_from}»' if repaired_from else "ok"

    st = derive_stats(prof)
    last = st["last_post"] or ""
    if last and st["days_since_last"] is not None:
        last += f" ({st['days_since_last']} дн. назад)"
    return [
        lead_id, "@" + prof.get("username", handle),
        prof.get("followers_count", ""), prof.get("follows_count", ""),
        prof.get("media_count", ""), last,
        st["posts_per_month"] if st["posts_per_month"] is not None else "",
        st["median_likes"] if st["median_likes"] is not None else "",
        st["er_pct"] if st["er_pct"] is not None else "",
        f"{st['reels_share_pct']}%" if st["reels_share_pct"] is not None else "",
        prof.get("name", ""),
        " ".join((prof.get("biography") or "").split())[:300],
        prof.get("website", ""), status, now,
        f'=IMAGE("{screen_url}")' if screen_url else "", screen_url,
        # The whole point of the rebuild: columns are for The eyes, this cell
        # is for an agent. crm.py unpacks it straight back into the lead record.
        json.dumps({"stats": st, "posts": pack_posts(prof)}, ensure_ascii=False),
    ]


def write_rows(env, sid, new_rows, updates):
    if new_rows:
        rng = f"{urlparse.quote(TAB)}!A1"
        sheets_call(env, "POST",
                    f"/values/{rng}:append?valueInputOption=USER_ENTERED"
                    "&insertDataOption=INSERT_ROWS",
                    {"values": new_rows})
        log(f"appended {len(new_rows)} row(s)")
    if updates:
        sheets_call(env, "POST", "/values:batchUpdate", {
            "valueInputOption": "USER_ENTERED",
            "data": [{"range": f"{TAB}!A{n}:{LAST_COL}{n}", "values": [r]}
                     for n, r in updates]})
        log(f"updated {len(updates)} row(s)")
    # Only worth doing when a grid was actually uploaded: =IMAGE() scales to
    # its cell and renders as a smear on a 21px row. Data-only runs keep normal
    # rows -- 150px rows on a text table is just scrolling.
    if not any(r[COL_URL] for r in new_rows + [r for _, r in updates]):
        return
    filled = len(crm.fetch(env, [TAB], strict=False).get(TAB, []))
    if filled > 1:
        sheets_call(env, "POST", ":batchUpdate", {"requests": [
            {"updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "ROWS",
                          "startIndex": 1, "endIndex": filled},
                "properties": {"pixelSize": 150}, "fields": "pixelSize"}}]})


# ------------------------------------------------------------------- driver

def collect_targets(env, a):
    """(lead_id, raw chat answer) pairs to enrich, oldest lead first.

    The raw answer is carried, not a cleaned handle: repairing it is the
    resolver's job and it needs the original to work from."""
    if a.handle:
        h = norm_handle(a.handle)
        if not h:
            die(f"«{a.handle}» is not an Instagram username")
        return [(f"MANUAL-{h}", h)]

    data = crm.fetch(env, [crm.LEADS_TAB, crm.CALLS_TAB])
    leads = crm.build(data[crm.LEADS_TAB], data[crm.CALLS_TAB])
    leads = [L for L in leads if not L["is_test"]]
    if not a.all:
        start = datetime.now() - timedelta(days=a.days)
        leads = [L for L in leads if crm.in_window(L, start, None)]

    # Every lead who answered at all gets a row, including the ones whose
    # answer yields no candidate. Filtering them out here would leave a stale
    # row in the sheet with no way to correct it on a re-run.
    return [(L["lead_id"], L["chat"]["instagram"])
            for L in leads if L["chat"].get("instagram")]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch leads that already have a «Профили» row")
    ap.add_argument("--handle", help="enrich one account directly, no lead needed")
    ap.add_argument("--grid", action="store_true",
                    help="also build the profile-grid image and upload it — off by "
                         "default: it costs 12 image downloads per lead on a "
                         "2-4 Mb/s VPN and the data columns carry the facts")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")

    env = crm.load_env()
    targets = collect_targets(env, a)
    if not targets:
        log("no leads with an Instagram handle in that window.")
        return

    # Claim the tab BEFORE spending the network budget. Each account costs a
    # Graph call plus seven image downloads over a 2-4 Mb/s VPN; discovering a
    # permissions problem after all of that throws the whole run away.
    sid = None if a.dry_run else ensure_tab(env)
    existing = {} if a.dry_run else read_existing(env)
    todo = [(lid, h) for lid, h in targets
            if a.refresh or lid not in existing]
    if not todo:
        log(f"all {len(targets)} lead(s) already in «{TAB}». --refresh to re-fetch.")
        return

    log(f"{len(todo)} account(s) to fetch\n")
    overrides = load_overrides()
    new_rows, updates, results = [], [], []
    for lid, raw in todo:
        log(f"{raw}  ({lid})")
        prof, handle, tried = resolve_profile(raw, overrides)
        if prof.get("rate_limited"):
            log(f"    {prof['error']}\n"
                f"\nSTOP — the app's hourly Graph budget is gone. Nothing "
                f"further was looked up, and no row was marked failed on "
                f"account of it. Wait ~1h and re-run; already-resolved rows "
                f"are skipped unless you pass --refresh.")
            break
        repaired = bool(tried) and tried[-1] != ovkey(raw)
        if prof.get("error"):
            log(f"    {prof['error'][:60]} — пробовали: {', '.join(tried) or '—'}")
        else:
            if repaired:
                log(f"    исправлено → @{handle}")
            st = derive_stats(prof)
            log(f"    {prof.get('followers_count', 0)} подписчиков · "
                f"{prof.get('media_count', 0)} постов · "
                f"последний {st['last_post'] or '?'} "
                f"({st['days_since_last']} дн. назад) · "
                f"{st['posts_per_month'] or '?'}/мес · "
                f"ER {st['er_pct'] or '?'}% · Reels {st['reels_share_pct'] or 0}%")

        screen_url = ""
        if not prof.get("error") and a.grid:
            blob = build_grid(prof)
            if not a.dry_run:
                screen_url = upload_imgbb(blob, f"{handle}.jpg")
                if screen_url:
                    log(f"    {screen_url}")
            else:
                out = HERE / f"_dryrun_{handle}.jpg"
                out.write_bytes(blob)
                log(f"    wrote {out.name} (dry run — nothing uploaded)")

        row = row_for(lid, handle, prof, screen_url,
                      raw if repaired else "")
        results.append({
            "lead_id": lid, "handle": handle, "raw_answer": raw,
            "tried": tried, "screenshot_url": screen_url,
            "status": prof.get("error") or "ok",
            "stats": {} if prof.get("error") else derive_stats(prof),
            "posts": [] if prof.get("error") else pack_posts(prof),
            "profile": {k: v for k, v in prof.items() if k != "media"},
        })
        if lid in existing:
            # Never let a failed lookup overwrite a row that already resolved.
            # The account did not stop existing because one call came back
            # empty; the old data is better than a fresh «не найден».
            was = crm.cell(existing[lid][1], 13)
            if prof.get("error") and was.startswith(("ok", "исправлен")):
                log(f"    keeping the existing row — refusing to overwrite "
                    f"«{was[:40]}» with a failure")
                continue
            updates.append((existing[lid][0], row))
        else:
            new_rows.append(row)

    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    if a.dry_run:
        log("\n-- dry run, sheet untouched. Rows that would be written:")
        for r in new_rows + [r for _, r in updates]:
            log("   " + " | ".join(str(c)[:28] for c in r))
        return

    write_rows(env, sid, new_rows, updates)
    ok = sum(1 for r in results if r["status"] == "ok")
    log(f"\ndone. «{TAB}»: {ok} account(s) resolved, {len(todo) - ok} did not — "
        f"see the статус column.")


if __name__ == "__main__":
    main()
