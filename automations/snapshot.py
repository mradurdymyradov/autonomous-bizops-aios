#!/usr/bin/env python3
"""Fold every reader into one row per Ashgabat date, and keep it forever.

Read-only against every API. Writes only under automations/snapshots/.

WHY THIS EXISTS: every reader is a point-in-time query against an API with a hard
window -- IG insights cap at 30 days, story insights die at 24h, GA4 backfills ~48h
then freezes, Meta presets only reach back so far. Nothing accumulates. Every day
that passes unsnapshotted is gone for good, and a dashboard cannot draw a line
through data nobody kept. This is the only script whose value decays if it is not
run; the rest can always be run later.

The row shape is law: automations/snapshot-schema.md. Don't add a field here
without adding it there.

Run:
  python snapshot.py                    last 7 days, upsert
  python snapshot.py --days 30          wider backfill
  python snapshot.py --dry-run          print the rows, write nothing
  python snapshot.py --only meta,crm    just those readers
  python snapshot.py --skip ig          everything but that one
  python snapshot.py --force            rewrite rows already marked final

Rows stay mutable for 3 days (GA4 backfills, Meta insights lag), then freeze.
Re-running is safe and expected -- that is how the last three days get corrected.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
SNAP = HERE / "snapshots"
BAR = "=" * 72

# Asia/Ashgabat, UTC+5, no DST. The Meta ad account, the GA4 property and the
# Sheet all report in it, so it is the join key. Cloudflare is UTC and is kept
# separate on purpose -- see the schema.
TZ = timezone(timedelta(hours=5))

SOURCES = ["meta", "ga4", "crm", "ig", "cf"]
MUTABLE_DAYS = 3


def today_ash():
    return datetime.now(TZ).date()


def load_module(name, path):
    """Import a reader by path. All four are named report.py, so they collide
    under a plain import -- and meta-ads has a hyphen, which is not importable
    at all. Explicit spec loading sidesteps both."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_reader(script, args, timeout=900):
    """Shell out to a reader's --json. Returns parsed JSON or raises RuntimeError."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run(
            [sys.executable, str(script.name), *args, "--json"],
            cwd=str(script.parent), env=env, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"timed out after {timeout}s (the VPN, usually)")
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "").strip().splitlines()
        raise RuntimeError(f"exit {p.returncode}: {tail[-1] if tail else 'no output'}")
    try:
        return json.loads(p.stdout)
    except ValueError as e:
        raise RuntimeError(f"reader did not emit JSON: {e}")


def blank(dates):
    return {d: {} for d in dates}


# ------------------------------------------------------------------ collectors
# Each returns {ashgabat_date: {...}} and raises RuntimeError on failure. A
# failure must never look like a zero -- see assemble().

def collect_meta(dates, start, end, raw):
    """Per-day Meta insights. report.py only does date_preset windows, so this
    calls the Graph directly through its helpers -- the documented escape hatch
    in the check-ads skill -- with time_increment=1 for one row per day."""
    M = load_module("_meta_report", HERE / "meta-ads" / "report.py")
    env = M.load_env(M.ENV)
    token = env["META_ADS_ACCESS_TOKEN"]
    v = env.get("GRAPH_VERSION", "v21.0")
    acct = env["META_AD_ACCOUNT_ID"]

    r = M.get(f"{acct}/insights", token, v, {
        "fields": "spend,impressions,reach,clicks,cpc,ctr,actions",
        "time_range": json.dumps({"since": start, "until": end}),
        "time_increment": 1,
        "level": "account",
    })
    if e := M.err(r):
        raise RuntimeError(e)
    raw["meta"] = r

    def action(row, kind):
        for a in row.get("actions") or []:
            if a["action_type"] == kind:
                return int(float(a["value"]))
        return 0

    # The reader SUCCEEDED, so a date Meta returned no row for genuinely had no
    # delivery -- that is a real zero, not missing data. Only a failed reader
    # yields null (see assemble). Defaulting here keeps the two distinguishable.
    zero = {"spend_usd": 0.0, "impressions": 0, "reach": 0, "clicks": 0,
            "link_clicks": 0, "landing_page_views": 0, "meta_leads": 0,
            "cpc": 0.0, "ctr": 0.0}
    out = {d: dict(zero) for d in dates}
    for row in r.get("data") or []:
        d = row.get("date_start")
        if d not in out:
            continue
        # Meta returns every numeric as a string. Cast, or it concatenates.
        out[d] = {
            "spend_usd": float(row.get("spend") or 0),
            "impressions": int(row.get("impressions") or 0),
            "reach": int(row.get("reach") or 0),
            "clicks": int(row.get("clicks") or 0),
            "link_clicks": action(row, "link_click"),
            "landing_page_views": action(row, "landing_page_view"),
            "meta_leads": action(row, "lead"),
            "cpc": float(row.get("cpc") or 0),
            "ctr": float(row.get("ctr") or 0),
        }
    return out


def collect_ga4(dates, start, end, raw):
    """Per-day sessions, generate_lead and paid sessions. The sweep's by_date
    section has no per-day event breakdown, so this runs three ad-hoc reports."""
    G = load_module("_ga4_report", HERE / "ga4" / "report.py")
    client, prop = G.client_and_property()

    def iso(gadate):                       # GA4 returns "20260803"
        return f"{gadate[:4]}-{gadate[4:6]}-{gadate[6:]}" if len(gadate) == 8 else gadate

    totals = G.run_report(client, prop, ["date"],
                          ["sessions", "engagedSessions", "keyEvents"],
                          start, end, limit=400)
    events = G.run_report(client, prop, ["date", "eventName"], ["eventCount"],
                          start, end, limit=2000)
    channels = G.run_report(client, prop, ["date", "sessionDefaultChannelGroup"],
                            ["sessions"], start, end, limit=2000)
    raw["ga4"] = {"totals": totals, "events": events, "channels": channels}
    for rep in (totals, events, channels):
        if rep.get("error"):
            raise RuntimeError(rep["error"])

    out = blank(dates)
    for rec in totals.get("records") or []:
        d = iso(rec.get("date", ""))
        if d in out:
            out[d].update({
                "sessions": int(rec.get("sessions") or 0),
                "engaged_sessions": int(rec.get("engagedSessions") or 0),
                "key_events": int(rec.get("keyEvents") or 0),
            })
    for rec in events.get("records") or []:
        d = iso(rec.get("date", ""))
        if d in out and rec.get("eventName") == "generate_lead":
            out[d]["generate_lead"] = int(rec.get("eventCount") or 0)
    for rec in channels.get("records") or []:
        d = iso(rec.get("date", ""))
        if d in out and rec.get("sessionDefaultChannelGroup") == "Paid Social":
            out[d]["paid_sessions"] = int(rec.get("sessions") or 0)

    # False zeros: generate_lead fired but keyEvents is 0 => config gap, not
    # reality. Carried per-row so nothing downstream prints a 0% conversion rate.
    configured = G.key_events_configured({"totals_volume": {"records": [
        {"keyEvents": str(sum(v.get("key_events", 0) for v in out.values()))}]},
        "EVENTS - every event GA4 recorded": {"records": [
            {"eventName": "generate_lead",
             "eventCount": str(sum(v.get("generate_lead", 0) for v in out.values()))}]}})
    for v in out.values():
        for k in ("generate_lead", "paid_sessions", "sessions", "engaged_sessions"):
            v.setdefault(k, 0)             # reader answered => a quiet day is 0
        v["key_events_configured"] = configured
    return out


def collect_crm(dates, days, raw):
    """TRUTH for заявки. Grouped by the lead's own Ashgabat timestamp."""
    d = run_reader(HERE / "sheets" / "crm.py", ["--days", str(days)])
    raw["crm"] = d
    out = blank(dates)
    for L in d.get("leads") or []:
        ts = (L.get("ts") or "")[:10]          # '2026-07-24T04:31:50' -> date
        if ts not in out:
            continue                           # crm.py's window overlaps ours
        if L.get("is_test"):
            continue
        row = out[ts]
        row["leads_raw_rows"] = row.get("leads_raw_rows", 0) + 1
        if L.get("is_duplicate_phone"):
            row["duplicate_phones"] = row.get("duplicate_phones", 0) + 1
            continue
        row["leads_real"] = row.get("leads_real", 0) + 1
        if not L.get("phone_digits"):
            row["no_phone"] = row.get("no_phone", 0) + 1
        creative = (L.get("utm") or {}).get("creative") or "(none)"
        row.setdefault("by_creative", {})
        row["by_creative"][creative] = row["by_creative"].get(creative, 0) + 1
        chat = L.get("chat") or {}
        for field, key in (("business", "by_business"), ("language", "by_language")):
            val = chat.get(field)
            if val:
                row.setdefault(key, {})
                row[key][val] = row[key].get(val, 0) + 1
    # Same rule as meta: the reader answered, so a quiet day is a real zero.
    for v in out.values():
        for k in ("leads_real", "leads_raw_rows", "duplicate_phones", "no_phone"):
            v.setdefault(k, 0)
    return out


