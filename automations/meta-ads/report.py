#!/usr/bin/env python3
"""Read what's actually live in the voronka.tm ad account.

Read-only. Creates nothing, changes nothing, never starts spend.

Prints, in order:
  1. account-level spend + insights for the window
  2. every campaign, with its ad sets and ads, plus per-campaign insights

Run:  python report.py [--days 30] [--all] [--who] [--json]
  --days N   insights window, default 30
  --all      include ARCHIVED/DELETED objects (default: active + paused only)
  --who      audience breakdowns, ranked by cost per reported lead
  --json     machine-readable; prints nothing else. This is the surface a runner
             (check-full / snapshot) consumes -- the other four readers already
             had it, this one did not until 2026-07-28.
"""
import argparse
import contextlib
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV = Path(__file__).parent / ".env"


def load_env(path):
    env = {}
    if not path.exists():
        sys.exit(f"missing {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def get(path, token, version, params=None, tries=3):
    """GET a Graph endpoint. Retries -- this runs over a 2-4 Mb/s VPN that drops."""
    url = f"https://graph.facebook.com/{version}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    ctx = ssl.create_default_context()
    last = None
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                return json.loads(body)
            except ValueError:
                return {"error": {"message": body, "code": e.code}}
        except Exception as e:  # timeout, DNS, TLS -- the VPN
            last = e
            if attempt < tries:
                time.sleep(2 * attempt)
    return {"error": {"message": f"network failed after {tries} tries: {last}"}}


def err(resp):
    if isinstance(resp, dict) and "error" in resp:
        return str(resp["error"].get("message", resp["error"]))
    return None


def money(minor):
    """Budgets and amount_spent come back in the account's minor units (cents)."""
    try:
        return f"${float(minor) / 100:.2f}"
    except (TypeError, ValueError):
        return "-"


def show_insights(ins, indent="  "):
    """Print one insights row. Meta omits fields entirely when there's no data."""
    if not ins:
        print(f"{indent}insights: no delivery in window")
        return
    spend = ins.get("spend", "0")
    imp = ins.get("impressions", "0")
    reach = ins.get("reach", "0")
    clicks = ins.get("clicks", "0")
    cpc = ins.get("cpc")
    ctr = ins.get("ctr")
    print(f"{indent}spend ${spend} | impr {imp} | reach {reach} | clicks {clicks}"
          f"{f' | CPC ${cpc}' if cpc else ''}{f' | CTR {ctr}%' if ctr else ''}")
    for a in ins.get("actions", []) or []:
        # only the ones that matter for this funnel
        if a["action_type"] in ("landing_page_view", "link_click", "lead",
                                "offsite_conversion.fb_pixel_lead"):
            print(f"{indent}  {a['action_type']}: {a['value']}")


# Who the money actually reached. This is the ONLY route to audience demographics:
# the organic IG endpoints withhold them until ~100 followers, the Marketing API
# does not care how many followers we have. Verified working 2026-07-26.
BREAKDOWN_SETS = [
    ("age", "age"),
    ("gender", "gender"),
    ("age + gender", "age,gender"),
    ("placement", "publisher_platform,platform_position"),
    ("device", "impression_device"),
    ("region", "region"),
]


def leads_from(row):
    for a in row.get("actions", []) or []:
        if a["action_type"] == "lead":
            try:
                return int(a["value"])
            except (TypeError, ValueError):
                return 0
    return 0


def show_breakdowns(acct, token, v, preset):
    """Rank every audience slice by cost per reported lead. Meta's `lead` is not
    truth -- the Telegram bot and the Sheet are -- but the RANKING between slices
    is the useful part, and both sides are counted the same way."""
    print("\n" + "=" * 64)
    print("WHO THE SPEND REACHED  (Meta-reported leads, ranked by cost)")
    print("=" * 64)
    collected = {}
    for label, bd in BREAKDOWN_SETS:
        r = get(f"{acct}/insights", token, v,
                {"fields": "reach,clicks,spend,actions", "breakdowns": bd,
                 "date_preset": preset, "level": "account"})
        if e := err(r):
            print(f"\n{label}: ! {e[:70]}")
            collected[label] = {"error": e}
            continue
        rows = r.get("data", []) or []
        if not rows:
            print(f"\n{label}: no data in window")
            collected[label] = []
            continue
        parsed = []
        for row in rows:
            dims = " ".join(str(row.get(k)) for k in bd.split(",") if row.get(k))
            spend, leads = float(row.get("spend") or 0), leads_from(row)
            parsed.append((dims, spend, leads, row.get("reach"), row.get("clicks")))
        # Slices with leads first, cheapest first; the rest by spend.
        parsed.sort(key=lambda p: (p[2] == 0, p[1] / p[2] if p[2] else -p[1]))
        print(f"\n{label}:")
        for dims, spend, leads, reach, clicks in parsed:
            cpl = f"${spend / leads:.2f}" if leads else "-"
            print(f"  {dims[:34]:34} spend ${spend:>5.2f}  reach {str(reach):>5}  "
                  f"clicks {str(clicks):>4}  leads {leads:>3}  per lead {cpl:>7}")
        collected[label] = [
            {"slice": dims, "spend": spend, "leads": leads,
             "reach": reach, "clicks": clicks,
             "cost_per_lead": round(spend / leads, 4) if leads else None}
            for dims, spend, leads, reach, clicks in parsed
        ]
    return collected


def run(args, out):
    env = load_env(ENV)
    token = env.get("META_ADS_ACCESS_TOKEN", "")
    if not token:
        sys.exit("META_ADS_ACCESS_TOKEN empty in .env")
    v = env.get("GRAPH_VERSION", "v21.0")
    acct = env["META_AD_ACCOUNT_ID"]

    preset = {7: "last_7d", 14: "last_14d", 30: "last_30d", 90: "last_90d"}.get(
        args.days, "last_30d")
    ins_fields = "spend,impressions,reach,clicks,cpc,ctr,actions"
    out["window"] = {"days": args.days, "date_preset": preset}
    out["account_id"] = acct

    print("=" * 64)
    # ASCII only in the printed report -- the Windows console is cp1252 and
    # mangles em dashes and bullets into garbage.
    print(f"voronka.tm ad account: {acct}   (window: {preset})")
    print("=" * 64)

    # ---- account ------------------------------------------------------
    a = get(acct, token, v, {
        "fields": "name,account_status,currency,timezone_name,amount_spent,balance"})
    if e := err(a):
        sys.exit(f"! account read failed: {e}")
    out["account"] = a
    print(f"name    : {a.get('name')}")
    print(f"status  : {a.get('account_status')} "
          f"{'(ACTIVE)' if a.get('account_status') == 1 else '(NOT ACTIVE)'}")
    print(f"currency: {a.get('currency')}  tz {a.get('timezone_name')}")
    print(f"lifetime spend: {money(a.get('amount_spent'))}")

    ai = get(f"{acct}/insights", token, v,
             {"fields": ins_fields, "date_preset": preset})
    if e := err(ai):
        print(f"  ! insights: {e}")
        out["insights"] = {"error": e}
    else:
        rows = ai.get("data", [])
        out["insights"] = rows[0] if rows else None
        show_insights(rows[0] if rows else None)

    if args.who:
        out["breakdowns"] = show_breakdowns(acct, token, v, preset)

    # ---- campaigns ----------------------------------------------------
    params = {
        "fields": "name,status,effective_status,objective,daily_budget,"
                  "lifetime_budget,budget_remaining,created_time,start_time,stop_time",
        "limit": 100,
    }
    if not args.all:
        params["effective_status"] = json.dumps(
            ["ACTIVE", "PAUSED", "CAMPAIGN_PAUSED", "IN_PROCESS", "WITH_ISSUES"])

    c = get(f"{acct}/campaigns", token, v, params)
    if e := err(c):
        sys.exit(f"! campaigns read failed: {e}")
    camps = c.get("data", [])
    out["campaigns"] = []

    print(f"\n=== campaigns: {len(camps)} ===")
    if not camps:
        print("  none. Nothing has ever been built in this account via API or UI.")
        return 0

    for camp in camps:
        cid = camp["id"]
        budget = camp.get("daily_budget") or camp.get("lifetime_budget")
        btype = "daily" if camp.get("daily_budget") else "lifetime"
        print(f"\n[{camp.get('effective_status')}] {camp.get('name')}  ({cid})")
        print(f"  objective: {camp.get('objective')}"
              f"{f'  budget {money(budget)} {btype}' if budget else ''}")
        print(f"  created  : {camp.get('created_time')}")
        print(f"  schedule : {camp.get('start_time', '-')} -> "
              f"{camp.get('stop_time', 'no end')}")

        rec = dict(camp)
        rec["adsets"] = []

        ci = get(f"{cid}/insights", token, v,
                 {"fields": ins_fields, "date_preset": preset})
        if e := err(ci):
            print(f"  ! insights: {e}")
            rec["insights"] = {"error": e}
        else:
            rows = ci.get("data", [])
            rec["insights"] = rows[0] if rows else None
            show_insights(rows[0] if rows else None)

        sets = get(f"{cid}/adsets", token, v, {
            "fields": "name,effective_status,daily_budget,lifetime_budget,"
                      "optimization_goal,targeting",
            "limit": 50})
        for s in sets.get("data", []) or []:
            sb = s.get("daily_budget") or s.get("lifetime_budget")
            geo = ",".join((s.get("targeting", {}).get("geo_locations", {})
                            .get("countries", [])))
            print(f"    - adset [{s.get('effective_status')}] {s.get('name')}")
            print(f"      goal {s.get('optimization_goal')}"
                  f"{f' | {money(sb)}' if sb else ''}"
                  f"{f' | geo {geo}' if geo else ''}")

            ads = get(f"{s['id']}/ads", token, v,
                      {"fields": "name,effective_status", "limit": 50})
            ad_rows = ads.get("data", []) or []
            for ad in ad_rows:
                print(f"        > ad [{ad.get('effective_status')}] {ad.get('name')}")
            rec["adsets"].append({
                "id": s.get("id"), "name": s.get("name"),
                "effective_status": s.get("effective_status"),
                "optimization_goal": s.get("optimization_goal"),
                "budget_minor": sb, "geo": geo,
                "ads": [{"id": ad.get("id"), "name": ad.get("name"),
                         "effective_status": ad.get("effective_status")}
                        for ad in ad_rows],
            })

        out["campaigns"].append(rec)

    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="insights window (default 30)")
    ap.add_argument("--all", action="store_true", help="include archived/deleted")
    ap.add_argument("--who", action="store_true",
                    help="audience breakdowns: age, gender, placement, device, region")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="machine-readable. Suppresses the human report entirely -- "
                         "this is what a runner (check-full / snapshot) consumes.")
    args = ap.parse_args()

    out = {}
    if not args.as_json:
        return run(args, out)

    # Human output goes to a sink so stdout stays valid JSON. sys.exit() inside
    # run() still fires on a hard failure -- that is deliberate, a runner needs a
    # non-zero exit, not an empty object that looks like "no campaigns".
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = run(args, out)
    except SystemExit as e:
        print(json.dumps({"error": buf.getvalue().strip() or str(e)}, indent=2))
        raise
    print(json.dumps(out, indent=2, default=str))
    return rc


if __name__ == "__main__":
    sys.exit(main())
