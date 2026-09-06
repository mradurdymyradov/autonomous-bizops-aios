# ig-insights — Instagram organic performance

**What's blocked across every system, and what unlocks it: [../CAPABILITIES.md](../CAPABILITIES.md).**

Reads everything the Instagram Graph API will give us about @voronka.tm. Read-only: it posts nothing
and changes nothing.

**Current numbers are not in this file** — run the script. This file is the technical reference: what
exists, what's blocked, and every dead end already walked so nobody walks it twice.

The third leg of the measurement stack:

| Question | Tool |
|---|---|
| Did the paid ads spend and deliver? | `/check-ads` → `../meta-ads/report.py` |
| What happened on voronkatm.com? | `/check-ga4` → `../ga4/report.py` |
| **Is the profile itself working organically?** | **`/check-ig` → this** |
| How many real заявки? | Telegram bot + Sheet CRM. **Only these are truth.** |

## Files

- `report.py` — the whole tool. Called by the `check-ig` skill.
- `history/` — `--snapshot` output. **Committed on purpose.** Meta deletes insight history after 30
  days and story insights after 24h; these files are the only copy that outlives it.
- No `.env` of its own **by design.** Insights use the system-user token in `../meta-ads/.env`; the
  publishing quota needs the page token in `../ig-poster/.env`. One less copy of a token that can
  spend from the card on file.

## Usage

```bash
cd automations/ig-insights
python report.py                          # 28 days, 12 posts, everything
python report.py --days 30                # Meta's hard cap per query
python report.py --snapshot               # write history/<timestamp>.json — do this before stories die
python report.py --competitor someshop.tm # competitor / prospect research
python report.py --json                   # machine-readable
python report.py --no-demographics        # skip 12 calls that are empty until ~100 followers
```

On Windows the console is cp1251 and Cyrillic captions crash the print. Prefix with
`PYTHONIOENCODING=utf-8` if you see a `UnicodeEncodeError`.

## The full catalogue — what this account can and cannot get

Probed exhaustively 2026-07-26. Every field, metric, breakdown and edge below was actually called.

### Works

| Level | Available |
|---|---|
| Profile | `username, name, biography, website, followers_count, follows_count, media_count, ig_id, legacy_instagram_user_id, profile_picture_url, has_profile_pic, is_published` |
| Account totals | `views, reach, profile_views, accounts_engaged, total_interactions, likes, comments, saves, shares, replies, profile_links_taps, website_clicks` |
| Daily series | `reach`, `follower_count` |
| **Breakdowns** | `views`+`reach`+`total_interactions` × `media_product_type`; `views`+`reach` × `follow_type`; `profile_links_taps` × `contact_button_type` |
| Per post | `views, reach, total_interactions, likes, comments, saved, shares, profile_visits, follows, profile_activity` |
| Per post fields | `caption, media_type, media_product_type, permalink, shortcode, timestamp, like_count, comments_count, is_comment_enabled, media_url, children, boost_eligibility_info` |
| Comments | full text, author, timestamp, like_count |
| Stories | `views, reach, replies, shares, profile_visits, follows, total_interactions, navigation` — **only while live** |
| Reels | `ig_reels_avg_watch_time, ig_reels_video_view_total_time` (none posted yet) |
| Publishing quota | `content_publishing_limit` — 100 posts/24h, needs the **page** token |
| **Competitors** | `business_discovery` on any public business/creator account |

### The breakdown that matters most

`media_product_type` **separates AD from POST / STORY / CAROUSEL_CONTAINER.** This is the difference
between "we reached 5,939 accounts" and the truth, which is that ~5,939 of that was the $5.87 ad and
organic reach was ~156. Never report an account-level total without running this split first.

`follow_type` splits FOLLOWER vs NON_FOLLOWER reach — how much of the audience is the 29 followers
versus everyone else.

### Blocked, and why

| Thing | Status |
|---|---|
| **Hashtag search** (`ig_hashtag_search`, top/recent media) | **Blocked.** Needs "Instagram Public Content Access" App Review. Same root cause as the ad-creative block: the app is unpublished. |
| DM / `conversations` | Blocked — needs `instagram_manage_messages` granted to the app, not just the token. |
| `view_count` on **our own** media | Blocked outside Business Discovery — but readable on *other* accounts via `business_discovery`. |
| Shopping (`available_catalogs`, `product_tags`, `product_appeal`) | No permission. Not applicable to this business. |
| `dataset` / events | Needs `instagram_manage_events`. |
| Facebook Page insights | Return empty — the Page has 0 fans and is a technical requirement, not a channel. Needs the page token, not the ads token. |
| `impressions` | **Removed by Meta in v22.0.** Use `views`. |

### Withheld by volume, not broken

- **All three demographic sets** (`follower_demographics`, `engaged_audience_demographics`,
  `reached_audience_demographics`) across country/city/age/gender return empty. Meta gates these behind
  roughly **100 followers**; the account has 29.
- **`follows_and_unfollows`** and daily `follower_count` — same reason.

These start working on their own. There is nothing to fix and nothing to debug.

## Traps already hit, so nobody hits them twice

- **`saved` per media vs `saves` at account level.** Meta does not alias them, and the wrong name 400s
  the *entire* metric batch, not just that field. This is why both account totals and media insights
  fetch **one metric per call** — a dead metric then costs one line of the report instead of the report.
- **`views`, `profile_views`, `website_clicks` and friends are rejected without `metric_type=total_value`.**
- **The pinned `GRAPH_VERSION` is inert — and this is not a problem to fix.** Meta ignores the version
  in the URL entirely. Asking for `v18.0`, `v21.0`, `v23.0` or `v25.0` all return
  `facebook-api-version: v25.0` in the response header, and identical values in the body (verified
  2026-07-26 across account and media insights, and against the ad account and campaigns endpoints).
  So `meta-ads/.env` saying `v21.0` costs nothing and breaks nothing — the ads tooling is genuinely
  fine. It only explains a confusing error message: `impressions` fails with "no longer supported from
  v22.0" on what looks like a v21.0 request, because the request was never v21.0. `report.py` here
  names `v25.0` so the code matches what it's actually tested against. Nothing needs changing.
- **30-day cap** on account insights per query. `--days` clamps instead of failing.
- **Story insights die with the story at 24h.** There is no historical stories endpoint. If it wasn't
  snapshotted inside the window it does not exist. This is the single biggest data-loss hole.
- Every call retries with backoff — the VPN drops mid-request regularly. A blank result is more often
  the connection than the API.

## Reading the numbers honestly

Per-post numbers are the clean organic signal — the ad creatives were never published as feed posts,
so they don't contaminate the post lines. Account-level lines do include ad traffic until you split
them by `media_product_type`.

With 29 followers, single-digit moves are noise. One person saving a post swings eng/reach by points.
