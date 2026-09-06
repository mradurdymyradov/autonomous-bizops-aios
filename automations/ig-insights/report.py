#!/usr/bin/env python3
"""Read everything the Instagram Graph API will give us about @voronka.tm.

Read-only. Posts nothing, changes nothing.
Organic sister to ../meta-ads/report.py (paid) and ../ga4/report.py (site).

Credentials are NOT duplicated here. Insights use the system-user token in
../meta-ads/.env; the publishing quota needs the page token in ../ig-poster/.env.

Run:  python report.py [--days 28] [--posts 12] [--competitor natgeo] [--json] [--snapshot]
  --days N        window, Meta caps at 30. Default 28.
  --posts N       how many recent posts to pull, default 12
  --competitor U  business_discovery on a public business/creator account (repeatable)
  --json          machine-readable dump
  --snapshot      append the JSON to history/ -- the only defence against Meta's
                  30-day insight window and the 24h story window
"""
import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
ADS_ENV = HERE.parent / "meta-ads" / ".env"
POSTER_ENV = HERE.parent / "ig-poster" / ".env"
HISTORY = HERE / "history"

# Meta ignores the version in the URL and serves v25.0 for every version we ask for
# -- v18.0 through v25.0 all come back with `facebook-api-version: v25.0` (verified
# 2026-07-26). So ask for what we actually get and test against, rather than pinning
# a number that has no effect. Nothing breaks if this is stale; it just stops lying.
VERSION = "v25.0"

# --- account level -----------------------------------------------------------
# Rejected unless asked for as a single total.
TOTAL_METRICS = [
    "views", "reach", "profile_views", "accounts_engaged", "total_interactions",
    "likes", "comments", "saves", "shares", "replies", "follows_and_unfollows",
    "profile_links_taps", "website_clicks",
]
# (metric, breakdown) pairs that actually return rows on this account.
BREAKDOWNS = [
    ("views", "media_product_type"),
    ("reach", "media_product_type"),
    ("total_interactions", "media_product_type"),
    ("views", "follow_type"),
    ("reach", "follow_type"),
    ("profile_links_taps", "contact_button_type"),
]
DEMOGRAPHIC_METRICS = [
    "follower_demographics", "engaged_audience_demographics", "reached_audience_demographics",
]

# --- media level -------------------------------------------------------------
MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,permalink,timestamp,like_count,"
    "comments_count,is_comment_enabled,shortcode,media_url,boost_eligibility_info,"
    "children{id,media_type,media_url}"
)
# Per media it is `saved`; at account level it is `saves`. Meta does not alias them.
MEDIA_METRICS = [
    "views", "reach", "total_interactions", "likes", "comments", "saved", "shares",
    "profile_visits", "follows", "profile_activity",
]
REEL_METRICS = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
STORY_METRICS = [
    "views", "reach", "replies", "shares", "profile_visits", "follows",
    "total_interactions", "navigation",
]


def load_env():
    """Insights token from meta-ads, page token from ig-poster. Neither is copied here."""
    def parse(path):
        d = {}
        if not path.exists():
            return d
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
        return d

    ads, poster = parse(ADS_ENV), parse(POSTER_ENV)
    token = ads.get("META_ADS_ACCESS_TOKEN") or poster.get("IG_ACCESS_TOKEN")
    ig_id = ads.get("META_IG_ACCOUNT_ID") or poster.get("IG_USER_ID")
    if not token or not ig_id:
        sys.exit(f"No usable credentials. Looked in:\n  {ADS_ENV}\n  {POSTER_ENV}")
    return token, poster.get("IG_ACCESS_TOKEN"), ig_id


def get(path, token, params=None, tries=3):
    """GET a Graph endpoint. Retries -- this runs over a 2-4 Mb/s VPN that drops."""
    url = f"https://graph.facebook.com/{VERSION}/{path}"
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


def rows_from(total_value):
    """Flatten Meta's nested breakdown shape into {dimension: value}."""
    out = {}
    for b in total_value.get("breakdowns", []):
        for res in b.get("results", []):
            out["/".join(res.get("dimension_values", []))] = res.get("value")
    return out


# ---------------------------------------------------------------- account

def fetch_profile(tok, ig):
    return get(ig, tok, {"fields": "username,name,biography,website,followers_count,"
                                   "follows_count,media_count,ig_id,is_published"})


