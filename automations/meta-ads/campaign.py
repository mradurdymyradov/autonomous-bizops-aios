#!/usr/bin/env python3
"""Create a Meta ad campaign for voronka.tm via the Marketing API.

Builds the full stack in one run: campaign -> ad set -> creative -> ad.

TWO SAFETY RULES, both deliberate:
  1. Nothing is created unless you pass --create. Without it you get a dry run
     that prints every payload so you can read what would be sent.
  2. Everything is created PAUSED. Nothing spends until you flip it on in Ads
     Manager yourself. This script never starts spend.

Usage:
  python campaign.py --image ../ig-poster/p2.png \\
      --headline "Инстаграм есть, а клиентов нет?" \\
      --primary-text "..." --budget 5

  ...read the dry run, then add --create.
"""
import argparse
import base64
import json
import mimetypes
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
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


def graph(method, path, token, version, data=None, tries=3):
    """Call a Graph endpoint. Retries network faults but not Meta's own errors."""
    url = f"https://graph.facebook.com/{version}/{path}"
    ctx = ssl.create_default_context()
    body = urllib.parse.urlencode(data or {}).encode() if method == "POST" else None
    if method == "GET" and data:
        url += "?" + urllib.parse.urlencode(data)

    last = None
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        if body:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Meta answered. It's a real error, retrying won't change it.
            raw = e.read().decode("utf-8", "replace")
            try:
                return json.loads(raw)
            except ValueError:
                return {"error": {"message": raw, "code": e.code}}
        except Exception as e:  # VPN drop, timeout, TLS
            last = e
            if attempt < tries:
                time.sleep(2 * attempt)
    return {"error": {"message": f"network failed after {tries} tries: {last}"}}


def must(resp, what):
    """Abort loudly rather than continue building on a failed parent object."""
    if isinstance(resp, dict) and "error" in resp:
        e = resp["error"]
        print(f"\n!! {what} FAILED")
        print(f"   {e.get('message')}")
        if e.get("error_user_msg"):
            print(f"   {e['error_user_msg']}")
        sys.exit(1)
    return resp