def collect_ig(dates, days, raw):
    """Organic only. daily.reach is a list of {value, end_time}."""
    d = run_reader(HERE / "ig-insights" / "report.py",
                   ["--days", str(min(days, 30)), "--no-demographics"])
    raw["ig"] = d
    out = blank(dates)
    for point in ((d.get("daily") or {}).get("reach") or []):
        # end_time is the START of the following day, so the value belongs to
        # the day before it. Getting this wrong shifts the whole series by one.
        et = (point.get("end_time") or "")[:10]
        if not et:
            continue
        try:
            day = (date.fromisoformat(et) - timedelta(days=1)).isoformat()
        except ValueError:
            continue
        if day in out:
            out[day]["account_reach"] = point.get("value")
    profile = d.get("profile") or {}
    for v in out.values():
        v["followers"] = profile.get("followers_count")
        v["posts_live"] = profile.get("media_count")
    return out


def collect_cf(dates, start, end, raw):
    """ALARMS, not volume. pageViews is bot-inflated and must not be charted."""
    d = run_reader(HERE / "cloudflare" / "report.py",
                   ["--from", start, "--to", end])
    raw["cf"] = d
    out = blank(dates)
    for day in d.get("daily") or []:
        dt = (day.get("dimensions") or {}).get("date")
        if dt not in out:
            continue
        s = day.get("sum") or {}
        f5xx = sum(r["requests"] for r in (s.get("responseStatusMap") or [])
                   if str(r.get("edgeResponseStatus", "")).startswith("5"))
        out[dt] = {
            "tz": "UTC",                       # the one source not on Ashgabat time
            "origin_5xx": f5xx,
            "page_views_bot_inflated": s.get("pageViews"),
            "function_invocations": 0,
            "function_errors": 0,
        }
    for fn in d.get("functions") or []:
        hour = (fn.get("dimensions") or {}).get("datetimeHour") or ""
        day = hour[:10]
        if day in out and out[day]:
            out[day]["function_invocations"] += (fn.get("sum") or {}).get("requests", 0)
            out[day]["function_errors"] += (fn.get("sum") or {}).get("errors", 0)
    return out