def fetch_totals(tok, ig, since, until):
    """One metric per call on purpose: a batched call dies whole when a single
    metric is unsupported, and the supported set shifts between API versions."""
    out = {}
    for metric in TOTAL_METRICS:
        r = get(f"{ig}/insights", tok, {"metric": metric, "period": "day",
                                        "metric_type": "total_value",
                                        "since": since, "until": until})
        e = err(r)
        if e:
            out[metric] = {"error": e}
            continue
        data = r.get("data") or []
        if not data:
            out[metric] = {"error": "empty -- too little volume"}
            continue
        tv = data[0].get("total_value") or {}
        if "value" in tv:
            out[metric] = {"value": tv["value"]}
        else:
            rows = rows_from(tv)
            out[metric] = {"breakdown": rows} if rows else {"error": "empty"}
    return out


def fetch_breakdowns(tok, ig, since, until):
    out = {}
    for metric, breakdown in BREAKDOWNS:
        r = get(f"{ig}/insights", tok, {"metric": metric, "period": "day",
                                        "metric_type": "total_value", "breakdown": breakdown,
                                        "since": since, "until": until})
        key = f"{metric}/{breakdown}"
        if err(r) or not r.get("data"):
            out[key] = {"error": err(r) or "empty"}
            continue
        rows = rows_from(r["data"][0].get("total_value", {}))
        out[key] = rows or {"error": "empty"}
    return out


def fetch_daily(tok, ig, since, until):
    out = {}
    for metric in ("reach", "follower_count"):
        r = get(f"{ig}/insights", tok, {"metric": metric, "period": "day",
                                        "since": since, "until": until})
        out[metric] = [] if err(r) or not r.get("data") else r["data"][0].get("values", [])
    return out


def fetch_demographics(tok, ig):
    out = {}
    for metric in DEMOGRAPHIC_METRICS:
        out[metric] = {}
        for breakdown in ("country", "city", "age", "gender"):
            r = get(f"{ig}/insights", tok, {"metric": metric, "period": "lifetime",
                                            "metric_type": "total_value",
                                            "timeframe": "this_month", "breakdown": breakdown})
            if err(r) or not r.get("data"):
                # Meta gates these behind ~100 followers. Empty means small, not broken.
                out[metric][breakdown] = {"error": err(r) or "empty -- needs ~100 followers"}
                continue
            rows = rows_from(r["data"][0].get("total_value", {}))
            out[metric][breakdown] = dict(sorted(rows.items(), key=lambda kv: -(kv[1] or 0)))
    return out


# ---------------------------------------------------------------- media

def _media_insights(tok, media_id, metrics):
    """One call per metric. Media types disagree about which metrics exist and a
    single unsupported name 400s the whole batch."""
    out = {}
    for m in metrics:
        r = get(f"{media_id}/insights", tok, {"metric": m})
        if err(r) or not r.get("data"):
            continue
        vals = r["data"][0].get("values") or []
        if vals:
            out[m] = vals[0].get("value")
    return out


def fetch_posts(tok, ig, limit):
    r = get(f"{ig}/media", tok, {"fields": MEDIA_FIELDS, "limit": limit})
    if err(r):
        return [], err(r)
    posts = r.get("data", [])
    for p in posts:
        metrics = list(MEDIA_METRICS)
        if p.get("media_product_type") == "REELS":
            metrics += REEL_METRICS
        p["insights"] = _media_insights(tok, p["id"], metrics)
        if p.get("comments_count"):
            c = get(f"{p['id']}/comments", tok,
                    {"fields": "id,text,username,timestamp,like_count", "limit": 25})
            p["comments"] = [] if err(c) else c.get("data", [])
    return posts, None


def fetch_stories(tok, ig):
    """Stories vanish after 24h and take their insights with them. Anything not
    captured inside the window is gone for good -- hence --snapshot."""
    r = get(f"{ig}/stories", tok, {"fields": "id,media_type,media_product_type,timestamp,permalink"})
    if err(r):
        return [], err(r)
    stories = r.get("data", [])
    for s in stories:
        s["insights"] = _media_insights(tok, s["id"], STORY_METRICS)
    return stories, None


