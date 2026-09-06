#!/usr/bin/env python3
"""Health-check the Cloudflare connection. Fails loudly on the exact broken line.

Run:  python verify.py

Checks, in order:
  1. .env exists and the keys are filled
  2. Cloudflare accepts the token at all
  3. the token can read the zone (voronkatm.com)
  4. the token can read the account
  5. GraphQL analytics answers for the zone
  6. the Pages project is visible (optional -- only gates /api/lead numbers)
  7. there is actual traffic in the last 7 days
"""
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("missing lib. run:  python -m pip install requests")

ENV = Path(__file__).parent / ".env"
REST = "https://api.cloudflare.com/client/v4"
GQL = "https://api.cloudflare.com/client/v4/graphql"
OK, BAD, WARN = "  OK  ", " FAIL ", " NOTE "

TOKEN_RECIPE = """create the token at
         https://dash.cloudflare.com/profile/api-tokens -> Create Token
         -> Create Custom Token, with these four permissions:
              Zone    | Analytics         | Read
              Zone    | Zone              | Read
              Account | Account Analytics | Read
              Account | Pages             | Read
         Zone Resources:    Include -> Specific zone -> voronkatm.com
         Account Resources: Include -> your account
         Then paste it into automations/cloudflare/.env as CF_API_TOKEN"""


def step(n, what):
    print(f"\n[{n}] {what}")


def die(msg, fix):
    print(f"{BAD} {msg}")
    print(f"       fix: {fix}")
    sys.exit(1)