def upload_image(path, env, token, version, dry):
    """Upload a local image, return its hash. Ads reference images by hash."""
    p = Path(path)
    if not p.exists():
        sys.exit(f"image not found: {p}")
    if dry:
        print(f"  [dry] would upload {p.name} ({p.stat().st_size // 1024} KB)")
        return "<image_hash_pending>"

    raw = base64.b64encode(p.read_bytes()).decode()
    resp = graph("POST", f"{env['META_AD_ACCOUNT_ID']}/adimages", token, version,
                 {"bytes": raw, "name": p.name})
    must(resp, "image upload")
    images = resp.get("images", {})
    if not images:
        sys.exit(f"upload returned no image: {resp}")
    h = list(images.values())[0]["hash"]
    print(f"  uploaded {p.name} -> {h}")
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="creative image (1:1 or 4:5 works best)")
    ap.add_argument("--headline", required=True, help="ad headline, Russian")
    ap.add_argument("--primary-text", required=True, help="body copy, Russian")
    ap.add_argument("--description", default="", help="optional link description")
    ap.add_argument("--link", default="https://voronkatm.com")
    ap.add_argument("--cta", default="LEARN_MORE",
                    help="LEARN_MORE, SIGN_UP, GET_QUOTE, CONTACT_US")
    ap.add_argument("--budget", type=float, default=5.0, help="USD (default 5/day)")
    ap.add_argument("--budget-type", choices=["daily", "lifetime"], default="daily")
    ap.add_argument("--end-date", help="YYYY-MM-DD, required for lifetime budget")
    ap.add_argument("--countries", default="TM", help="comma-separated country codes")
    ap.add_argument("--age-min", type=int, default=18)
    ap.add_argument("--age-max", type=int, default=65)
    ap.add_argument("--name", default="", help="campaign name suffix")
    ap.add_argument("--no-ig", action="store_true", help="skip Instagram identity")
    ap.add_argument("--create", action="store_true",
                    help="actually create. Without this it's a dry run.")
    args = ap.parse_args()

    if args.budget_type == "lifetime" and not args.end_date:
        sys.exit("--budget-type lifetime requires --end-date YYYY-MM-DD")

    env = load_env(ENV)
    token = env.get("META_ADS_ACCESS_TOKEN", "")
    if not token:
        sys.exit("META_ADS_ACCESS_TOKEN empty. Run verify.py first.")
    v = env["GRAPH_VERSION"]
    acct = env["META_AD_ACCOUNT_ID"]
    dry = not args.create

    tag = args.name or uuid.uuid4().hex[:6]
    cents = int(round(args.budget * 100))

    print("=" * 60)
    print("DRY RUN — nothing will be created. Add --create to execute."
          if dry else "CREATING (everything PAUSED)")
    print("=" * 60)
    print(f"account : {acct}  ({env.get('GRAPH_VERSION')})")
    print(f"budget  : ${args.budget:.2f} {args.budget_type}")
    print(f"geo     : {args.countries}  age {args.age_min}-{args.age_max}")
    print(f"link    : {args.link}\n")

    # ---- 1. campaign -------------------------------------------------
    # OUTCOME_TRAFFIC, not OUTCOME_LEADS: a cold pixel can't feed conversion
    # optimization on a small budget. See SKILL.md for when to switch.
    campaign_payload = {
        "name": f"voronka | audit-call | {tag}",
        "objective": "OUTCOME_TRAFFIC",
        "status": "PAUSED",
        "special_ad_categories": json.dumps([]),
        # Required whenever budget sits on the ad set instead of the campaign.
        # Meta rejects the whole call without it. Confirmed via validate_only.
        "is_adset_budget_sharing_enabled": "false",
    }
    print("1. campaign")
    print(f"   {json.dumps(campaign_payload, ensure_ascii=False, indent=6)}")
    if dry:
        campaign_id = "<campaign_id_pending>"
    else:
        r = must(graph("POST", f"{acct}/campaigns", token, v, campaign_payload), "campaign")
        campaign_id = r["id"]
        print(f"   -> {campaign_id}")

    # ---- 2. ad set ---------------------------------------------------
    targeting = {
        "geo_locations": {"countries": args.countries.split(",")},
        "age_min": args.age_min,
        "age_max": args.age_max,
    }
    adset_payload = {
        "name": f"voronka | {args.countries} broad | {tag}",
        "campaign_id": campaign_id,
        "status": "PAUSED",
        "billing_event": "IMPRESSIONS",
        # LANDING_PAGE_VIEWS over LINK_CLICKS: pays for people who actually
        # loaded the page, filters out accidental/bounce clicks.
        "optimization_goal": "LANDING_PAGE_VIEWS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "destination_type": "WEBSITE",
        "promoted_object": json.dumps({"pixel_id": env["META_PIXEL_ID"]}),
        "targeting": json.dumps(targeting),
    }
    if args.budget_type == "daily":
        adset_payload["daily_budget"] = cents
    else:
        adset_payload["lifetime_budget"] = cents
        adset_payload["end_time"] = f"{args.end_date}T23:59:59+0500"  # Asia/Ashgabat

    print("\n2. ad set")
    print(f"   {json.dumps(adset_payload, ensure_ascii=False, indent=6)}")
    if dry:
        adset_id = "<adset_id_pending>"
    else:
        r = must(graph("POST", f"{acct}/adsets", token, v, adset_payload), "ad set")
        adset_id = r["id"]
        print(f"   -> {adset_id}")

    # ---- 3. creative -------------------------------------------------
    print("\n3. creative")
    image_hash = upload_image(args.image, env, token, v, dry)

    link_data = {
        "image_hash": image_hash,
        "link": args.link,
        "message": args.primary_text,
        "name": args.headline,
        "call_to_action": {"type": args.cta, "value": {"link": args.link}},
    }
    if args.description:
        link_data["description"] = args.description

    story = {"page_id": env["META_PAGE_ID"], "link_data": link_data}
    if not args.no_ig and env.get("META_IG_ACCOUNT_ID"):
        # instagram_actor_id is rejected ("must be a valid Instagram account id");
        # instagram_user_id passes field validation. Not yet fully confirmed --
        # the app-mode error masks this check until the app is Live.
        story["instagram_user_id"] = env["META_IG_ACCOUNT_ID"]

    creative_payload = {
        "name": f"voronka | creative | {tag}",
        "object_story_spec": json.dumps(story, ensure_ascii=False),
    }
    print(f"   {json.dumps(story, ensure_ascii=False, indent=6)}")
    if dry:
        creative_id = "<creative_id_pending>"
    else:
        r = must(graph("POST", f"{acct}/adcreatives", token, v, creative_payload), "creative")
        creative_id = r["id"]
        print(f"   -> {creative_id}")

    # ---- 4. ad -------------------------------------------------------
    ad_payload = {
        "name": f"voronka | ad | {tag}",
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    }
    print("\n4. ad")
    print(f"   {json.dumps(ad_payload, ensure_ascii=False, indent=6)}")
    if dry:
        print("\nDry run complete. Re-run with --create to build it.")
        return 0

    r = must(graph("POST", f"{acct}/ads", token, v, ad_payload), "ad")
    ad_id = r["id"]
    print(f"   -> {ad_id}")

    acct_num = acct.replace("act_", "")
    print("\n" + "=" * 60)
    print("CREATED, ALL PAUSED. Nothing is spending.")
    print(f"  campaign {campaign_id}")
    print(f"  ad set   {adset_id}")
    print(f"  creative {creative_id}")
    print(f"  ad       {ad_id}")
    print("\nReview it, then turn it on yourself:")
    print(f"  https://adsmanager.facebook.com/adsmanager/manage/campaigns"
          f"?act={acct_num}&selected_campaign_ids={campaign_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