def fetch_quota(page_tok, ig):
    """Needs the page token -- the ads system-user token lacks instagram_content_publish."""
    if not page_tok:
        return {"error": "no page token"}
    r = get(f"{ig}/content_publishing_limit", page_tok, {"fields": "config,quota_usage"})
    if err(r) or not r.get("data"):
        return {"error": err(r) or "empty"}
    return r["data"][0]


def fetch_competitor(tok, ig, username):
    """business_discovery reads any PUBLIC business/creator account -- and hands over
    view_count, which Meta blocks on our own media. Prospect and competitor research."""
    fields = (
        f"business_discovery.username({username})"
        "{followers_count,follows_count,media_count,name,username,biography,website,"
        "media.limit(12){id,caption,like_count,comments_count,timestamp,media_type,"
        "media_product_type,permalink,view_count}}"
    )
    r = get(ig, tok, {"fields": fields})
    if err(r):
        return {"error": err(r)}
    return r.get("business_discovery", {"error": "no data"})


# ---------------------------------------------------------------- printing

def num(v):
    return f"{v:,}" if isinstance(v, (int, float)) else "-"


def one_line(caption, width=52):
    if not caption:
        return "(no caption)"
    flat = " ".join(caption.split())
    return flat[: width - 1] + "…" if len(flat) > width else flat