def get(path, token):
    try:
        return requests.get(f"{REST}{path}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=45).json()
    except requests.RequestException as e:
        die(f"network: {e}",
            "the VPN tunnel is 2-4 Mb/s and drops. Retry before suspecting the code.")
    except ValueError:
        die("Cloudflare returned a non-JSON body",
            "usually a captive portal or the VPN dropping mid-request. Retry.")


def first_error(blob):
    errs = blob.get("errors") or []
    if not errs:
        return ""
    e = errs[0]
    return f"{e.get('code', '?')}: {e.get('message', e)}"


def main():
    print("=" * 72)
    print("Cloudflare connection check -- voronkatm.com")
    print("=" * 72)

    # 1 -----------------------------------------------------------------
    step(1, ".env file and keys")
    if not ENV.exists():
        die(f"no {ENV}",
            "copy .env.example to .env and fill it in (README step 1)")
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    token = env.get("CF_API_TOKEN", "")
    if not token or token.startswith("<"):
        die("CF_API_TOKEN is empty", TOKEN_RECIPE)
    print(f"{OK} CF_API_TOKEN = {token[:6]}...{token[-4:]} ({len(token)} chars)")

    zone = env.get("CF_ZONE_ID", "")
    if not zone or zone.startswith("<"):
        die("CF_ZONE_ID is empty",
            "dash.cloudflare.com -> voronkatm.com -> Overview -> right column, "
            "'Zone ID'. A 32-char hex string.")
    account = env.get("CF_ACCOUNT_ID", "")
    if not account or account.startswith("<"):
        die("CF_ACCOUNT_ID is empty",
            "same Overview page, right column, 'Account ID'. Also 32-char hex.")
    if zone == account:
        die("CF_ZONE_ID and CF_ACCOUNT_ID are the same value",
            "they are two different IDs on the same panel. Re-copy both.")
    print(f"{OK} CF_ZONE_ID    = {zone}")
    print(f"{OK} CF_ACCOUNT_ID = {account}")
    project = env.get("CF_PAGES_PROJECT", "").strip()
    print(f"{OK} CF_PAGES_PROJECT = {project or '(unset -- step 6 will be skipped)'}")

    # 2 -----------------------------------------------------------------
    step(2, "does Cloudflare accept the token")
    v = get("/user/tokens/verify", token)
    if not v.get("success"):
        die(f"token rejected -- {first_error(v)}",
            "the token is wrong, revoked, or you pasted the Global API Key "
            "instead of an API token.\n            " + TOKEN_RECIPE)
    print(f"{OK} token is {v.get('result', {}).get('status', 'active')}")

    # 3 -----------------------------------------------------------------
    step(3, "can the token read the zone")
    z = get(f"/zones/{zone}", token)
    if not z.get("success"):
        err = first_error(z)
        if "9109" in err or "Unauthorized" in err or "authentication" in err.lower():
            die(f"zone not readable -- {err}",
                "the token is missing Zone|Zone|Read, or the zone is not in its "
                "Zone Resources.\n            " + TOKEN_RECIPE)
        die(f"zone lookup failed -- {err}", "check CF_ZONE_ID on the Overview page")
    name = z["result"].get("name")
    plan = (z["result"].get("plan") or {}).get("name", "?")
    print(f"{OK} zone: {name}  |  plan: {plan}")
    if name and "voronkatm" not in name:
        print(f"{WARN} that is not voronkatm.com -- you wired up the wrong zone")
    if "free" in plan.lower():
        print(f"{WARN} Free plan: daily zone analytics work; the per-path 'adaptive'")
        print("       datasets may be restricted or short-retention. That is a plan")
        print("       limit, not a broken setup. report.py degrades section by section.")

    # 4 -----------------------------------------------------------------
    step(4, "can the token read account analytics")
    # NOT /accounts/{id} -- that REST endpoint needs Account|Account Settings|Read,
    # a scope this token deliberately does not carry. The thing that actually
    # matters is whether the account GraphQL container answers.
    acc_q = """
    { viewer { accounts(filter: {accountTag: "%s"}) { accountTag } } }""" % account
    try:
        ar = requests.post(GQL,
                           headers={"Authorization": f"Bearer {token}",
                                    "Content-Type": "application/json"},
                           json={"query": acc_q}, timeout=60).json()
    except (requests.RequestException, ValueError) as e:
        ar = {"errors": [{"message": str(e)}]}
    if ar.get("errors") or not (ar.get("data") or {}).get("viewer", {}).get("accounts"):
        msg = "; ".join(e.get("message", str(e)) for e in ar.get("errors") or [])
        print(f"{WARN} account analytics not readable -- {msg[:160] or 'empty container'}")
        print("       Only affects the Pages Functions section (/api/lead counts).")
        print("       Add Account|Account Analytics|Read to the token.")
    else:
        print(f"{OK} account analytics readable")

    # 5 -----------------------------------------------------------------
    step(5, "GraphQL analytics for this zone")
    start = (date.today() - timedelta(days=6)).isoformat()
    end = date.today().isoformat()
    query = """
    { viewer { zones(filter: {zoneTag: "%s"}) {
        httpRequests1dGroups(limit: 10, filter: {date_geq: "%s", date_leq: "%s"}) {
          dimensions { date }
          sum { requests pageViews }
          uniq { uniques }
    } } } }""" % (zone, start, end)
    try:
        r = requests.post(GQL,
                          headers={"Authorization": f"Bearer {token}",
                                   "Content-Type": "application/json"},
                          json={"query": query}, timeout=60).json()
    except (requests.RequestException, ValueError) as e:
        die(f"GraphQL call failed: {e}", "retry -- the tunnel drops")
    if r.get("errors"):
        msg = "; ".join(e.get("message", str(e)) for e in r["errors"])
        die(f"GraphQL refused: {msg[:300]}",
            "almost always Zone|Analytics|Read missing from the token.\n"
            "            " + TOKEN_RECIPE)
    try:
        days = r["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]
    except (KeyError, IndexError, TypeError):
        die("GraphQL answered but returned no zone container",
            "CF_ZONE_ID is valid hex but not a zone this token can see")
    print(f"{OK} GraphQL answered -- {len(days)} day buckets")

    # 6 -----------------------------------------------------------------
    step(6, "Pages project (optional)")
    if not project:
        print(f"{WARN} CF_PAGES_PROJECT unset -- skipping. Set it to the project name")
        print("       shown at dash -> Workers & Pages (it is 'voronka') to get")
        print("       /api/lead invocation counts.")
    else:
        pr = get(f"/accounts/{account}/pages/projects/{project}", token)
        if not pr.get("success"):
            print(f"{WARN} project '{project}' not readable -- {first_error(pr)}")
            print("       Add Account|Pages|Read, or fix the project name.")
        else:
            res = pr["result"]
            print(f"{OK} Pages project '{res.get('name')}'")
            domains = res.get("domains") or []
            if domains:
                print(f"       domains: {', '.join(domains[:5])}")

    # 7 -----------------------------------------------------------------
    step(7, "is there actual traffic")
    total = sum(d["sum"]["requests"] for d in days)
    pv = sum(d["sum"]["pageViews"] for d in days)
    if not total:
        print(f"{BAD} zero requests in the last 7 days")
        print("       Auth passed, so this is not a credential problem. Either the")
        print("       domain is not proxied through Cloudflare (orange cloud off),")
        print("       or nothing has visited. Check dash -> DNS.")
        return 1
    print(f"{OK} {total:,} requests / {pv:,} page views in 7 days")
    for d in days:
        print(f"         {d['dimensions']['date']}  {d['sum']['requests']:>7,} req  "
              f"{d['sum']['pageViews']:>6,} pv  {d['uniq']['uniques']:>5,} uniq")

    print("\n" + "=" * 72)
    print("ALL CHECKS PASSED. Run:  python report.py --days 7")
    print("Compare page views against /check-ads link clicks and /check-ga4 sessions.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
