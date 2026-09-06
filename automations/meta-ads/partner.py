#!/usr/bin/env python3
"""Is a partner's Business Portfolio verified, and what does it actually give us?

Answers the one question that gates `campaign.py` (see ../CAPABILITIES.md §2A):
a *verified* Business Portfolio can claim our app `automation_1`, which publishes
it, which unblocks ad-creative creation.

Read-only. Creates nothing, grants nothing, spends nothing.

It needs a token that has a role in the partner's portfolio. Three ways to get one,
cheapest first -- the full procedure is in partner-portfolio.md:
  1. she adds The Facebook user to her portfolio -> use a user token
  2. she creates a system user in her portfolio -> use that token
  3. she reads the status off her own screen and we skip this script entirely

Usage:
    python partner.py --business-id <her portfolio id>          # token from partner.env
    python partner.py --business-id <id> --token <token>
    python partner.py --list                                    # what can this token see at all?
    python partner.py --ours                                    # our own portfolio, as a control
"""
import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# The Windows console defaults to cp1251 here, which mangles Cyrillic portfolio
# names and the § in "§2A" into garbage. Force UTF-8 out.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

HERE = Path(__file__).parent
ENV = HERE / ".env"              # ours: META_ADS_ACCESS_TOKEN, META_BUSINESS_ID, META_APP_ID
PARTNER_ENV = HERE / "partner.env"  # hers: PARTNER_TOKEN, PARTNER_BUSINESS_ID. Gitignored.

# Business node fields. Meta rejects the whole request when one field is unknown,
# so an error on the batch triggers a per-field probe instead of a blank verdict.
# `is_disabled_for_integrity_reasons` is deliberately absent -- confirmed nonexistent
# on the Business node 2026-08-04, it only cost a wasted probe call.
BIZ_FIELDS = [
    "id", "name", "verification_status", "created_time", "vertical",
    "primary_page", "two_factor_type", "link", "timezone_id",
]

# What `verification_status` means. Only one of these unblocks anything.
VERDICT = {
    "verified": ("VERIFIED", "This portfolio can claim our app. Proceed to partner-portfolio.md step 4."),
    "not_verified": ("NOT verified", "Same wall as ours. Nothing to gain -- do not restructure anything."),
    "pending": ("pending review", "Documents submitted, Meta hasn't ruled. Re-run in a few days."),
    "pending_need_more_info": ("pending, needs more info", "Meta asked her for another document. Stalled until she sends it."),
    "pending_submission": ("not submitted", "She started and stopped. She holds the documents; ask her to finish."),
    "failed": ("FAILED review", "Meta rejected her documents. Treat as not verified."),
    "expired": ("expired", "Was verified, lapsed. She can re-verify -- she has the documents."),
    "revoked": ("revoked", "Meta pulled it. Treat as not verified and do not attach our app."),
    "not_eligible": ("not eligible", "Dead end for this portfolio."),
}


def load_env(path):
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
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
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # A 4xx is Meta's real answer, not a network blip. Don't retry it.
            body = e.read().decode("utf-8", "replace")
            try:
                return json.loads(body)
            except ValueError:
                return {"error": {"message": body, "code": e.code}}
        except Exception as e:  # timeouts, DNS, TLS -- the VPN
            last = e
            if attempt < tries:
                time.sleep(2 * attempt)
    return {"error": {"message": f"network failed after {tries} tries: {last}"}}


def err(resp):
    if isinstance(resp, dict) and "error" in resp:
        e = resp["error"]
        code = e.get("code")
        sub = e.get("error_subcode")
        msg = e.get("message", str(e))
        tail = f" [code {code}{'/' + str(sub) if sub else ''}]" if code else ""
        return msg + tail
    return None


def fetch_fields(node, token, version, fields):
    """Ask for everything; if Meta rejects the batch, probe field by field.

    A single unknown field 400s the whole request, which reads like "no access"
    and isn't. Probing tells us which fields are missing vs which are forbidden.
    """
    resp = get(node, token, version, {"fields": ",".join(fields)})
    if not err(resp):
        return resp, []
    out, dead = {}, []
    for f in fields:
        r = get(node, token, version, {"fields": f})
        if e := err(r):
            dead.append((f, e))
        else:
            out.update(r)
    return out, dead


def show_business(biz, dead):
    print(f"  id         : {biz.get('id')}")
    print(f"  name       : {biz.get('name')}")
    print(f"  created    : {biz.get('created_time')}")
    print(f"  vertical   : {biz.get('vertical')}")
    print(f"  2FA        : {biz.get('two_factor_type')}")
    if biz.get("is_disabled_for_integrity_reasons"):
        print("  ! portfolio is DISABLED for integrity reasons -- unusable regardless of verification")
    raw = biz.get("verification_status")
    print(f"  verification_status: {raw!r}")
    if raw is None:
        print("  ? Meta did not return the field. Either the token lacks business_management,")
        print("    or the role is too low. See the field errors below and partner-portfolio.md step 3.")
    else:
        label, meaning = VERDICT.get(str(raw).lower(), (str(raw), "Unrecognised value -- record it in partner-portfolio.md."))
        print(f"  -> {label}: {meaning}")
    for f, e in dead:
        print(f"  ~ field {f}: {e}")
    return str(biz.get("verification_status") or "").lower()


