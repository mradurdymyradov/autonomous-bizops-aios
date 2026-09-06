#!/usr/bin/env python3
"""Verify the Meta Ads system-user token actually works before we build on it.

Checks, in order:
  1. Which scopes the token really carries (the UI warns about some, but silently
     drops others -- only debug_token tells the truth).
  2. Ad account: reachable, active, and has a real funding source.
  3. Page: reachable (every ad creative needs it).
  4. Pixel: reachable (the ad set's conversion source).
  5. Instagram account linked to the Page (IG-first funnel).

Token is sent as a Bearer header, never in the URL, so it stays out of logs.
Run:  python verify.py
"""
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV = Path(__file__).parent / ".env"

# Scopes we actually need. Anything missing here is a hard blocker.
REQUIRED = ["ads_management", "ads_read", "business_management"]
# Nice to have. Missing these limits creative options but not campaign creation.
WANTED = ["pages_read_engagement", "pages_manage_ads", "instagram_basic"]


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
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # A 4xx is a real answer from Meta, not a network blip. Don't retry it.
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
        return f"{e.get('message', e)}"
    return None


def main():
    env = load_env(ENV)
    token = env.get("META_ADS_ACCESS_TOKEN", "")
    if not token:
        sys.exit("META_ADS_ACCESS_TOKEN is empty in .env")

    v = env.get("GRAPH_VERSION", "v21.0")
    acct = env.get("META_AD_ACCOUNT_ID", "")
    page = env.get("META_PAGE_ID", "")
    pixel = env.get("META_PIXEL_ID", "")

    ok = True

    # 1. real scopes
    print("=== 1. token scopes ===")
    d = get("debug_token", token, v, {"input_token": token})
    if e := err(d):
        print(f"  ! debug_token failed: {e}")
        ok = False
        granted = []
    else:
        data = d.get("data", {})
        granted = data.get("scopes", [])
        expires = data.get("expires_at", 0)
        print(f"  type      : {data.get('type')}")
        print(f"  app_id    : {data.get('app_id')}")
        print(f"  valid     : {data.get('is_valid')}")
        print(f"  expires_at: {'NEVER' if expires == 0 else expires}")
        print(f"  scopes    : {', '.join(sorted(granted)) or '(none)'}")

    missing_req = [s for s in REQUIRED if s not in granted]
    missing_opt = [s for s in WANTED if s not in granted]
    if missing_req:
        print(f"  ! BLOCKER, missing required: {', '.join(missing_req)}")
        ok = False
    if missing_opt:
        print(f"  ~ missing optional: {', '.join(missing_opt)}")

    # 2. ad account + funding
    print("\n=== 2. ad account ===")
    a = get(acct, token, v, {
        "fields": "name,account_status,disable_reason,currency,timezone_name,"
                  "funding_source_details,balance,amount_spent,business"
    })
    if e := err(a):
        print(f"  ! {e}")
        ok = False
    else:
        # 1 = ACTIVE. Anything else means ads won't deliver.
        status = a.get("account_status")
        print(f"  name     : {a.get('name')}")
        print(f"  status   : {status} {'(ACTIVE)' if status == 1 else '(NOT ACTIVE)'}")
        print(f"  currency : {a.get('currency')}")
        print(f"  timezone : {a.get('timezone_name')}")
        fund = a.get("funding_source_details")
        print(f"  funding  : {fund if fund else '!! NONE ON FILE'}")
        if status != 1:
            print(f"  ! account not active, disable_reason={a.get('disable_reason')}")
            ok = False
        if not fund:
            print("  ! no funding source, campaigns will fail to publish")
            ok = False

    # 3. page
    print("\n=== 3. page ===")
    p = get(page, token, v, {"fields": "name,id,instagram_business_account"})
    if e := err(p):
        print(f"  ! {e}")
        ok = False
    else:
        print(f"  name: {p.get('name')} ({p.get('id')})")
        iga = p.get("instagram_business_account", {})
        if iga:
            print(f"  ig  : {iga.get('id')}")
            print(f"  -> add to .env:  META_IG_ACCOUNT_ID={iga.get('id')}")
        else:
            print("  ~ no IG business account linked to this Page")

    # 4. pixel
    print("\n=== 4. pixel ===")
    px = get(pixel, token, v, {"fields": "name,id,last_fired_time,is_unavailable"})
    if e := err(px):
        print(f"  ! {e}")
        ok = False
    else:
        print(f"  name      : {px.get('name')} ({px.get('id')})")
        print(f"  last fired: {px.get('last_fired_time', 'never')}")

    print("\n" + ("PASS - safe to build on" if ok else "FAIL - fix the ! lines above"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
