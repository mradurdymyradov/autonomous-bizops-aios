#!/usr/bin/env python3
"""Read everything GA4 knows about voronka.tm, for any period.

Read-only. Queries the GA4 Data API. Writes nothing, changes nothing.

Run:
  python report.py                          last 7 days
  python report.py --days 30                last 30 days
  python report.py --from 2026-07-23 --to 2026-07-27
  python report.py --days 3 --json          machine-readable
  python report.py --realtime               who is on the site right now
  python report.py --list                   every dimension + metric this property offers
  python report.py --dims country,city --metrics sessions,keyEvents --limit 50
                                            ad-hoc query for anything not in the sweep

Default sweep covers: totals, day-by-day, hour-of-day, acquisition (channel /
source / medium / campaign / referrer), every event, key events, pages, landing
pages, geography, technology, audience, and demographics.
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
        RunRealtimeReportRequest, GetMetadataRequest,
    )
    from google.oauth2 import service_account
except ImportError:
    sys.exit("missing lib. run:  python -m pip install google-analytics-data")

ENV = Path(__file__).parent / ".env"

# The console here is cp1252 -- ASCII only in printed output or it prints garbage.
BAR = "=" * 72


# ---------------------------------------------------------------- env / auth

def load_env(path):
    env = {}
    if not path.exists():
        sys.exit(f"missing {path}  -- see README.md, section 'Setup'")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def client_and_property(env=None):
    env = env or load_env(ENV)
    prop = env.get("GA4_PROPERTY_ID", "")
    if not prop or prop.startswith("<"):
        sys.exit("GA4_PROPERTY_ID empty in .env  -- README.md step 4")
    prop = prop.replace("properties/", "").strip()

    key_path = Path(env.get("GA4_CREDENTIALS_JSON", "").strip())
    if not key_path.is_absolute():
        key_path = Path(__file__).parent / key_path
    if not key_path.exists():
        sys.exit(f"service account key not found: {key_path}  -- README.md step 3")

    creds = service_account.Credentials.from_service_account_file(
        str(key_path),
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=creds), prop


# ---------------------------------------------------------------- api calls

# Metrics/dimensions GA4 rejects for a given property (custom setups, older
# API surface) get dropped and the request retried, rather than killing the run.
def _prune(msg, names):
    """Return names minus anything the error message complained about."""
    bad = {n for n in names if f"'{n}'" in msg or f'"{n}"' in msg or n in msg}
    return [n for n in names if n not in bad], bad


def run_report(client, prop, dims, metrics, start, end, limit=25,
               order_by=None, tries=3):
    """One runReport. Retries the VPN, prunes fields GA4 refuses."""
    dims, metrics = list(dims), list(metrics)
    for _ in range(4):  # at most 4 prune rounds
        if not metrics:
            return {"error": "all metrics rejected", "rows": []}
        req = RunReportRequest(
            property=f"properties/{prop}",
            dimensions=[Dimension(name=d) for d in dims],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=start, end_date=end)],
            limit=limit,
            return_property_quota=False,
        )
        if order_by and order_by in metrics:
            req.order_bys = [OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name=order_by), desc=True)]
        elif dims and dims[0] in ("date", "dateHour", "hour"):
            req.order_bys = [OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name=dims[0]))]

        last = None
        for attempt in range(1, tries + 1):
            try:
                return _shape(client.run_report(req), dims, metrics)
            except Exception as e:  # noqa: BLE001 -- want the message, any type
                msg = str(e)
                last = e
                if "INVALID_ARGUMENT" in msg or "not a valid" in msg \
                        or "incompatible" in msg.lower():
                    break  # fall through to pruning
                if attempt < tries:
                    time.sleep(2 * attempt)  # 2-4 Mb/s VPN that drops
                else:
                    return {"error": msg, "rows": []}

        msg = str(last)
        metrics2, badm = _prune(msg, metrics)
        dims2, badd = _prune(msg, dims)
        if not badm and not badd:
            return {"error": msg, "rows": []}
        metrics, dims = metrics2, dims2
    return {"error": "gave up pruning", "rows": []}


def _shape(resp, dims, metrics):
    out = {"dims": dims, "metrics": metrics, "rows": [], "totals": {},
           "row_count": resp.row_count}
    for r in resp.rows:
        out["rows"].append({
            "keys": [v.value for v in r.dimension_values],
            "vals": [v.value for v in r.metric_values],
        })
    for t in resp.totals:
        out["totals"] = {m: v.value for m, v in zip(metrics, t.metric_values)}
    # `rows` is positional -- keys[] and vals[] line up with dims[] and metrics[]
    # by INDEX. Anything reading it by position gives a silently wrong number
    # when GA4 prunes a rejected metric (see _prune), which is a wrong answer,
    # not a crash. `records` is the same data keyed by name; consume this.
    out["records"] = [dict(zip(dims, r["keys"])) | dict(zip(metrics, r["vals"]))
                      for r in out["rows"]]
    return out


def key_events_configured(sections):
    """Tri-state: is `generate_lead` actually marked as a key event in GA4?

    True  -- keyEvents is counting, conversion rates are real
    False -- generate_lead fired but keyEvents is 0. Every conversion metric in
             this property is a FALSE zero, by config, not by reality. Anything
             computing a conversion rate must suppress it rather than print 0%.
    None  -- no leads in the window, so the question can't be answered from here.

    One toggle fixes False: GA4 -> Admin -> Events -> Mark as key event.
    """
    def _first(section, pred, field):
        for rec in (sections.get(section) or {}).get("records") or []:
            if pred(rec):
                try:
                    return int(rec.get(field) or 0)
                except (TypeError, ValueError):
                    return 0
        return 0

    key_events = _first("totals_volume", lambda r: True, "keyEvents")
    leads = _first("EVENTS - every event GA4 recorded",
                   lambda r: r.get("eventName") == "generate_lead", "eventCount")
    if key_events > 0:
        return True
    return False if leads > 0 else None


# ---------------------------------------------------------------- formatting

def num(s):
    """GA4 returns everything as a string. Make it readable."""
    try:
        f = float(s)
    except (TypeError, ValueError):
        return str(s)
    if f != f or f in (float("inf"), float("-inf")):
        return "-"
    if abs(f - round(f)) < 1e-9:
        return f"{int(round(f)):,}"
    return f"{f:,.2f}"


def pretty(name, raw):
    """Rates come back as 0..1 floats, durations as seconds."""
    try:
        f = float(raw)
    except (TypeError, ValueError):
        return str(raw)
    if name.endswith("Rate") or name in ("engagementRate", "bounceRate"):
        return f"{f * 100:.2f}%"
    if "Duration" in name:
        m, s = divmod(int(f), 60)
        return f"{m}m{s:02d}s" if m else f"{int(f)}s"
    if name in ("totalRevenue", "purchaseRevenue", "averagePurchaseRevenue"):
        return f"${f:,.2f}"
    return num(raw)


def table(title, rep, note=""):
    print(f"\n--- {title} " + "-" * max(0, 68 - len(title)))
    if note:
        print(f"    ({note})")
    if rep.get("error"):
        print(f"    ! {rep['error'][:300]}")
        return
    if not rep["rows"]:
        print("    no data in this period")
        return

    dims, metrics = rep["dims"], rep["metrics"]
    head = [d for d in dims] + [m for m in metrics]
    rows = [[k for k in r["keys"]] + [pretty(m, v)
                                      for m, v in zip(metrics, r["vals"])]
            for r in rep["rows"]]

    widths = [len(h) for h in head]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    widths = [min(w, 42) for w in widths]

    def line(cells):
        return "  ".join(str(c)[:widths[i]].ljust(widths[i])
                         for i, c in enumerate(cells))

    print("    " + line(head))
    print("    " + "  ".join("-" * w for w in widths))
    for r in rows:
        print("    " + line(r))
    if rep.get("row_count", 0) > len(rows):
        print(f"    ... {rep['row_count'] - len(rows)} more rows "
              f"(raise --limit to see them)")


def totals_block(title, rep):
    print(f"\n--- {title} " + "-" * max(0, 68 - len(title)))
    if rep.get("error"):
        print(f"    ! {rep['error'][:300]}")
        return
    if not rep["totals"]:
        print("    no data in this period")
        return
    w = max(len(k) for k in rep["totals"])
    for k, v in rep["totals"].items():
        print(f"    {k.ljust(w)}  {pretty(k, v)}")


# ---------------------------------------------------------------- the sweep

# Metrics that pair with almost any dimension. Anything GA4 refuses for a
# given dimension gets pruned automatically by run_report.
CORE = ["sessions", "totalUsers", "screenPageViews", "eventCount",
        "keyEvents", "engagementRate", "averageSessionDuration"]

SECTIONS = [
    # (title, dimensions, metrics, limit, order_by, note)
    ("EVENTS - every event GA4 recorded", ["eventName"],
     ["eventCount", "totalUsers", "eventCountPerUser", "keyEvents"], 100,
     "eventCount", "generate_lead is the LP's real-submit event"),

    ("ACQUISITION - default channel group", ["sessionDefaultChannelGroup"],
     CORE, 25, "sessions", ""),
    ("ACQUISITION - source / medium", ["sessionSource", "sessionMedium"],
     CORE, 40, "sessions", ""),
    ("ACQUISITION - campaign", ["sessionCampaignName", "sessionSource"],
     CORE, 30, "sessions", "Meta ads land here if UTMs are set"),
    ("ACQUISITION - first-touch source / medium",
     ["firstUserSource", "firstUserMedium"], ["totalUsers", "newUsers",
     "sessions", "keyEvents"], 30, "totalUsers", "how users FIRST arrived"),
    ("ACQUISITION - referrer URLs", ["pageReferrer"],
     ["sessions", "totalUsers", "keyEvents"], 30, "sessions", ""),

    ("PAGES - landing pages", ["landingPage"],
     ["sessions", "totalUsers", "engagementRate", "keyEvents",
      "averageSessionDuration", "bounceRate"], 40, "sessions", ""),
    ("PAGES - all page paths", ["pagePath"],
     ["screenPageViews", "totalUsers", "userEngagementDuration", "eventCount"],
     40, "screenPageViews", ""),
    ("PAGES - page titles", ["pageTitle"],
     ["screenPageViews", "totalUsers"], 25, "screenPageViews", ""),

    ("GEOGRAPHY - country", ["country"], CORE, 30, "sessions",
     "TKM is VPN-heavy; scattered countries = VPN exits, not bad targeting"),
    ("GEOGRAPHY - region / city", ["region", "city"],
     ["sessions", "totalUsers", "keyEvents", "engagementRate"], 40, "sessions",
     ""),

    ("TECHNOLOGY - device category", ["deviceCategory"], CORE, 10, "sessions",
     ""),
    ("TECHNOLOGY - operating system / browser",
     ["operatingSystem", "browser"],
     ["sessions", "totalUsers", "engagementRate", "keyEvents"], 30, "sessions",
     ""),
    ("TECHNOLOGY - screen resolution", ["screenResolution"],
     ["sessions", "totalUsers"], 20, "sessions", ""),
    ("TECHNOLOGY - mobile device model", ["mobileDeviceModel"],
     ["sessions", "totalUsers"], 25, "sessions", ""),

    ("AUDIENCE - new vs returning", ["newVsReturning"],
     ["sessions", "totalUsers", "engagementRate", "keyEvents"], 10, "sessions",
     ""),
    ("AUDIENCE - language", ["language"], ["sessions", "totalUsers"], 20,
     "sessions", ""),
    ("AUDIENCE - age bracket", ["userAgeBracket"],
     ["totalUsers", "sessions", "keyEvents"], 15, "totalUsers",
     "Google thresholds demographics on low traffic -- blank is normal"),
    ("AUDIENCE - gender", ["userGender"],
     ["totalUsers", "sessions", "keyEvents"], 10, "totalUsers", ""),
]


def sweep(client, prop, start, end, limit_override=None):
    data = {}

    print(f"\n{BAR}\nTOTALS\n{BAR}")
    t1 = run_report(client, prop, [], [
        "activeUsers", "totalUsers", "newUsers", "sessions", "engagedSessions",
        "screenPageViews", "eventCount", "keyEvents"], start, end, limit=1)
    t2 = run_report(client, prop, [], [
        "engagementRate", "bounceRate", "averageSessionDuration",
        "userEngagementDuration", "sessionsPerUser",
        "screenPageViewsPerSession", "eventCountPerUser"], start, end, limit=1)
    totals_block("volume", t1)
    totals_block("engagement", t2)
    data["totals_volume"], data["totals_engagement"] = t1, t2

    print(f"\n{BAR}\nOVER TIME\n{BAR}")
    by_date = run_report(client, prop, ["date"], [
        "sessions", "totalUsers", "newUsers", "screenPageViews", "eventCount",
        "keyEvents", "engagementRate", "averageSessionDuration"],
        start, end, limit=400)
    table("day by day", by_date)
    data["by_date"] = by_date

    by_hour = run_report(client, prop, ["hour"], [
        "sessions", "totalUsers", "keyEvents", "engagementRate"],
        start, end, limit=24)
    table("hour of day (property timezone)", by_hour,
          "when your audience is actually awake -- use it for ad scheduling")
    data["by_hour"] = by_hour

    current = None
    for title, dims, metrics, limit, order, note in SECTIONS:
        head = title.split(" - ")[0]
        if head != current:
            print(f"\n{BAR}\n{head}\n{BAR}")
            current = head
        rep = run_report(client, prop, dims, metrics, start, end,
                         limit=limit_override or limit, order_by=order)
        table(title.split(" - ", 1)[1], rep, note)
        data[title] = rep

    return data


# ---------------------------------------------------------------- modes

def list_catalog(client, prop):
    """Every dimension and metric THIS property offers, custom ones included."""
    md = client.get_metadata(GetMetadataRequest(
        name=f"properties/{prop}/metadata"))
    print(f"\n{BAR}\nDIMENSIONS ({len(md.dimensions)})\n{BAR}")
    for d in sorted(md.dimensions, key=lambda x: x.api_name):
        flag = "  [CUSTOM]" if d.custom_definition else ""
        print(f"  {d.api_name.ljust(38)} {d.ui_name}{flag}")
    print(f"\n{BAR}\nMETRICS ({len(md.metrics)})\n{BAR}")
    for m in sorted(md.metrics, key=lambda x: x.api_name):
        flag = "  [CUSTOM]" if m.custom_definition else ""
        print(f"  {m.api_name.ljust(38)} {m.ui_name}{flag}")
    print(f"\nUse any of these:  python report.py --dims A,B --metrics X,Y")


def realtime(client, prop):
    print(f"\n{BAR}\nREALTIME - active users in the last 30 minutes\n{BAR}")
    for dims in (["unifiedScreenName"], ["country", "city"],
                 ["deviceCategory"], ["eventName"]):
        try:
            resp = client.run_realtime_report(RunRealtimeReportRequest(
                property=f"properties/{prop}",
                dimensions=[Dimension(name=d) for d in dims],
                metrics=[Metric(name="activeUsers")],
                limit=25))
            rep = _shape(resp, dims, ["activeUsers"])
        except Exception as e:  # noqa: BLE001
            rep = {"error": str(e), "rows": [], "dims": dims,
                   "metrics": ["activeUsers"]}
        table(" / ".join(dims), rep)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument("--days", type=int, help="window ending today (default 7)")
    ap.add_argument("--from", dest="frm", help="start date YYYY-MM-DD")
    ap.add_argument("--to", dest="to", help="end date YYYY-MM-DD (default today)")
    ap.add_argument("--limit", type=int, help="max rows per table")
    ap.add_argument("--json", action="store_true", help="machine-readable dump")
    ap.add_argument("--realtime", action="store_true", help="last 30 minutes")
    ap.add_argument("--list", action="store_true",
                    help="every dimension + metric this property offers")
    ap.add_argument("--dims", help="ad-hoc query: comma-separated dimensions")
    ap.add_argument("--metrics", help="ad-hoc query: comma-separated metrics")
    args = ap.parse_args()

    env = load_env(ENV)
    client, prop = client_and_property(env)

    if args.list:
        return list_catalog(client, prop)
    if args.realtime:
        return realtime(client, prop)

    # GA4 dates are in the PROPERTY's timezone, not UTC and not this machine's.
    if args.frm:
        start = args.frm
        end = args.to or "today"
    else:
        days = args.days or 7
        start = (date.today() - timedelta(days=days - 1)).isoformat()
        end = args.to or "today"

    if args.dims or args.metrics:
        dims = [d.strip() for d in (args.dims or "").split(",") if d.strip()]
        metrics = [m.strip() for m in (args.metrics or "").split(",") if m.strip()]
        rep = run_report(client, prop, dims, metrics, start, end,
                         limit=args.limit or 100,
                         order_by=metrics[0] if metrics else None)
        if args.json:
            print(json.dumps(rep, indent=1))
        else:
            print(f"\nproperty {prop}  |  {start} -> {end}")
            table(" / ".join(dims) or "totals", rep)
        return 0

    site = env.get("GA4_PROPERTY_NAME", "voronka.tm")
    if not args.json:
        print(BAR)
        print(f"GA4: {site}   property {prop}   window {start} -> {end}")
        print("read-only. GA4 dates use the PROPERTY timezone, not UTC.")
        print(BAR)

    if args.json:
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            data = sweep(client, prop, start, end, args.limit)
        print(json.dumps({"property": prop, "start": start, "end": end,
                          "key_events_configured": key_events_configured(data),
                          "sections": data}, indent=1))
    else:
        data = sweep(client, prop, start, end, args.limit)
        if key_events_configured(data) is False:
            print(f"\n{BAR}")
            print("WARNING: generate_lead fired in this window, but keyEvents is 0.")
            print("Every conversion-rate number in this property is a FALSE zero --")
            print("it is a config gap, not reality. Do not report 0% conversion.")
            print("Fix: GA4 -> Admin -> Events -> generate_lead -> Mark as key event.")
        print(f"\n{BAR}")
        print("Anything missing? `--list` shows every field this property has,")
        print("then `--dims A,B --metrics X,Y` queries it directly.")
        print(BAR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
