#!/usr/bin/env python3
"""Read Cloudflare's server-side view of voronkatm.com.

Read-only. Queries the Cloudflare GraphQL Analytics API. Writes nothing,
changes nothing, deploys nothing.

This is the only surface that sees a visit BEFORE any JavaScript runs. GA4
needs a tag to fire; the Meta pixel needs a tag to fire; Cloudflare counts the
request at the edge. That gap is the whole point of this tool.

Run:
  python report.py                       last 7 days
  python report.py --days 30             last 30 days
  python report.py --from 2026-07-23 --to 2026-07-27
  python report.py --paths               per-URL breakdown (adaptive dataset)
  python report.py --json                machine-readable
  python report.py --list                which datasets THIS plan actually exposes
  python report.py --gql "<query>"       ad-hoc GraphQL for anything not covered

Every section probes independently. A section the plan does not expose prints
"unavailable" with Cloudflare's own error and the rest of the run continues.
"""
import argparse
import contextlib
import io
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("missing lib. run:  python -m pip install requests")

ENV = Path(__file__).parent / ".env"
GQL = "https://api.cloudflare.com/client/v4/graphql"
REST = "https://api.cloudflare.com/client/v4"

# The console here is cp1251/cp1252 -- ASCII only in printed output.
BAR = "=" * 72


# ---------------------------------------------------------------- env / auth

def load_env(path=ENV):
    env = {}
    if not path.exists():
        sys.exit(f"missing {path}  -- see README.md, section 'Setup'")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    for key in ("CF_API_TOKEN", "CF_ZONE_ID", "CF_ACCOUNT_ID"):
        val = env.get(key, "")
        if not val or val.startswith("<"):
            sys.exit(f"{key} empty in .env  -- run:  python verify.py")
    return env


def gql(query, token, tries=4):
    """One GraphQL call. Retries the VPN. Raises RuntimeError on API errors.

    Dates are inlined into the query text rather than passed as variables --
    Cloudflare's filter fields use custom scalars (Date, Time) and guessing the
    variable type name is a needless way to fail.
    """
    last = None
    for attempt in range(tries):
        try:
            r = requests.post(
                GQL,
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                json={"query": query},
                timeout=60,
            )
        except requests.RequestException as e:      # tunnel dropped
            last = str(e)
            time.sleep(2 ** attempt)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            last = f"HTTP {r.status_code}"
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 403:
            raise RuntimeError(
                "403 -- the token lacks a permission for this dataset. "
                "run: python verify.py")
        try:
            body = r.json()
        except ValueError:
            raise RuntimeError(f"HTTP {r.status_code}, non-JSON body: {r.text[:300]}")
        if body.get("errors"):
            msg = "; ".join(e.get("message", str(e)) for e in body["errors"])
            raise RuntimeError(msg)
        return body.get("data") or {}
    raise RuntimeError(f"network failed after {tries} tries: {last}")


def rest(path, token, tries=4):
    last = None
    for attempt in range(tries):
        try:
            r = requests.get(f"{REST}{path}",
                             headers={"Authorization": f"Bearer {token}"},
                             timeout=45)
        except requests.RequestException as e:
            last = str(e)
            time.sleep(2 ** attempt)
            continue
        try:
            return r.json()
        except ValueError:
            last = f"HTTP {r.status_code}"
            time.sleep(2 ** attempt)
    raise RuntimeError(f"network failed after {tries} tries: {last}")


# ---------------------------------------------------------------- queries

def q_daily(zone, start, end):
    return """
    { viewer { zones(filter: {zoneTag: "%s"}) {
        httpRequests1dGroups(
          limit: 366
          filter: {date_geq: "%s", date_leq: "%s"}
          orderBy: [date_ASC]
        ) {
          dimensions { date }
          sum {
            requests
            pageViews
            cachedRequests
            bytes
            threats
            countryMap { clientCountryName requests }
            responseStatusMap { edgeResponseStatus requests }
            contentTypeMap { edgeResponseContentTypeName requests }
          }
          uniq { uniques }
        }
    } } }""" % (zone, start, end)


def q_hourly(zone, start_dt, end_dt):
    return """
    { viewer { zones(filter: {zoneTag: "%s"}) {
        httpRequests1hGroups(
          limit: 744
          filter: {datetime_geq: "%s", datetime_leq: "%s"}
          orderBy: [datetime_ASC]
        ) {
          dimensions { datetime }
          sum { requests pageViews }
          uniq { uniques }
        }
    } } }""" % (zone, start_dt, end_dt)


