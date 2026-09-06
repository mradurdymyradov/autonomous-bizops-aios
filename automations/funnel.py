#!/usr/bin/env python3
"""Read the stored snapshots and print one funnel, end to end.

Touches no API and needs no VPN -- it reads automations/snapshots/daily/ only.
`snapshot.py` captures; this reads. That split is deliberate: on a 2-4 Mb/s
tunnel that drops, the analysis should never be gated on the network.

Row shape is law: automations/snapshot-schema.md.

Run:
  python funnel.py                    last 14 stored days
  python funnel.py --days 30
  python funnel.py --from 2026-07-23 --to 2026-07-27
  python funnel.py --creatives        which ad produced which leads
  python funnel.py --json

If the window is empty or stale, run:  python snapshot.py --days N
"""
import argparse
import contextlib
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DAILY = Path(__file__).parent / "snapshots" / "daily"
TZ = timezone(timedelta(hours=5))          # Asia/Ashgabat
BAR = "=" * 72


def load(start, end):
    rows = []
    if not DAILY.exists():
        sys.exit(f"no snapshots yet at {DAILY}\n"
                 "run:  python snapshot.py --days 14")
    for f in sorted(DAILY.glob("*.json")):
        if start <= f.stem <= end:
            try:
                rows.append(json.loads(f.read_text(encoding="utf-8")))
            except ValueError:
                print(f"  ! unreadable row skipped: {f.name}")
    return rows


def total(rows, source, field):
    """Sum a field, but keep null distinct from zero. Returns (sum, n_missing).

    A day whose reader FAILED contributes nothing and is counted as missing, so
    a tunnel drop can never masquerade as a quiet day in the totals.
    """
    got, missing = 0, 0
    for r in rows:
        block = r.get(source)
        if block is None or field not in block or block.get(field) is None:
            missing += 1
            continue
        got += block[field]
    return got, missing


def pct(a, b):
    return f"{100.0 * a / b:.1f}%" if b else "-"