# ------------------------------------------------------------------ assembling

def assemble(dates, collected, failed, captured_at, cutoff):
    rows = []
    for d in dates:
        row = {
            "date": d,
            "captured_at": captured_at,
            "final": date.fromisoformat(d) < cutoff,
            "sources_ok": sorted(k for k in collected if collected[k] is not None),
            "sources_failed": failed,
        }
        for src in SOURCES:
            got = collected.get(src)
            # A failed reader is null, never 0. "The VPN dropped" and "reach was
            # zero" must not collapse into the same value on a chart.
            row[src] = None if got is None else (got.get(d) or {})
        meta, crm = row.get("meta") or {}, row.get("crm") or {}
        row["money"] = {"spend_usd": meta.get("spend_usd"), "revenue_usd": 0}
        row["funnel"] = {
            "impressions": meta.get("impressions"),
            "link_clicks": meta.get("link_clicks"),
            "ga4_sessions": (row.get("ga4") or {}).get("sessions"),
            "generate_lead": (row.get("ga4") or {}).get("generate_lead"),
            "leads_real": crm.get("leads_real"),
        }
        rows.append(row)
    return rows


def write_rows(rows, force, dry):
    daily = SNAP / "daily"
    written, skipped = [], []
    for row in rows:
        path = daily / f"{row['date']}.json"
        if path.exists() and not force:
            try:
                if json.loads(path.read_text(encoding="utf-8")).get("final"):
                    skipped.append(row["date"])
                    continue
            except ValueError:
                pass                       # unreadable: overwrite it
        if not dry:
            daily.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(row, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        written.append(row["date"])
    return written, skipped


def print_table(rows):
    print(f"\n{BAR}\nFUNNEL BY DAY (Ashgabat)\n{BAR}")
    head = ("date", "impr", "clicks", "sess", "gen_lead", "LEADS", "spend")
    print("  " + "".join(h.rjust(w) for h, w in
                         zip(head, (12, 9, 8, 7, 10, 8, 9))))

    def cell(v, w, money=False):
        if v is None:
            return "-".rjust(w)
        return (f"${v:,.2f}" if money else f"{v:,}").rjust(w)

    tot = dict.fromkeys(("impressions", "link_clicks", "ga4_sessions",
                         "generate_lead", "leads_real"), 0)
    spend = 0.0
    for r in rows:
        f = r["funnel"]
        print("  " + r["date"].rjust(12)
              + cell(f["impressions"], 9) + cell(f["link_clicks"], 8)
              + cell(f["ga4_sessions"], 7) + cell(f["generate_lead"], 10)
              + cell(f["leads_real"], 8)
              + cell((r["money"] or {}).get("spend_usd"), 9, money=True))
        for k in tot:
            tot[k] += f.get(k) or 0
        spend += (r["money"] or {}).get("spend_usd") or 0
    print("  " + "TOTAL".rjust(12) + f"{tot['impressions']:,}".rjust(9)
          + f"{tot['link_clicks']:,}".rjust(8) + f"{tot['ga4_sessions']:,}".rjust(7)
          + f"{tot['generate_lead']:,}".rjust(10)
          + f"{tot['leads_real']:,}".rjust(8) + f"${spend:,.2f}".rjust(9))

    # ASCII only in printed output -- this console is cp1251 and turns Cyrillic
    # into question marks. The data files are UTF-8 and keep it properly.
    if tot["leads_real"] and spend:
        print(f"\n  ${spend / tot['leads_real']:.2f} per real lead "
              f"({tot['leads_real']} leads on ${spend:.2f})")
    ga4 = next((r["ga4"] for r in rows if r.get("ga4")), None)
    if ga4 and ga4.get("key_events_configured") is False:
        print("\n  NOTE: keyEvents is 0 by CONFIG, not reality -- generate_lead is")
        print("  not marked as a key event. Conversion rates suppressed, not zero.")
        print("  Fix: GA4 -> Admin -> Events -> generate_lead -> Mark as key event.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--only", help="comma-separated: " + ",".join(SOURCES))
    p.add_argument("--skip", help="comma-separated")
    p.add_argument("--dry-run", action="store_true", dest="dry")
    p.add_argument("--force", action="store_true",
                   help="rewrite rows already marked final")
    a = p.parse_args()

    wanted = [s for s in (a.only.split(",") if a.only else SOURCES)
              if s not in (a.skip.split(",") if a.skip else [])]
    bad = [s for s in wanted if s not in SOURCES]
    if bad:
        sys.exit(f"unknown source(s): {', '.join(bad)}. Known: {', '.join(SOURCES)}")

    end_d = today_ash()
    start_d = end_d - timedelta(days=a.days - 1)
    start, end = start_d.isoformat(), end_d.isoformat()
    dates = [(start_d + timedelta(days=i)).isoformat() for i in range(a.days)]
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(BAR)
    print(f"SNAPSHOT  {start} .. {end}  (Asia/Ashgabat)")
    print(f"sources: {', '.join(wanted)}")
    print(BAR)

    raw, collected, failed = {}, {}, {}
    jobs = {
        "meta": lambda: collect_meta(dates, start, end, raw),
        "ga4": lambda: collect_ga4(dates, start, end, raw),
        "crm": lambda: collect_crm(dates, a.days, raw),
        "ig": lambda: collect_ig(dates, a.days, raw),
        "cf": lambda: collect_cf(dates, start, end, raw),
    }
    for src in wanted:
        print(f"  {src:5} ... ", end="", flush=True)
        try:
            collected[src] = jobs[src]()
            print("ok")
        except Exception as e:                      # noqa: BLE001 -- one dead
            collected[src] = None                   # reader must not kill the run
            failed[src] = str(e)[:300]
            print(f"FAILED  {str(e)[:100]}")

    rows = assemble(dates, collected, failed, captured_at,
                    end_d - timedelta(days=MUTABLE_DAYS))
    print_table(rows)

    written, skipped = write_rows(rows, a.force, a.dry)
    if not a.dry:
        rawdir = SNAP / "raw" / end
        rawdir.mkdir(parents=True, exist_ok=True)
        for src, blob in raw.items():
            (rawdir / f"{src}.json").write_text(
                json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{BAR}")
    if a.dry:
        print(f"DRY RUN -- nothing written. {len(written)} rows would be.")
    else:
        print(f"wrote {len(written)} rows -> {SNAP / 'daily'}")
        print(f"raw   -> {SNAP / 'raw' / end}")
    if skipped:
        print(f"skipped {len(skipped)} already-final rows "
              f"({skipped[0]}..{skipped[-1]}). --force to rewrite.")
    if failed:
        print(f"\n{len(failed)} reader(s) failed -- those fields are null, NOT zero:")
        for src, e in failed.items():
            print(f"  {src}: {e}")
        print("A failure here is usually the VPN. Re-run; rows upsert.")
    print(BAR)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