def q_paths(zone, start_dt, end_dt, limit):
    return """
    { viewer { zones(filter: {zoneTag: "%s"}) {
        httpRequestsAdaptiveGroups(
          limit: %d
          filter: {datetime_geq: "%s", datetime_leq: "%s"}
          orderBy: [count_DESC]
        ) {
          count
          dimensions {
            clientRequestPath
            clientRequestHTTPMethodName
            edgeResponseStatus
          }
        }
    } } }""" % (zone, limit, start_dt, end_dt)


def q_referers(zone, start_dt, end_dt, limit):
    return """
    { viewer { zones(filter: {zoneTag: "%s"}) {
        httpRequestsAdaptiveGroups(
          limit: %d
          filter: {datetime_geq: "%s", datetime_leq: "%s"}
          orderBy: [count_DESC]
        ) {
          count
          dimensions { clientRefererHost clientCountryName }
        }
    } } }""" % (zone, limit, start_dt, end_dt)


def q_pages_functions(account, start_dt, end_dt, project):
    # No scriptName filter. Pages does NOT name the worker after the project --
    # it is "pages-worker--<numeric-id>-production". Filtering on the project
    # name here returns zero rows and the section silently vanishes.
    # scriptName comes back as a dimension; match on it after the fact.
    return """
    { viewer { accounts(filter: {accountTag: "%s"}) {
        pagesFunctionsInvocationsAdaptiveGroups(
          limit: 500
          filter: {datetime_geq: "%s", datetime_leq: "%s"}
          orderBy: [datetimeHour_ASC]
        ) {
          sum { requests errors }
          dimensions { datetimeHour scriptName status }
        }
    } } }""" % (account, start_dt, end_dt)


def q_introspect(type_name):
    return '{ __type(name: "%s") { fields { name } } }' % type_name


# ---------------------------------------------------------------- probing

class Probe:
    """Run a query, remember why it failed instead of killing the run."""

    def __init__(self, token):
        self.token = token
        self.errors = {}

    def run(self, label, query, unwrap):
        try:
            data = gql(query, self.token)
        except RuntimeError as e:
            self.errors[label] = str(e)[:300]
            return None
        try:
            return unwrap(data)
        except (KeyError, IndexError, TypeError):
            self.errors[label] = "the zone/account returned no container for this dataset"
            return None


def zone_unwrap(field):
    return lambda d: d["viewer"]["zones"][0][field]


def account_unwrap(field):
    return lambda d: d["viewer"]["accounts"][0][field]


# ---------------------------------------------------------------- printing

def head(title):
    print(f"\n{BAR}\n{title}\n{BAR}")


def rows(pairs, width=34, total=None):
    for name, count in pairs:
        share = ""
        if total:
            share = f"  {100.0 * count / total:5.1f}%"
        print(f"  {str(name)[:width].ljust(width)} {count:>10,}{share}")