def print_report(data, args):
    p = data["profile"]
    totals, bd = data["totals"], data["breakdowns"]
    w = 76
    print("=" * w)
    print(f"@{p.get('username')} — organic, last {args.days} days")
    print(f"generated {data['generated_utc'][:16]} UTC  ·  graph {VERSION}")
    print("=" * w)
    print(f"{p.get('name', '')}")
    print(f"followers {num(p.get('followers_count'))}   following {num(p.get('follows_count'))}"
          f"   posts {num(p.get('media_count'))}   {p.get('website', '')}")

    # The headline split. Everything else is noise until this is read.
    reach_split = bd.get("reach/media_product_type", {})
    if isinstance(reach_split, dict) and "error" not in reach_split:
        ad = reach_split.get("AD", 0) or 0
        organic = sum(v or 0 for k, v in reach_split.items() if k != "AD")
        print("\n--- PAID vs ORGANIC (reach) ---")
        print(f"  ad reach       {num(ad):>9}")
        print(f"  organic reach  {num(organic):>9}   " +
              "  ".join(f"{k.lower()}={num(v)}" for k, v in reach_split.items() if k != "AD"))

    print("\n--- account totals ---")
    for metric in TOTAL_METRICS:
        row = totals.get(metric, {})
        if "value" in row:
            print(f"  {metric:22} {num(row['value'])}")
        elif "breakdown" in row:
            print(f"  {metric:22} " + "  ".join(f"{k}={num(v)}" for k, v in row["breakdown"].items()))
        else:
            print(f"  {metric:22} —  ({row.get('error', 'n/a')[:44]})")

    print("\n--- breakdowns ---")
    for key, rows in bd.items():
        if "error" in rows:
            print(f"  {key:38} —  ({rows['error'][:30]})")
        else:
            print(f"  {key:38} " + "  ".join(f"{k}={num(v)}" for k, v in rows.items()))

    daily = data["daily"].get("reach") or []
    if daily:
        print("\n--- daily reach ---")
        peak = max((d.get("value") or 0) for d in daily) or 1
        for d in daily:
            v = d.get("value") or 0
            bar = "█" * max(1, round(v / peak * 34)) if v else ""
            print(f"  {d.get('end_time', '')[:10]}  {num(v):>7}  {bar}")

    posts = data["posts"]
    print(f"\n--- posts ({len(posts)}) ---")
    if data.get("posts_error"):
        print(f"  could not read media: {data['posts_error']}")
    for post in posts:
        i = post.get("insights", {})
        reach, inter = i.get("reach"), i.get("total_interactions")
        rate = f"{inter / reach * 100:.1f}%" if isinstance(inter, (int, float)) and reach else "-"
        print(f"  {post.get('timestamp', '')[:10]}  "
              f"{post.get('media_product_type') or post.get('media_type', '?'):<8} "
              f"{one_line(post.get('caption'))}")
        print(f"      views {num(i.get('views')):>6}  reach {num(reach):>6}  "
              f"interactions {num(inter):>5}  eng/reach {rate:>6}")
        print(f"      likes {num(i.get('likes')):>6}  saved {num(i.get('saved')):>6}  "
              f"shares {num(i.get('shares')):>11}  "
              f"profile visits {num(i.get('profile_visits')):>3}  follows {num(i.get('follows')):>3}")
        for c in post.get("comments", [])[:5]:
            print(f"      💬 @{c.get('username')}: {one_line(c.get('text'), 46)}")
        print(f"      {post.get('permalink', '')}")

    stories = data["stories"]
    print(f"\n--- live stories ({len(stories)}) ---")
    if not stories:
        print("  none live right now. Stories and their insights die after 24h —")
        print("  run with --snapshot inside the window or the numbers are gone.")
    for s in stories:
        i = s.get("insights", {})
        print(f"  {s.get('timestamp', '')[:16]}  views {num(i.get('views'))}  "
              f"reach {num(i.get('reach'))}  replies {num(i.get('replies'))}  "
              f"profile visits {num(i.get('profile_visits'))}  follows {num(i.get('follows'))}")

    q = data["quota"]
    if "error" not in q:
        cfg = q.get("config", {})
        print(f"\n--- publishing quota ---\n  {q.get('quota_usage')} / "
              f"{cfg.get('quota_total')} posts used in the last "
              f"{(cfg.get('quota_duration') or 0) // 3600}h")

    demo = data.get("demographics")
    if demo:
        print("\n--- audience demographics ---")
        for metric, breakdowns in demo.items():
            for b, rows in breakdowns.items():
                if "error" in rows:
                    print(f"  {metric[:24]:26} {b:8} —  ({rows['error'][:38]})")
                else:
                    top = list(rows.items())[:6]
                    print(f"  {metric[:24]:26} {b:8} " +
                          "  ".join(f"{k}={num(v)}" for k, v in top))

    for username, c in (data.get("competitors") or {}).items():
        print(f"\n--- @{username} (business_discovery) ---")
        if "error" in c:
            print(f"  {c['error'][:70]}")
            continue
        print(f"  {c.get('name')}  ·  followers {num(c.get('followers_count'))}  "
              f"posts {num(c.get('media_count'))}  {c.get('website') or ''}")
        med = c.get("media", {}).get("data", [])
        for m in med[:10]:
            print(f"    {m.get('timestamp', '')[:10]}  {m.get('media_product_type', ''):<8} "
                  f"likes {num(m.get('like_count')):>7}  comments {num(m.get('comments_count')):>5}"
                  f"  views {num(m.get('view_count')):>9}")

    print("\n" + "=" * w)
    print("Organic only. Paid: /check-ads   Site: /check-ga4")
    print("Neither is truth for заявки — the Telegram bot and the Sheet are.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--posts", type=int, default=12)
    ap.add_argument("--competitor", action="append", default=[])
    ap.add_argument("--no-demographics", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--snapshot", action="store_true")
    args = ap.parse_args()

    if args.days > 30:
        print("note: Meta caps account insights at 30 days per query — clamping.")
        args.days = 30

    tok, page_tok, ig = load_env()
    now = datetime.now(timezone.utc)
    until, since = int(now.timestamp()), int((now - timedelta(days=args.days)).timestamp())

    profile = fetch_profile(tok, ig)
    if err(profile):
        sys.exit(f"Cannot read the account: {err(profile)}")

    posts, posts_error = fetch_posts(tok, ig, args.posts)
    stories, _ = fetch_stories(tok, ig)
    data = {
        "generated_utc": now.isoformat(),
        "window_days": args.days,
        "profile": profile,
        "totals": fetch_totals(tok, ig, since, until),
        "breakdowns": fetch_breakdowns(tok, ig, since, until),
        "daily": fetch_daily(tok, ig, since, until),
        "posts": posts,
        "posts_error": posts_error,
        "stories": stories,
        "quota": fetch_quota(page_tok, ig),
        "demographics": None if args.no_demographics else fetch_demographics(tok, ig),
        "competitors": {u: fetch_competitor(tok, ig, u) for u in args.competitor},
    }

    if args.snapshot:
        HISTORY.mkdir(exist_ok=True)
        out = HISTORY / f"{now:%Y-%m-%d-%H%M}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"snapshot written: {out}")

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_report(data, args)


if __name__ == "__main__":
    main()