def edge(label, node, edge_name, token, version, fields, limit=25):
    r = get(f"{node}/{edge_name}", token, version, {"fields": fields, "limit": limit})
    if e := err(r):
        print(f"  {label}: -- {e}")
        return []
    rows = r.get("data", [])
    if not rows:
        print(f"  {label}: none")
        return []
    print(f"  {label}: {len(rows)}")
    for row in rows:
        bits = [f"{k}={v}" for k, v in row.items() if k != "id"]
        print(f"    - {row.get('id')}  {'  '.join(bits)}")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--business-id", help="the partner's Business Portfolio ID")
    ap.add_argument("--token", help="a token with a role in that portfolio (else PARTNER_TOKEN in partner.env)")
    ap.add_argument("--list", action="store_true", help="list every portfolio this token can see, then stop")
    ap.add_argument("--ours", action="store_true", help="run against our own portfolio as a control")
    ap.add_argument("--assets", action="store_true", help="also enumerate ad accounts / pages / system users")
    args = ap.parse_args()

    ours = load_env(ENV)
    theirs = load_env(PARTNER_ENV)
    version = ours.get("GRAPH_VERSION", "v21.0")

    if args.ours:
        token = ours.get("META_ADS_ACCESS_TOKEN", "")
        biz_id = ours.get("META_BUSINESS_ID", "")
        who = "OURS (control)"
    else:
        token = args.token or theirs.get("PARTNER_TOKEN", "") or ours.get("META_ADS_ACCESS_TOKEN", "")
        biz_id = args.business_id or theirs.get("PARTNER_BUSINESS_ID", "")
        who = "PARTNER"

    if not token:
        sys.exit("no token: pass --token, or put PARTNER_TOKEN in partner.env")

    print(f"=== 0. whose token is this ===")
    d = get("debug_token", token, version, {"input_token": token})
    if e := err(d):
        print(f"  ! debug_token failed: {e}")
        scopes = []
    else:
        data = d.get("data", {})
        scopes = data.get("scopes", [])
        print(f"  type   : {data.get('type')}")
        print(f"  app_id : {data.get('app_id')}")
        print(f"  user_id: {data.get('user_id')}")
        print(f"  valid  : {data.get('is_valid')}")
        print(f"  scopes : {', '.join(sorted(scopes)) or '(none)'}")
    if "business_management" not in scopes:
        print("  ! business_management is MISSING -- verification_status will come back empty.")
        print("    This is a token problem, not an access problem. Reissue with that scope.")

    print("\n=== 1. portfolios this token has a role in ===")
    me = get("me/businesses", token, version, {"fields": "id,name,verification_status", "limit": 50})
    if e := err(me):
        print(f"  ! {e}")
        seen = []
    else:
        seen = me.get("data", [])
        if not seen:
            print("  none.")
            if str(d.get("data", {}).get("type", "")).upper() == "SYSTEM_USER":
                # Verified 2026-08-04: our own system-user token returns [] here while
                # reading its own portfolio in step 2 perfectly well. Empty is not a verdict.
                print("  (expected -- /me/businesses is empty for SYSTEM_USER tokens by design.")
                print("   Step 2 below is the real test. Use a USER token to enumerate portfolios.)")
            else:
                print("  This token has no Business Portfolio role at all.")
        for b in seen:
            print(f"  - {b.get('id')}  {b.get('name')}  [{b.get('verification_status')}]")
    if args.list:
        return 0

    if not biz_id:
        print("\nno --business-id given. Pick one from the list above and re-run.")
        return 1

    print(f"\n=== 2. {who} portfolio {biz_id} ===")
    biz, dead = fetch_fields(biz_id, token, version, BIZ_FIELDS)
    if not biz:
        print("  ! nothing readable. Most likely the token has no role in this portfolio.")
        print("    That is the expected result before she grants access -- it is not a bug.")
        return 1
    status = show_business(biz, dead)

    if args.assets:
        print(f"\n=== 3. what the portfolio owns ===")
        edge("ad accounts", biz_id, "owned_ad_accounts", token, version,
             "name,account_status,currency,funding_source_details")
        edge("client ad accounts", biz_id, "client_ad_accounts", token, version, "name,account_status,currency")
        edge("pages", biz_id, "owned_pages", token, version, "name,instagram_business_account")
        edge("system users", biz_id, "system_users", token, version, "name,role")
        edge("owned apps", biz_id, "owned_apps", token, version, "name")

    app_id = ours.get("META_APP_ID", "")
    if app_id:
        print(f"\n=== 4. our app {app_id} -- which portfolio is it attached to? ===")
        a, adead = fetch_fields(app_id, token, version, ["id", "name", "company", "link"])
        if a:
            for k, val in a.items():
                print(f"  {k}: {val}")
        for f, e in adead:
            print(f"  ~ field {f}: {e}")
        print("  note: the app's business attachment is only fully readable with an app token")
        print("        or in the App Dashboard -- Settings > Basic > Verification. Check it there.")

    print("\n=== verdict ===")
    if status == "verified":
        print("  Her portfolio IS verified.")
        print("  This is the §2A unlock -- but only if she attaches app automation_1 to it.")
        print("  Partner access to her AD ACCOUNT alone changes nothing: the creative block")
        print("  lives on our app, not on any ad account. Read partner-portfolio.md before")
        print("  touching anything in Business Settings.")
    elif status:
        print(f"  Not usable for the §2A unlock (status: {status}).")
    else:
        print("  Inconclusive -- the field never came back. Fix the access first, then re-run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