def merge_map(days, key, name_field, count_field="requests"):
    """Sum one of the *Map breakdowns across every day in the window."""
    out = {}
    for d in days:
        for row in (d.get("sum", {}).get(key) or []):
            out[row[name_field]] = out.get(row[name_field], 0) + row[count_field]
    return sorted(out.items(), key=lambda x: -x[1])


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--from", dest="start", help="YYYY-MM-DD")
    p.add_argument("--to", dest="end", help="YYYY-MM-DD")
    p.add_argument("--paths", action="store_true",
                   help="per-URL and per-referer breakdown (adaptive dataset)")
    p.add_argument("--hours", action="store_true", help="hour-by-hour")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--list", action="store_true",
                   help="which datasets this plan exposes (schema introspection)")
    p.add_argument("--gql", help="run an arbitrary GraphQL query and print JSON")
    p.add_argument("--json", action="store_true", dest="as_json")
    a = p.parse_args()

    env = load_env()
    token = env["CF_API_TOKEN"]
    zone = env["CF_ZONE_ID"]
    account = env["CF_ACCOUNT_ID"]
    project = env.get("CF_PAGES_PROJECT", "").strip()

    if a.gql:
        print(json.dumps(gql(a.gql, token), indent=2))
        return 0

    if a.list:
        head("DATASETS THIS PLAN EXPOSES")
        # Cloudflare's analytics schema names these types in lowercase.
        for t in ("zone", "account"):
            try:
                d = gql(q_introspect(t), token)
                names = [f["name"] for f in d["__type"]["fields"]]
            except (RuntimeError, KeyError, TypeError) as e:
                print(f"\n{t}: introspection failed -- {str(e)[:200]}")
                continue
            print(f"\n{t} ({len(names)}):")
            for n in sorted(names):
                print(f"  {n}")
        print("\nAnything listed here can be queried with --gql.")
        return 0

    # --json must emit JSON and NOTHING else -- a runner (snapshot.py) parses
    # stdout. The human report below goes to a sink instead of being deleted, so
    # both modes stay one code path. Placed after --list/--gql, which own their
    # own output.
    sink = contextlib.ExitStack()
    if a.as_json:
        sink.enter_context(contextlib.redirect_stdout(io.StringIO()))

    # window ----------------------------------------------------------------
    if a.start:
        start = a.start
        end = a.end or date.today().isoformat()
    else:
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=a.days - 1)).isoformat()
    start_dt = f"{start}T00:00:00Z"
    end_dt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")

    probe = Probe(token)
    out = {"window": {"start": start, "end": end}}

    print(BAR)
    print(f"CLOUDFLARE EDGE -- voronkatm.com   {start} .. {end}")
    print("server-side. counts requests that never ran a line of JavaScript.")
    print(BAR)

    # 1. daily zone analytics (free plan: this is the reliable one) ----------
    days = probe.run("httpRequests1dGroups", q_daily(zone, start, end),
                     zone_unwrap("httpRequests1dGroups")) or []
    out["daily"] = days

    if days:
        req = sum(d["sum"]["requests"] for d in days)
        pv = sum(d["sum"]["pageViews"] for d in days)
        cached = sum(d["sum"]["cachedRequests"] for d in days)
        uniq = sum(d["uniq"]["uniques"] for d in days)
        byt = sum(d["sum"]["bytes"] for d in days)
        thr = sum(d["sum"]["threats"] for d in days)
        out["totals"] = {"requests": req, "pageViews": pv, "uniques": uniq,
                         "cachedRequests": cached, "bytes": byt, "threats": thr}

        head("TOTALS")
        rows([("requests (everything, bots included)", req),
              ("page views (html documents served)", pv),
              ("unique visitors (edge estimate)", uniq),
              ("cached requests", cached),
              ("threats blocked", thr),
              ("bytes served", byt)])

        print("\n  THE COMPARISON THIS TOOL EXISTS FOR:")
        print(f"    Cloudflare page views  {pv:,}")
        print("    vs Meta link clicks    -> /check-ads")
        print("    vs GA4 sessions        -> /check-ga4")
        print("  page views BELOW link clicks  = the click never reached the page")
        print("                                  (bounce-before-load, DNS, VPN, misfire)")
        print("  page views ABOVE GA4 sessions = the page loaded, the tag did not fire")

        head("DAY BY DAY")
        print(f"  {'date'.ljust(12)} {'requests':>10} {'pageViews':>10} {'uniques':>9}")
        for d in days:
            print(f"  {d['dimensions']['date'].ljust(12)} "
                  f"{d['sum']['requests']:>10,} {d['sum']['pageViews']:>10,} "
                  f"{d['uniq']['uniques']:>9,}")

        ctypes = merge_map(days, "contentTypeMap", "edgeResponseContentTypeName")
        if ctypes:
            head("CONTENT TYPE")
            rows(ctypes[:15], total=req)

        statuses = merge_map(days, "responseStatusMap", "edgeResponseStatus")
        if statuses:
            head("RESPONSE STATUS")
            rows(statuses[:15], total=req)
            bad = sum(c for s, c in statuses if int(s) >= 400)
            if bad:
                print(f"\n  {bad:,} requests returned 4xx/5xx "
                      f"({100.0 * bad / req:.1f}%). Anything on / or /api/lead is a "
                      "lost lead, not a statistic.")

        countries = merge_map(days, "countryMap", "clientCountryName")
        if countries:
            head("COUNTRY (edge-observed, VPN exits included)")
            rows(countries[:15], total=req)
            print("\n  TM traffic behind a VPN exits as NL/DE/TR. Scattered geography "
                  "here is\n  the same VPN effect GA4 shows, not a targeting failure.")
    else:
        head("TOTALS")
        print("  httpRequests1dGroups returned nothing -- see NOT AVAILABLE below.")

    # 2. hourly -------------------------------------------------------------
    if a.hours:
        hrs = probe.run("httpRequests1hGroups", q_hourly(zone, start_dt, end_dt),
                        zone_unwrap("httpRequests1hGroups"))
        out["hourly"] = hrs
        if hrs:
            head("HOUR BY HOUR (UTC -- Ashgabat is UTC+5)")
            for h in hrs:
                if h["sum"]["requests"]:
                    print(f"  {h['dimensions']['datetime']}  "
                          f"{h['sum']['requests']:>7,} req  "
                          f"{h['sum']['pageViews']:>6,} pv")

    # 3. per-path (adaptive; may be plan-limited) ---------------------------
    if a.paths:
        paths = probe.run("httpRequestsAdaptiveGroups (paths)",
                          q_paths(zone, start_dt, end_dt, a.limit),
                          zone_unwrap("httpRequestsAdaptiveGroups"))
        out["paths"] = paths
        if paths:
            agg = {}
            for row in paths:
                d = row["dimensions"]
                k = (d.get("clientRequestPath"),
                     d.get("clientRequestHTTPMethodName"),
                     d.get("edgeResponseStatus"))
                agg[k] = agg.get(k, 0) + row["count"]
            head("PATHS")
            print(f"  {'path'.ljust(38)} {'method'.ljust(7)} {'status'.ljust(6)} {'hits':>8}")
            for (path, meth, st), c in sorted(agg.items(), key=lambda x: -x[1])[:a.limit]:
                print(f"  {str(path)[:38].ljust(38)} {str(meth).ljust(7)} "
                      f"{str(st).ljust(6)} {c:>8,}")
            lead_hits = sum(c for (pth, _, st), c in agg.items()
                            if pth and "/api/lead" in pth and str(st) == "200")
            if lead_hits:
                print(f"\n  /api/lead 200s: {lead_hits:,}  <- server-side submits, "
                      "INCLUDING chat_answer\n  posts. Not a lead count. Reconcile "
                      "against /check-crm, which is truth.")

        refs = probe.run("httpRequestsAdaptiveGroups (referers)",
                         q_referers(zone, start_dt, end_dt, a.limit),
                         zone_unwrap("httpRequestsAdaptiveGroups"))
        out["referers"] = refs
        if refs:
            agg = {}
            for row in refs:
                k = row["dimensions"].get("clientRefererHost") or "(none/direct)"
                agg[k] = agg.get(k, 0) + row["count"]
            head("REFERER HOST")
            rows(sorted(agg.items(), key=lambda x: -x[1])[:20])
            print("\n  Instagram's in-app browser strips UTMs but usually keeps a "
                  "referer.\n  This is the one place paid IG traffic can be counted "
                  "without a tag.")

    # 4. Pages Functions -- /api/lead invocations ---------------------------
    fns = probe.run("pagesFunctionsInvocationsAdaptiveGroups",
                    q_pages_functions(account, start_dt, end_dt, project),
                    account_unwrap("pagesFunctionsInvocationsAdaptiveGroups"))
    out["functions"] = fns
    if fns:
        total_req = sum(f["sum"]["requests"] for f in fns)
        total_err = sum(f["sum"]["errors"] for f in fns)
        head("PAGES FUNCTIONS (functions/api/lead.js)")
        scripts = sorted({f["dimensions"].get("scriptName", "?") for f in fns})
        print(f"  worker(s)     {', '.join(scripts)}")
        print(f"  invocations   {total_req:>10,}")
        print(f"  errors        {total_err:>10,}")
        if total_err:
            print(f"\n  {total_err:,} FAILED INVOCATIONS. Every one is a submit that "
                  "reached the\n  server and may never have reached Telegram or the "
                  "Sheet. Check\n  /check-crm for the same window before assuming the "
                  "lead landed.")
        else:
            print("\n  No errors -- every submit that reached the edge was processed.")
        by_status = {}
        for f in fns:
            st = f["dimensions"].get("status", "?")
            by_status[st] = by_status.get(st, 0) + f["sum"]["requests"]
        if len(by_status) > 1:
            print()
            rows(sorted(by_status.items(), key=lambda x: -x[1]))

    # 5. what failed --------------------------------------------------------
    if probe.errors:
        head("NOT AVAILABLE ON THIS PLAN / TOKEN")
        for label, err in probe.errors.items():
            print(f"  {label}\n      {err}\n")
        print("  These are Cloudflare's own messages. A 'no such field' means the")
        print("  dataset is not on the Free plan; a permission message means the")
        print("  token is missing a scope -- run: python verify.py")
        print("  Run --list to see exactly what this account can query.")

    if a.as_json:
        sink.close()
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