def stage(label, value, width=22):
    return f"  {label.ljust(width)} {value:>12,}"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--from", dest="start")
    p.add_argument("--to", dest="end")
    p.add_argument("--creatives", action="store_true")
    p.add_argument("--json", action="store_true", dest="as_json")
    a = p.parse_args()

    today = datetime.now(TZ).date()
    end = a.end or today.isoformat()
    start = a.start or (today - timedelta(days=a.days - 1)).isoformat()
    rows = load(start, end)
    if not rows:
        sys.exit(f"no stored rows between {start} and {end}\n"
                 f"run:  python snapshot.py --days {a.days}")

    # --json emits JSON and nothing else -- a dashboard or runner parses stdout.
    # The human report goes to a sink so both modes stay one code path.
    sink = contextlib.ExitStack()
    if a.as_json:
        sink.enter_context(contextlib.redirect_stdout(io.StringIO()))

    impressions, _ = total(rows, "meta", "impressions")
    link_clicks, _ = total(rows, "meta", "link_clicks")
    spend, spend_missing = total(rows, "meta", "spend_usd")
    meta_leads, _ = total(rows, "meta", "meta_leads")
    sessions, _ = total(rows, "ga4", "sessions")
    paid_sessions, _ = total(rows, "ga4", "paid_sessions")
    gen_lead, _ = total(rows, "ga4", "generate_lead")
    leads_real, crm_missing = total(rows, "crm", "leads_real")
    fn_errors, _ = total(rows, "cf", "function_errors")
    origin_5xx, _ = total(rows, "cf", "origin_5xx")

    # ---------------------------------------------------------------- verdict
    if leads_real and spend:
        verdict = (f"{leads_real} real leads on ${spend:.2f} "
                   f"-- ${spend / leads_real:.2f} each")
    elif leads_real:
        verdict = f"{leads_real} real leads, no ad spend in this window"
    elif spend:
        verdict = f"${spend:.2f} spent, ZERO real leads -- the funnel is not closing"
    else:
        verdict = "no spend and no leads in this window -- nothing is running"

    print(BAR)
    print(f"FUNNEL  {start} .. {end}   ({len(rows)} stored days, Ashgabat)")
    print(BAR)
    print(f"\n  {verdict}\n")

    # ---------------------------------------------------------------- the line
    print(stage("impressions", impressions))
    print(f"       |  {pct(link_clicks, impressions)}  link CTR")
    print(stage("link clicks", link_clicks))
    print(f"       |  {pct(paid_sessions, link_clicks)}  arrival  "
          "(paid sessions vs paid clicks)")
    print(stage("paid sessions", paid_sessions))
    print(f"       |  {pct(gen_lead, sessions)}  page conversion  "
          "(on ALL sessions, not just paid)")
    print(stage("generate_lead", gen_lead))
    print(f"       |  {pct(leads_real, gen_lead)}  survives to the CRM")
    print(stage("REAL LEADS (truth)", leads_real))

    print(f"\n  all sessions {sessions:,}  (paid + organic + direct)")
    if spend:
        print(f"  spend ${spend:.2f}"
              + (f"  |  ${spend / link_clicks:.3f} per link click" if link_clicks else "")
              + (f"  |  ${spend / leads_real:.2f} per real lead" if leads_real else ""))
    print("  revenue $0.00  -- stays $0 until a pilot hits its N and pays")

    # ------------------------------------------------------- reconciliation
    print(f"\n{BAR}\nTHREE COUNTS OF THE SAME THING\n{BAR}")
    print(stage("Meta reported leads", meta_leads))
    print(stage("GA4 generate_lead", gen_lead))
    print(stage("CRM real leads", leads_real) + "   <- TRUTH")
    if leads_real:
        spread = max(meta_leads, gen_lead, leads_real) - min(meta_leads, gen_lead,
                                                             leads_real)
        print(f"\n  spread {spread} ({pct(spread, leads_real)} of truth). "
              "Meta and GA4 are estimates;")
        print("  the CRM is the only count that pays. A widening spread means a tag")
        print("  is misfiring -- chase it then, not now.")

    # ------------------------------------------------------------- alarms
    print(f"\n{BAR}\nALARMS\n{BAR}")
    if fn_errors:
        print(f"  /api/lead FAILED INVOCATIONS: {fn_errors}")
        print("  Each one is a submit that reached the server and may have reached")
        print("  NEITHER Telegram nor the Sheet. Invisible in every other tool.")
    else:
        print("  /api/lead errors      0   submits are landing")
    if origin_5xx:
        print(f"  origin 5xx            {origin_5xx}   visitors who got nothing")
    else:
        print("  origin 5xx            0   site served every request")

    # -------------------------------------------------------------- creatives
    if a.creatives:
        agg = {}
        for r in rows:
            for k, v in ((r.get("crm") or {}).get("by_creative") or {}).items():
                agg[k] = agg.get(k, 0) + v
        print(f"\n{BAR}\nREAL LEADS BY CREATIVE\n{BAR}")
        for k, v in sorted(agg.items(), key=lambda x: -x[1]):
            print(f"  {k.ljust(22)} {v:>5}  {pct(v, leads_real)}")
        print("\n  Volume is not the whole story -- check talk time per creative")
        print("  before calling a winner. `c.flat` bought clicks that did not hold")
        print("  a conversation (STATE.md).")

    # ----------------------------------------------------------- data health
    print(f"\n{BAR}\nDATA HEALTH\n{BAR}")
    moving = [r["date"] for r in rows if not r.get("final")]
    print(f"  {len(rows)} rows, {len(rows) - len(moving)} final, "
          f"{len(moving)} still moving"
          + (f" ({moving[0]}..{moving[-1]})" if moving else ""))
    if moving:
        print("  Rows stay mutable for 3 days -- GA4 backfills, Meta insights lag.")
        print("  Do not call a trend off the moving edge.")

    failed = {}
    for r in rows:
        for src, why in (r.get("sources_failed") or {}).items():
            failed.setdefault(src, []).append(r["date"])
    if failed:
        print("\n  READER FAILURES -- those fields are null, NOT zero:")
        for src, days in failed.items():
            print(f"    {src}: {len(days)} day(s), {days[0]}..{days[-1]}")
        print("  Re-run `snapshot.py` to fill them; rows upsert.")
    if crm_missing or spend_missing:
        print(f"\n  gaps: crm {crm_missing} day(s), meta {spend_missing} day(s)")

    ke = next((r["ga4"].get("key_events_configured")
               for r in rows if r.get("ga4")), None)
    if ke is False:
        print("\n  GA4 key events: NOT CONFIGURED.")
        print("  This does NOT invalidate the rates above -- those are computed")
        print("  from raw event counts, which work. It only means GA4's own")
        print("  built-in conversion metrics read 0 inside the GA4 UI.")
        print("  Fix: GA4 -> Admin -> Events -> generate_lead -> Mark as key event.")

    if a.as_json:
        sink.close()
        print(json.dumps({
            "window": {"start": start, "end": end, "rows": len(rows)},
            "funnel": {"impressions": impressions, "link_clicks": link_clicks,
                       "paid_sessions": paid_sessions, "sessions": sessions,
                       "generate_lead": gen_lead, "leads_real": leads_real},
            "money": {"spend_usd": round(spend, 2), "revenue_usd": 0,
                      "cost_per_real_lead": round(spend / leads_real, 4)
                      if leads_real else None},
            "reconciliation": {"meta_leads": meta_leads,
                               "ga4_generate_lead": gen_lead,
                               "crm_leads_real": leads_real},
            "alarms": {"function_errors": fn_errors, "origin_5xx": origin_5xx},
            "health": {"rows_moving": moving, "sources_failed": failed,
                       "key_events_configured": ke},
        }, indent=2))
    else:
        print(BAR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
