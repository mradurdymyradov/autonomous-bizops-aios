#!/usr/bin/env python3
"""Assemble the whole business into one self-contained HTML app.

WHY ONE FILE: the output is opened from file:// by double-clicking it. Chrome
blocks fetch() and ES-module src across file:// origins, so a sibling data.json
would silently fail. Everything -- CSS, JS, fonts, data -- is inlined into
index.html. That also makes a later Cloudflare Pages deploy a single upload,
and because the app routes on the URL *hash*, the same bytes behave identically
in both places (no _redirects file, no server rewrite).

NO NETWORK AT RENDER TIME. The page must open on a 2-4 Mb/s VPN that drops, and
in the air on a laptop. No CDN, no web font over the wire, no chart library.

THREE TIERS OF DATA, and the page is honest about which is which:
  1  snapshots/daily/*.json   stored rows, always available, no network
  2  sheets/crm.py --json     live behind --live, cached to cache/crm.json
  3  business.json            derived projection of the markdown, written by
                              the /dashboard skill. Carries a hash of every
                              source file so a stale projection announces itself.

Row shape is law: automations/snapshot-schema.md.

THIS FILE COMPUTES, THE PAGE DRAWS. Every ranking, rollup, rate and rule lives
here in Python where it can be read and checked; app.js only turns the result
into DOM. When something looks wrong on the page, the bug is almost always in
this file, and `python funnel.py` / `python sheets/crm.py --all` are the two
commands that prove it either way.

Run:
  python build.py                 offline -- stored rows + cached CRM
  python build.py --live          refresh the snapshot and the CRM first
  python build.py --open          build, then open it
  python build.py --days 30       narrow the window (default: everything stored)
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import re
import statistics
import subprocess
import sys
import webbrowser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
AUTOMATIONS = HERE.parent
REPO = AUTOMATIONS.parent
TEMPLATE = HERE / "template"
CACHE = HERE / "cache"
OUT = HERE / "index.html"

TZ = timezone(timedelta(hours=5))            # Asia/Ashgabat -- the join key
MUTABLE_DAYS = 3                             # schema rule 1
DEFERRAL_CATEGORIES = ["перезвонит сам", "думает", "отложил"]
DEAD_CATEGORIES = ["не ЦА", "не заявка", "пропал"]
WON_CATEGORY = "интерес"

# Below this many observations a percentage is theatre, so the page prints the
# count pair instead. NIST's rule of thumb for a proportion is min(Np, N(1-p))
# >= 5, which at these conversion rates lands north of 500 sessions; 30 is the
# softer floor under which a delta gets no percentage at all.
CONFIDENCE_N = 30

STAGES = ["agreed", "spec", "questions", "build", "creative", "meeting", "live", "decision"]


def today_ash():
    return datetime.now(TZ).date()


def days_since(iso):
    if not iso:
        return None
    try:
        return (today_ash() - date.fromisoformat(iso[:10])).days
    except ValueError:
        return None


def load_funnel_module():
    """Reuse funnel.py's load/total/pct rather than reimplementing them.

    total() already keeps null distinct from zero (schema rule 3) -- the
    difference between "the tunnel dropped" and "traffic collapsed". Copying
    that logic is how the two surfaces drift apart.
    """
    spec = importlib.util.spec_from_file_location("_funnel", AUTOMATIONS / "funnel.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


# ------------------------------------------------------------------ tier 3
def sha12(path):
    if not path.exists():
        return None
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def load_business():
    """The derived projection, plus a verdict on whether it has gone stale."""
    path = HERE / "business.json"
    if not path.exists():
        return None, [{"file": "business.json", "problem": "missing"}]
    biz = json.loads(path.read_text(encoding="utf-8"))
    drifted = []
    for rel, recorded in (biz.get("source_files") or {}).items():
        actual = sha12(REPO / rel)
        if actual is None:
            drifted.append({"file": rel, "problem": "source file is gone"})
        elif actual != recorded:
            drifted.append({"file": rel, "problem": "changed since the last sync"})
    return biz, drifted


# ------------------------------------------------------------------ tier 2
def fetch_crm(live):
    """crm.py --json --all, cached. Offline renders from the cache and SAYS so.

    A cached CRM that looks live is exactly how the «Звонки» tab misled once
    already -- so fetched_at rides along and the page prints it.
    """
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / "crm.json"
    if live:
        script = AUTOMATIONS / "sheets" / "crm.py"
        try:
            p = subprocess.run([sys.executable, script.name, "--json", "--all"],
                               cwd=script.parent, capture_output=True,
                               text=True, encoding="utf-8", timeout=600)
            if p.returncode == 0 and p.stdout.strip():
                payload = json.loads(p.stdout)
                cached.write_text(json.dumps(
                    {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "payload": payload}, ensure_ascii=False), encoding="utf-8")
                print("  crm      refreshed")
            else:
                print(f"  crm      FAILED ({p.returncode}) -- falling back to cache")
        except Exception as e:                                   # noqa: BLE001
            print(f"  crm      FAILED ({type(e).__name__}) -- falling back to cache")
    if not cached.exists():
        return None, None
    blob = json.loads(cached.read_text(encoding="utf-8"))
    return blob.get("payload"), blob.get("fetched_at")


def real_leads(payload):
    """The 61. crm.py hides test rows already; duplicates it flags but keeps."""
    return [L for L in (payload.get("leads") or [])
            if not L.get("is_test") and not L.get("is_duplicate_phone")]


HANDLE_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def clean_handle(prof_handle, typed):
    """A handle we can actually open, or None.

    Twelve of the 61 answered the Instagram question with "?" -- and one "-",
    one "нет". Those are answers, not handles. Rendering them as @? invites a
    click that 404s, so they collapse to None here, once, and `handle_raw`
    keeps what they typed for the drawer to quote.
    """
    h = (prof_handle or typed or "").strip().lstrip("@")
    return h if HANDLE_RE.match(h) else None


def trim_lead(L, idx):
    """One lead, flattened for the table and the drawer.

    Deliberately dropped: `page` (a 300-char fbclid URL), `chat_raw` answers
    that duplicate `chat`, and profile.recent_posts captions. Deliberately
    KEPT: the profile stats block and the note text -- they are the whole
    reason the drawer is worth opening.
    """
    cs = L.get("call_stats") or {}
    note = L.get("note") or {}
    prof = L.get("profile") or {}
    chat = L.get("chat") or {}
    stats = prof.get("stats") or {}
    calls = [{"ts": c.get("ts"), "event": c.get("event"),
              "duration": c.get("duration") or 0}
             for c in (L.get("calls") or [])]
    return {
        "i": idx,
        "id": L.get("lead_id"),
        "label": cs.get("label") or "",
        "ts": L.get("ts"),
        "day": (L.get("ts") or "")[:10],
        "hour": int(L["ts"][11:13]) if L.get("ts") else None,
        "days": days_since(L.get("ts")),
        "phone": L.get("phone"),
        "digits": L.get("phone_digits"),
        "business": chat.get("business"),
        "language": chat.get("language"),
        "handle": clean_handle(prof.get("handle"), chat.get("instagram")),
        "handle_raw": chat.get("instagram"),
        "handle_status": prof.get("status"),
        "name": prof.get("name") or None,
        "bio": (prof.get("bio") or "")[:220] or None,
        "followers": prof.get("followers"),
        "posts": prof.get("posts"),
        "er": stats.get("er_pct"),
        "last_post": stats.get("last_post"),
        "median_views": stats.get("median_views"),
        "creative": (L.get("utm") or {}).get("creative"),
        "variant": L.get("variant"),
        "utm_medium": (L.get("utm") or {}).get("medium"),
        "dialled": cs.get("outgoing") or 0,
        "answered": bool(cs.get("reached")),
        "conversations": cs.get("conversations") or 0,
        "talk": cs.get("talk_total") or 0,
        "talk_longest": cs.get("talk_longest") or 0,
        "called_back": bool(cs.get("called_back")),
        "missed_from_them": cs.get("missed_from_them") or 0,
        "mtc": cs.get("minutes_to_call"),
        "category": note.get("category"),
        "note": note.get("text"),
        "follow_up": note.get("follow_up"),
        "objections": note.get("objections") or [],
        "calls": calls,
        "qa": [{"q": r.get("question"), "a": r.get("answer")}
               for r in (L.get("chat_raw") or [])],
    }


def derive_crm(payload):
    """Everything the lead-level screens need, computed here so the JS stays dumb."""
    raw = real_leads(payload)
    summary = payload.get("summary") or {}
    leads = [trim_lead(L, i) for i, L in enumerate(raw)]

    def tally(key):
        out = {}
        for L in leads:
            v = L.get(key)
            if v:
                out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    dialled = [L for L in leads if L["dialled"]]
    answered = [L for L in leads if L["answered"]]
    never = [L for L in leads if not L["dialled"]]
    talk = sum(L["talk"] for L in leads)

    # --- speed to lead. The leak STATE.md names: his sleep cycle, not neglect.
    # Two distributions on one axis: when leads ARRIVE and when they get CALLED.
    # The gap between the two humps is the finding; a single median hides it.
    mins = [L["mtc"] for L in leads if isinstance(L["mtc"], (int, float))]
    arrive = {h: 0 for h in range(24)}
    called = {h: 0 for h in range(24)}
    within = {h: 0 for h in range(24)}
    hour_mins = {h: [] for h in range(24)}
    for L in leads:
        if L["hour"] is not None:
            arrive[L["hour"]] += 1
            if isinstance(L["mtc"], (int, float)):
                hour_mins[L["hour"]].append(L["mtc"])
                if L["mtc"] <= 60:
                    within[L["hour"]] += 1
        for c in L["calls"]:
            if c["event"] == "исходящий" and c["ts"]:
                called[int(c["ts"][11:13])] += 1
    by_hour = [{"hour": h, "arrived": arrive[h], "called": called[h],
                "within_hour": within[h],
                "median": round(statistics.median(hour_mins[h])) if hour_mins[h] else None}
               for h in range(24)]

    # --- the callback pile. Every one of these was already paid for.
    debt = sorted([L for L in leads if L["category"] in DEFERRAL_CATEGORIES],
                  key=lambda L: L["ts"] or "")

    # Two different numbers, and conflating them overstates the wall by a third:
    # `objections` counts OCCURRENCES, `objection_leads` counts LEADS who raised
    # at least one. STATE.md's finding is the second -- most calls die without a
    # stated objection at all.
    objections, objection_leads = {}, 0
    for L in leads:
        if L["objections"]:
            objection_leads += 1
        for o in L["objections"]:
            objections[o] = objections.get(o, 0) + 1

    # --- creative quality, not creative volume. The finding that c.flat buys
    # clicks which don't hold a conversation only exists at this cut.
    quality = {}
    for L in leads:
        c = L["creative"] or "(none)"
        q = quality.setdefault(c, {"creative": c, "leads": 0, "dialled": 0,
                                   "answered": 0, "talk": 0, "over3": 0,
                                   "won": 0, "deferred": 0})
        q["leads"] += 1
        if L["dialled"]:
            q["dialled"] += 1
        if L["answered"]:
            q["answered"] += 1
            q["talk"] += L["talk"]
            if L["talk"] > 180:
                q["over3"] += 1
        if L["category"] == WON_CATEGORY:
            q["won"] += 1
        if L["category"] in DEFERRAL_CATEGORIES:
            q["deferred"] += 1
    for q in quality.values():
        q["avg_talk"] = round(q["talk"] / q["answered"]) if q["answered"] else None
    quality = sorted(quality.values(), key=lambda q: -q["leads"])

    # --- calls per Ashgabat day, for the activity strip. Sourced from the
    # phone-log export, so it stops at whatever `export_through` says.
    calls_per_day = {}
    for L in leads:
        for c in L["calls"]:
            if c["ts"]:
                d = c["ts"][:10]
                calls_per_day[d] = calls_per_day.get(d, 0) + 1
    leads_per_day = {}
    for L in leads:
        if L["day"]:
            leads_per_day[L["day"]] = leads_per_day.get(L["day"], 0) + 1

    return {
        "leads_real": summary.get("leads_real", len(leads)),
        "rows": summary.get("rows"),
        "no_phone": summary.get("no_phone"),
        "duplicate_phones": summary.get("duplicate_phones"),
        "tests_hidden": summary.get("tests_hidden"),
        "window": payload.get("window"),
        "by_creative": tally("creative"),
        "by_business": tally("business"),
        "by_language": tally("language"),
        "by_variant": tally("variant"),
        "categories": tally("category"),
        "objections": dict(sorted(objections.items(), key=lambda kv: -kv[1])),
        "objection_leads": objection_leads,
        "noted": sum(1 for L in leads if L["category"]),
        "won": [L["i"] for L in leads if L["category"] == WON_CATEGORY],
        "debt": [L["i"] for L in debt],
        "never_dialled": [L["i"] for L in never],
        "quality": quality,
        "calls": {
            "dialled": len(dialled),
            "answered": len(answered),
            "talk_seconds": talk,
            "called_back": sum(1 for L in leads if L["called_back"]),
            "missed_from_them": sum(L["missed_from_them"] for L in leads),
            "never_dialled": len(never),
            "conversations": sum(L["conversations"] for L in leads),
        },
        "speed": {
            "median_minutes": round(statistics.median(mins)) if mins else None,
            "within_hour": sum(1 for m in mins if m <= 60),
            "measured": len(mins),
            "by_hour": by_hour,
        },
        "per_day": {"leads": leads_per_day, "calls": calls_per_day},
        "leads": leads,
    }


# ------------------------------------------------------------------ tier 1
def derive_rows(rows, fm):
    """The stored time series, plus the funnel totals over the whole window.

    The date axis is continuous: a date with no stored row becomes null, never
    zero. A chart that draws a missing capture as a flat zero is worse than a
    gap in the line (schema rule 3).
    """
    by_date = {r["date"]: r for r in rows}
    first = date.fromisoformat(rows[0]["date"])
    last = date.fromisoformat(rows[-1]["date"])
    cutoff = today_ash() - timedelta(days=MUTABLE_DAYS)

    series, d = [], first
    while d <= last:
        iso = d.isoformat()
        r = by_date.get(iso)
        if r is None:
            series.append({"date": iso, "missing": True})
        else:
            meta, ga4, crm = r.get("meta") or {}, r.get("ga4") or {}, r.get("crm") or {}
            failed = r.get("sources_failed") or {}
            series.append({
                "date": iso,
                "final": bool(r.get("final")) and d <= cutoff,
                "failed": list(failed),
                "spend": None if "meta" in failed else meta.get("spend_usd"),
                "impressions": None if "meta" in failed else meta.get("impressions"),
                "reach": None if "meta" in failed else meta.get("reach"),
                "clicks": None if "meta" in failed else meta.get("clicks"),
                "link_clicks": None if "meta" in failed else meta.get("link_clicks"),
                "meta_leads": None if "meta" in failed else meta.get("meta_leads"),
                "cpc": None if "meta" in failed else meta.get("cpc"),
                "ctr": None if "meta" in failed else meta.get("ctr"),
                "sessions": None if "ga4" in failed else ga4.get("sessions"),
                "paid_sessions": None if "ga4" in failed else ga4.get("paid_sessions"),
                "engaged": None if "ga4" in failed else ga4.get("engaged_sessions"),
                "generate_lead": None if "ga4" in failed else ga4.get("generate_lead"),
                "leads": None if "crm" in failed else crm.get("leads_real"),
                "fn_errors": (r.get("cf") or {}).get("function_errors"),
                "fn_invocations": (r.get("cf") or {}).get("function_invocations"),
                "origin_5xx": (r.get("cf") or {}).get("origin_5xx"),
                "followers": (r.get("ig") or {}).get("followers"),
                "captured_at": r.get("captured_at"),
            })
        d += timedelta(days=1)

    t = lambda src, f: fm.total(rows, src, f)[0]                 # noqa: E731
    impressions, link_clicks = t("meta", "impressions"), t("meta", "link_clicks")
    spend = t("meta", "spend_usd")
    sessions, gen_lead = t("ga4", "sessions"), t("ga4", "generate_lead")
    paid_sessions = t("ga4", "paid_sessions")
    leads_real = t("crm", "leads_real")

    failures = {}
    for r in rows:
        for src in (r.get("sources_failed") or {}):
            failures.setdefault(src, []).append(r["date"])

    key_events_configured = next(
        (r["ga4"].get("key_events_configured") for r in reversed(rows) if r.get("ga4")), None)

    # The last day that actually delivered anything. With a paused campaign
    # this is the number that matters, not "yesterday".
    last_spend = next((s["date"] for s in reversed(series) if s.get("spend")), None)
    last_lead = next((s["date"] for s in reversed(series) if s.get("leads")), None)

    return {
        "window": {"start": rows[0]["date"], "end": rows[-1]["date"], "rows": len(rows)},
        "series": series,
        "funnel": [
            {"key": "impressions",   "label": "Impressions",   "value": impressions,
             "source": "Meta"},
            {"key": "link_clicks",   "label": "Link clicks",   "value": link_clicks,
             "source": "Meta"},
            {"key": "paid_sessions", "label": "Paid sessions", "value": paid_sessions,
             "source": "GA4"},
            {"key": "generate_lead", "label": "Form submits",  "value": gen_lead,
             "source": "GA4"},
            {"key": "leads_real",    "label": "Real leads",    "value": leads_real,
             "source": "Sheet CRM", "truth": True},
        ],
        "rates": {
            "link_ctr": pct(link_clicks, impressions),
            "arrival": pct(paid_sessions, link_clicks),
            "page_conversion": pct(gen_lead, sessions),
            "survives": pct(leads_real, gen_lead),
        },
        "money": {
            "spend": round(spend, 2),
            "cost_per_link_click": round(spend / link_clicks, 3) if link_clicks else None,
            "cost_per_real_lead": round(spend / leads_real, 2) if leads_real else None,
        },
        "reconciliation": {
            "meta_leads": t("meta", "meta_leads"),
            "ga4_generate_lead": gen_lead,
            "crm_leads_real": leads_real,
        },
        "totals": {
            "impressions": impressions, "reach": t("meta", "reach"),
            "clicks": t("meta", "clicks"), "link_clicks": link_clicks,
            "sessions": sessions, "paid_sessions": paid_sessions,
            "engaged": t("ga4", "engaged_sessions"),
            "generate_lead": gen_lead, "leads_real": leads_real,
            "fn_invocations": t("cf", "function_invocations"),
        },
        "alarms": {
            "function_errors": t("cf", "function_errors"),
            "origin_5xx": t("cf", "origin_5xx"),
            "key_events_configured": key_events_configured,
        },
        "health": {
            "moving": [s["date"] for s in series
                       if not s.get("missing") and not s.get("final")],
            "missing": [s["date"] for s in series if s.get("missing")],
            "failures": failures,
            "last_capture": rows[-1].get("captured_at"),
        },
        "ig": {
            "followers": next((s["followers"] for s in reversed(series)
                               if s.get("followers")), None),
            "posts_live": next(((r.get("ig") or {}).get("posts_live")
                                for r in reversed(rows) if (r.get("ig") or {}).get("posts_live")),
                               None),
        },
        "last_spend_day": last_spend,
        "last_lead_day": last_lead,
        "ads_latest": next(({"cpc": (r.get("meta") or {}).get("cpc"),
                             "ctr": (r.get("meta") or {}).get("ctr"),
                             "date": r["date"]}
                            for r in reversed(rows) if (r.get("meta") or {}).get("spend_usd")),
                           None),
    }


# ------------------------------------------------------------------ the queue
def build_queue(stored, crm, biz):
    """The ranked list of things that need Operator, in focus order.

    This is the whole point of the rebuild. A report tells you what happened;
    a queue tells you what to do, and shrinks as you do it. It shrinks for real
    -- every item is derived from a source Operator changes by working (a note in
    the Sheet, a line in STATE.md), so the next `/dashboard --live` drops it.
    Nothing here is a checkbox that only the page remembers.

    Order is fixed and NOT user-sortable, the way Linear's Triage is fixed:
    the ordering IS the opinion. Groups with nothing in them render nothing.
    """
    q = []

    def add(group, rank, title, meta=None, why=None, action=None,
            href=None, tel=None, sev="act", days=None, lead=None):
        q.append({"group": group, "rank": rank, "title": title, "meta": meta,
                  "why": why, "action": action, "href": href, "tel": tel,
                  "sev": sev, "days": days, "lead": lead})

    pipeline = (biz or {}).get("pipeline") or []

    # 1 — money already spent that is leaking on the floor. A deployed client
    #     page whose form goes nowhere is worse than no page: it takes a real
    #     заявка and drops it silently.
    #
    #     `form_dead` and not merely `blocker`: a deployed page can be blocked on
    #     the client (NG waiting on her own decision) with a form that works
    #     perfectly. Titling that "заявки уходят в никуда" is a lie, and it is the
    #     one row on this page nobody may learn to ignore.
    for p in pipeline:
        if p.get("deploy_url") and p.get("form_dead"):
            add("broken", 10, f"{p['name']} — заявки уходят в никуда",
                meta=p["deploy_url"], why=p["blocker"],
                action=p.get("next_action"), href=f"#/pipeline/{p['slug']}",
                sev="act", days=days_since(p.get("deployed_on")))

    # 2 — leads nobody has dialled. Paid for, still warm, zero touches.
    if crm:
        for i in crm["never_dialled"]:
            L = crm["leads"][i]
            add("uncalled", 20, L["business"] or "заявка без бизнеса",
                meta=L["phone"], why="Never dialled",
                href=f"#/leads/{L['i']}", tel=L["digits"], sev="act",
                days=L["days"], lead=L["i"])

    # 3 — the deferral pile, oldest first. Half of every recorded note.
    if crm:
        for i in crm["debt"]:
            L = crm["leads"][i]
            add("callback", 30, L["business"] or L["phone"] or "лид",
                meta=L["category"], why=L["note"], action=L["follow_up"],
                href=f"#/leads/{L['i']}", tel=L["digits"], sev="act",
                days=L["days"], lead=L["i"])

    # 4 — pilots. One at a time is the rule, so this is ranked, not parallel.
    #     `parked` pilots are left out entirely: capacity is THE stated
    #     constraint of this business, so a pilot deferred on purpose is a
    #     decision already made, not a thing needing him this morning. They keep
    #     their blocker and next action on the Pipeline route, where the
    #     decision is reviewed rather than re-taken every day.
    for p in pipeline:
        if p.get("parked"):
            continue
        if p.get("deploy_url") and p.get("form_dead"):
            continue                                  # already in group 1
        if p.get("blocker"):
            add("blocked", 40, p["name"], meta=p.get("niche"),
                why=p["blocker"], action=p.get("next_action"),
                href=f"#/pipeline/{p['slug']}", sev="act",
                days=days_since(p.get("last_touch")))
        elif p.get("next_action"):
            add("pilot", 50, p["name"], meta=p.get("niche"),
                why=f"stage · {p.get('stage')}", action=p["next_action"],
                href=f"#/pipeline/{p['slug']}", sev="watch",
                days=days_since(p.get("last_touch")))

    # 5 — open loops and tasks the markdown already ranked as high.
    for L in (biz or {}).get("open_loops") or []:
        if L.get("severity") == "high":
            add("loop", 60, L["title"], meta="open loop", why=L.get("text"),
                href="#/system/loops", sev="watch")
    for t in (biz or {}).get("todo") or []:
        if t.get("importance") == "высокая":
            add("task", 70, t["title"], meta=t.get("where"),
                why=t.get("note"), action=t.get("urgency"),
                href="#/system/todo", sev="watch")

    q.sort(key=lambda x: (x["rank"], -(x["days"] or 0)))
    return q


def build_insights(stored, crm, biz, drifted):
    """Rule-generated, never guessed. Each one names its evidence.

    Threshold rules only -- no model, no heuristics that can't be read off the
    page. An insight that cries wolf costs more than one that never fires, so
    anything resting on fewer than CONFIDENCE_N observations is suppressed
    rather than dressed up as a percentage.
    """
    out = []

    def add(sev, headline, evidence, recommend, href=None):
        out.append({"sev": sev, "headline": headline, "evidence": evidence,
                    "recommend": recommend, "href": href})

    ads = (biz or {}).get("ads") or {}
    unbuilt = sum(1 for p in ((biz or {}).get("pipeline") or [])
                  if not p.get("deploy_url"))
    paused = days_since(ads.get("paused_since"))
    if ads.get("status") == "PAUSED" and paused:
        add("act", f"Ads have been off for {paused} days",
            f"Last spend {stored.get('last_spend_day')}, "
            f"last real lead {stored.get('last_lead_day')}. "
            f"${stored['money']['spend']:.2f} lifetime, "
            f"${stored['money']['cost_per_real_lead']:.2f} per real заявка."
            if stored["money"]["cost_per_real_lead"] else "No spend in the window.",
            "Traffic is proven and is not the gate. Nothing new comes in until "
            f"a campaign runs — but {unbuilt} pilot{'s are' if unbuilt != 1 else ' is'} "
            "unbuilt, so this is a choice, not a leak.", "#/marketing")

    if crm:
        n = crm["calls"]["never_dialled"]
        if n:
            add("act", f"{n} lead{'s' if n != 1 else ''} never dialled",
                f"{crm['calls']['dialled']} of {crm['leads_real']} numbers dialled, "
                f"{crm['calls']['answered']} answered.",
                "Every one was paid for at the current cost per заявка. "
                "Dial them before spending on new traffic.", "#/leads?f=uncalled")

        debt = len(crm["debt"])
        if debt:
            oldest = max((crm["leads"][i]["days"] or 0) for i in crm["debt"])
            add("act", f"{debt} deferrals waiting on a second touch",
                f"перезвонит сам {crm['categories'].get('перезвонит сам', 0)} · "
                f"думает {crm['categories'].get('думает', 0)} · "
                f"отложил {crm['categories'].get('отложил', 0)}. "
                f"Oldest is {oldest} days old. "
                f"Only {crm['objection_leads']} of {crm['noted']} noted leads "
                f"raised an objection at all.",
                "There is still no second-touch step in this funnel. The pile is "
                "more than four times the size of the yes pile and it is already "
                "paid for.", "#/leads?f=callback")

        sp = crm["speed"]
        if sp["median_minutes"] and sp["measured"] >= 10:
            add("watch",
                f"Median {sp['median_minutes']} minutes from заявка to first call",
                f"{sp['within_hour']} of {sp['measured']} inside an hour.",
                "The shape is the sleep cycle, not neglect — leads arriving "
                "00:00–09:00 sit until he wakes. Fixing it is a schedule "
                "change, not effort.", "#/leads/speed")

    fn = stored["alarms"]["function_errors"]
    if fn:
        add("act", f"{fn} Cloudflare function errors in the window",
            "Every one is a submit that may have reached neither Telegram nor "
            "the Sheet.", "Run /check-cf and read the tail.", "#/system")

    stale = days_since(stored["window"]["end"])
    if stale and stale > 1:
        add("watch", f"No snapshot written for {stale} days",
            f"Last stored row {stored['window']['end']}. GA4 freezes after ~48h "
            "and IG insights cap at 30 days — days missed here are gone.",
            "Run /check-full, or python automations/snapshot.py --days 7.",
            "#/system")

    if drifted:
        add("watch", "The pipeline projection is behind the markdown",
            ", ".join(f"{d['file']} {d['problem']}" for d in drifted),
            "Re-run /dashboard so business.json catches up with STATE.md.",
            "#/system")

    if stored["alarms"]["key_events_configured"] is False:
        add("watch", "generate_lead is not a key event in GA4",
            "Every conversion rate in the property reads 0 by config, not by "
            "reality.", "Toggle it on the property. Note it is not retroactive.",
            "#/system")

    order = {"act": 0, "watch": 1, "info": 2}
    out.sort(key=lambda x: order.get(x["sev"], 3))
    return out


def build_activity(stored, crm, days=30):
    """One cell per Ashgabat day: what actually happened, from real events.

    Not a streak and not scored. Leads in and calls out are the two things Operator
    does that leave a trace, and both are already recorded — nothing here asks
    him to log anything.
    """
    end = today_ash()
    start = end - timedelta(days=days - 1)
    snap = {s["date"]: s for s in stored["series"]}
    per = (crm or {}).get("per_day") or {"leads": {}, "calls": {}}
    cells, d = [], start
    while d <= end:
        iso = d.isoformat()
        s = snap.get(iso) or {}
        leads = per["leads"].get(iso, 0)
        calls = per["calls"].get(iso, 0)
        cells.append({
            "date": iso,
            "leads": leads,
            "calls": calls,
            "spend": s.get("spend"),
            "sessions": s.get("sessions"),
            "captured": bool(s) and not s.get("missing"),
            "score": leads * 3 + calls,
        })
        d += timedelta(days=1)
    top = max([c["score"] for c in cells] or [0])
    for c in cells:
        c["level"] = 0 if not c["score"] else min(4, 1 + int(3 * c["score"] / top)) if top else 0
    return cells


def enrich_pipeline(biz):
    """Stage index, staleness and a per-client build state the page can draw."""
    for p in (biz or {}).get("pipeline") or []:
        p["stage_i"] = STAGES.index(p["stage"]) if p.get("stage") in STAGES else 0
        p["idle"] = days_since(p.get("last_touch"))
        p["state"] = ("broken" if p.get("deploy_url") and p.get("form_dead")
                      else "blocked" if p.get("blocker")
                      else "moving")
    return biz


# ------------------------------------------------------------------ assembly
# Golos Text is the landing page's body face and is already in the house, has a
# full Cyrillic set, and ships as one variable file 400..900. Prata was DROPPED:
# a Didone masthead is what made the previous page read as a printed brief.
#
# Golos has no `tnum` and its digits are proportional (0=620, 1=485, 4=610 units),
# so columns of figures do not line up in it. Every number on this page is
# therefore set in the system UI face, whose digits ARE tabular by default
# (Segoe UI on this machine, SF on Apple), with mono reserved for the data
# register -- phones, handles, timestamps, IDs. Verified against the actual font
# binaries, not assumed.
#
# They are base64'd into the page because it opens from file:// with no network.
CYR = "U+0401,U+0410-044F,U+0451,U+2116"
LAT = "U+0020-007E,U+00A0,U+00AB,U+00BB,U+2010-2015,U+2018-201F,U+2026"
FONT_FACES = {
    "golos-cyr": ("Golos Text", "400 900", CYR),
    "golos-lat": ("Golos Text", "400 900", LAT),
}
SKIP_FONTS = {"prata"}


def inline_fonts():
    """Base64 the woff2 files in template/fonts/ into @font-face rules.

    A CDN link would break the moment the tunnel drops, and the sandbox cannot
    download binaries anyway (CAPABILITIES.md B2).
    """
    folder = TEMPLATE / "fonts"
    if not folder.exists():
        return ""
    faces = []
    for f in sorted(folder.glob("*.woff2")):
        if f.stem in SKIP_FONTS:
            continue
        family, weight, urange = FONT_FACES.get(f.stem, (f.stem, "400", None))
        b64 = base64.b64encode(f.read_bytes()).decode()
        rule = (f"@font-face{{font-family:'{family}';font-style:normal;"
                f"font-weight:{weight};font-display:block;"
                f"src:url(data:font/woff2;base64,{b64}) format('woff2');")
        if urange:
            rule += f"unicode-range:{urange};"
        faces.append(rule + "}")
    return "\n".join(faces)


def build(live, days, open_after):
    fm = load_funnel_module()

    if live:
        print("live refresh:")
        snap = AUTOMATIONS / "snapshot.py"
        r = subprocess.run([sys.executable, snap.name, "--days", "7"],
                           cwd=snap.parent, capture_output=True, text=True,
                           encoding="utf-8", timeout=1800)
        print(f"  snapshot {'refreshed' if r.returncode == 0 else 'FAILED -- using stored rows'}")

    end = today_ash().isoformat()
    start = ((today_ash() - timedelta(days=days - 1)).isoformat() if days else "0000")
    rows = fm.load(start, end)
    if not rows:
        sys.exit(f"no stored rows in {AUTOMATIONS / 'snapshots' / 'daily'}\n"
                 "run:  python ../snapshot.py --days 14")

    crm_payload, crm_fetched = fetch_crm(live)
    biz, drifted = load_business()
    biz = enrich_pipeline(biz)

    stored = derive_rows(rows, fm)
    crm = derive_crm(crm_payload) if crm_payload else None

    data = {
        "built_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "today": today_ash().isoformat(),
        "confidence_n": CONFIDENCE_N,
        "stages": STAGES,
        "stored": stored,
        "crm": crm,
        "crm_fetched_at": crm_fetched,
        "business": biz,
        "drifted": drifted,
        "queue": build_queue(stored, crm, biz),
        "insights": build_insights(stored, crm, biz, drifted),
        "activity": build_activity(stored, crm),
    }

    html = (TEMPLATE / "index.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # </script> inside a string would close the tag early; escaping the slash is
    # enough and keeps the JSON valid. <!-- would also open a comment in HTML.
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = (html
            .replace("/*{{FONTS}}*/", inline_fonts())
            .replace("/*{{CSS}}*/", (TEMPLATE / "app.css").read_text(encoding="utf-8"))
            .replace("/*{{JS}}*/", (TEMPLATE / "app.js").read_text(encoding="utf-8"))
            .replace('"{{DATA}}"', payload))
    OUT.write_text(html, encoding="utf-8")

    kb = len(html.encode()) / 1024
    print(f"\n  {OUT}  ({kb:,.0f} KB)")
    print(f"  {stored['window']['rows']} stored days "
          f"{stored['window']['start']}..{stored['window']['end']}")
    if crm:
        print(f"  CRM {crm['leads_real']} real leads, fetched {crm_fetched}")
    else:
        print("  CRM UNAVAILABLE -- no cache and no live fetch. Run with --live.")
    print(f"  queue {len(data['queue'])} items, {len(data['insights'])} insights")
    for d in drifted:
        print(f"  ! {d['file']}: {d['problem']} -- rerun /dashboard")
    if open_after:
        webbrowser.open(OUT.as_uri())
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--live", action="store_true",
                   help="refresh the snapshot and the CRM first (needs the VPN)")
    p.add_argument("--days", type=int, default=0,
                   help="window in days; 0 (default) uses every stored row")
    p.add_argument("--open", action="store_true", dest="open_after")
    a = p.parse_args()
    return build(a.live, a.days, a.open_after)


if __name__ == "__main__":
    sys.exit(main())
