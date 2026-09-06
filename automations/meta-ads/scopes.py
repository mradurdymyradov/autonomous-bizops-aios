#!/usr/bin/env python3
"""Snapshot what both Meta tokens can still do. Run BEFORE and AFTER trimming
app use cases, then diff the output.

Removing a use case strips its permissions from the app, and already-minted
tokens silently lose those scopes -- the token stays "valid" but calls start
failing. Two separate tokens are at risk, minted at different times for
different jobs:

  ../ig-poster/.env  IG_ACCESS_TOKEN        permanent PAGE token   (publishing)
  ./.env             META_ADS_ACCESS_TOKEN  system user token      (ads)

Each is checked two ways: the scope list Meta reports, and one real read call
per automation. Scopes can look intact while access is gone, so the live call
is the one that actually settles it.

Usage:  python scopes.py           # run, save the output, trim, run again
"""
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent

# What each automation genuinely needs. Anything here that disappears after a
# trim means we removed a use case we depended on.
NEEDED = {
    "ads": ["ads_management", "ads_read", "business_management",
            "pages_read_engagement", "pages_manage_ads"],
    "ig": ["instagram_basic", "instagram_content_publish",
           "pages_show_list", "pages_read_engagement", "business_management"],
}


def load_env(path):
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def get(path, token, version, params=None, tries=3):
    """GET a Graph endpoint. Retries the network, never Meta's own 4xx."""
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
            try:
                return json.loads(e.read().decode("utf-8", "replace"))
            except ValueError:
                return {"error": {"message": f"HTTP {e.code}"}}
        except Exception as e:  # VPN drop / timeout / TLS
            last = e
            if attempt < tries:
                time.sleep(2 * attempt)
    return {"error": {"message": f"network failed after {tries} tries: {last}"}}


def report(label, token, version, needed, live_call):
    print(f"\n{'=' * 58}\n{label}\n{'=' * 58}")
    if not token:
        print("  !! no token in .env -- skipped")
        return

    d = get("debug_token", token, version, {"input_token": token}).get("data", {})
    if not d:
        print("  !! debug_token returned nothing. Token may be dead.")
        return

    scopes = sorted(d.get("scopes", []))
    exp = d.get("expires_at", 0)
    print(f"  valid   : {d.get('is_valid')}")
    print(f"  expires : {'NEVER' if exp == 0 else exp}")
    print(f"  scopes  : {len(scopes)}")
    for s in scopes:
        print(f"      {s}")

    missing = [p for p in needed if p not in scopes]
    print("\n  required scopes:")
    for p in needed:
        print(f"      {'ok  ' if p not in missing else 'GONE'}  {p}")

    # Scopes are a claim; this is the proof.
    name, path, params = live_call
    resp = get(path, token, version, params)
    if "error" in resp:
        print(f"\n  !! LIVE CHECK FAILED ({name}): {resp['error'].get('message')}")
    else:
        print(f"\n  live check ok ({name})")

    if missing:
        print(f"\n  !! {len(missing)} required scope(s) GONE -- this automation is broken")


def main():
    ads = load_env(HERE / ".env")
    ig = load_env(HERE.parent / "ig-poster" / ".env")
    v = ads.get("GRAPH_VERSION", "v21.0")

    report(
        "ADS  (meta-ads/.env -> campaign.py, verify.py)",
        ads.get("META_ADS_ACCESS_TOKEN", ""), v, NEEDED["ads"],
        ("read ad account", ads.get("META_AD_ACCOUNT_ID", "me"),
         {"fields": "name,account_status"}),
    )
    report(
        "IG   (ig-poster/.env -> post.py)",
        ig.get("IG_ACCESS_TOKEN", ""), ig.get("GRAPH_VERSION", v), NEEDED["ig"],
        ("read IG account", ig.get("IG_USER_ID", "me"),
         {"fields": "username,followers_count"}),
    )
    print("\nSave this output. Re-run after trimming use cases and compare.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
