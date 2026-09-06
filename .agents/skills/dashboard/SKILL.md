---
name: dashboard
description: >-
  Use when Operator wants the business dashboard — "open the dashboard", "build the dashboard", "show me everything", "refresh the dashboard", "покажи дашборд", "обнови дашборд" — or after STATE.md, TODO.md or a client folder changes and the pipeline on the page needs to catch up. Rebuilds the operations console: today's queue, the 7 pilots, leads, funnel, marketing and system health, as one self-contained HTML file.
---

# /dashboard

`automations/dashboard/index.html` — the console Operator opens with his coffee. Self-contained, opens from
`file://` by double-clicking, no network at render time.

**It is an operations console, not a report.** Rebuilt from scratch on 2026-08-05 because the previous
version read as «a pdf report of our current state, something like slides of our pitchdeck… I opened
that when you just built, and never want to look at that again». What made it a report was structural,
not cosmetic: one long scroll, a Didone masthead, a fixed prose column, no persistent chrome, nothing
to click. Keep the structure that replaced it (below) and the page stays a console.

**Design law is the header comment in `template/app.css`, NOT
[brand/content-rules.md](../../../brand/content-rules.md) §2** — Operator released this surface from the
brand palette on 2026-08-03 («if you need, change colors, dont lock in brand colors») and asked for
dark on 2026-08-05. Read that comment before changing any colour; it carries the seven rules and the
measured contrast of every token.

## What this command does

1. **Re-sync the projection** — rewrite `automations/dashboard/business.json` from the markdown.
2. **Rebuild** — `python automations/dashboard/build.py --live` (drop `--live` if the VPN is down).
3. **Print the path.** Operator opens it.

## Step 1 — rewriting business.json

`business.json` is a **derived projection**, exactly as `snapshots/` is a derived projection of the
APIs. It exists because the most important parts of this business — revenue, the pilots, the open
loops — live in prose that no API can answer. **Never hand-edit it and never ask Operator to.** The law
"no system that needs daily manual upkeep" is satisfied only because an agent writes this file from
sources that already exist.

Read these, in this order, and rewrite the file:

| Source | Fills |
|---|---|
| [STATE.md](../../../STATE.md) | `pipeline` (the client board), `open_loops`, `ads`, `content`, `money.revenue_usd` |
| [TODO.md](../../../TODO.md) | `todo` |
| `clients projects/<slug>/engagement.md` + `spec.md` | per-client `blocker`, `next_action`, `last_touch`, `build_repo`, `deploy_url`, `deployed_on`, `noindex`, `highlight` |
| [funnel/00-core.md](../../../funnel/00-core.md) §Terms | `offer` — price, deposit, free-campaign count and validity |
| [brain/calls/callback-debt.md](../../../brain/calls/callback-debt.md) | context for the deferral-pile insight |

Then **recompute `source_files`** — the first 12 hex chars of each source's SHA-1:

```bash
for f in STATE.md TODO.md "clients projects/README.md" brain/calls/callback-debt.md funnel/00-core.md; do sha1sum "$f" | cut -c1-12; done
```

`build.py` re-hashes those files at build time. Any mismatch surfaces as a **projection drift** count
in the rail's freshness block, an insight card, and a red stat on System → Health. **That is the whole
anti-rot mechanism — if you skip the hashes, the page lies quietly instead of loudly.**

Stages are fixed by [`clients projects/README.md`](../../../clients%20projects/README.md) §2:
`agreed → spec → questions → build → meeting → live → decision`. Use those exact strings; `build.py`
turns them into the seven-dot rail and will put a pilot at stage 0 if the string doesn't match.

## Step 2 — build

```bash
python automations/dashboard/build.py --live
```

- `--live` refreshes the snapshot rows and the CRM first. Needs the VPN.
- Without it the build is fully offline: stored rows + the cached CRM payload, and the page says on
  its own face how old each one is.
- `--open` opens it afterwards. `--days N` narrows the window; default is every stored row.
- On Windows, prefix with `PYTHONIOENCODING=utf-8` or the Cyrillic in the progress output raises
  `UnicodeEncodeError` under cp1251.

## The structure

Six sections, hash-routed as `#/<section>/<tab>`, with `?rec=<id>` opening the side drawer. Hash
routing is not a style choice: `pushState` throws on a `file://` opaque origin and a refresh gives
`ERR_FILE_NOT_FOUND`, and the same bytes then run unchanged from Cloudflare Pages with no `_redirects`.

| Route | Tabs | What it answers |
|---|---|---|
| `#/today` | — | What needs me this morning |
| `#/pipeline` | Board · Table | Where the seven pilots stand |
| `#/leads` | All · Callbacks · Uncalled · Interested · Speed | Every заявка, filterable, drillable |
| `#/funnel` | Chain · Creatives · Segments | Impressions → заявка, and which creative actually converts |
| `#/marketing` | Ads · Traffic · Instagram · Content | Spend, site, profile, batches |
| `#/system` | Health · Sources · Open loops · Tasks | Where every number came from and how old it is |

Today is the only screen with a fixed composition, because it is the one he opens every morning:
hero row (Needs you / In flight / Days dark) → up to three insight cards → the focus-ordered queue →
right column of pipeline, 30-day activity, lifetime counts.

**The queue is the point of the page.** `build_queue()` in `build.py` ranks every actionable thing
into fixed groups — `broken` (a deployed client page whose form goes nowhere) → `uncalled` →
`callback` → `blocked` → `pilot` → `loop` → `task` — and a group renders **nothing at all** when it
is empty. An empty queue draws the done-state, not a grid of zeros.

`build_insights()` is rule-generated only. Every card carries `{sev, headline, evidence, recommend,
href}` and comes from a named rule (ads paused N days, leads never dialled, deferral pile, speed to
lead, CF function errors, snapshot staleness, projection drift, GA4 key events off). **Never write a
prose insight by hand into the payload** — the page must be re-derivable from the data alone.

## Where the numbers come from

Three tiers, and the page states which is which on its own face:

| Tier | Source | Freshness |
|---|---|---|
| Stored rows | `snapshots/daily/*.json` via `funnel.py` | always available, offline, frozen after D+3 |
| CRM | `sheets/crm.py --json --all`, cached with `fetched_at` | live only behind `--live` |
| Projection | `business.json` | SHA-1 of every source; a mismatch banners the page |

## Rules that are easy to break

- **A failed reader is `null`, never `0`.** `derive_rows()` honours this and `dayBars()` draws three
  distinct states: a bar, a hairline stub for a measured zero, and *nothing* for a missing reading.
  Don't collapse the last two.
- **Rows stay mutable for 3 days.** Don't call a trend off them.
- **Only the Sheet CRM is truth for заявки.** Meta and GA4 are estimates and the page says so.
- **Percentages below `CONFIDENCE_N` (30) get a count pair, not a rate.**
- **The funnel scale break is drawn and named.** Four orders of magnitude sit between impressions
  and заявки; linear pins four of five bars to the floor, and log or sqrt would flatter the data. The
  page rescales after stage 1 and prints the zoom factor. Don't "fix" it with a log axis.
- **`build.py` computes, `app.js` draws.** Every rank, rate and rollup arrives pre-derived. The moment
  a derivation lives in both, the two drift.
- **One fact, one home.** Before adding a panel, check the fact isn't already on another route.
- **Every bar is one ink.** No ramps. Length carries magnitude, the label carries identity.
- **Body text is 15px; 11px is the floor and only uppercase micro-labels and badges go there.**
- **Every ink clears 4.5:1 on every surface it can land on** — verified by the snippet below, not by
  eye. The dimmest tier started at 3.0:1 as a "watermark" and immediately drew table headers.
- **No network at render time.** No CDN, no chart library, no web font over the wire. Fonts are
  base64'd from `template/fonts/` — Golos Text only; Prata was dropped with the report layout.
  Numbers are set in the system UI face because Golos ships **no** `tnum` and proportional digits
  make a column of figures wobble; mono (Consolas) is the data register — phones, handles, timestamps.
- **The output is gitignored.** `index.html` and `cache/` are generated; `business.json` is committed.

## Verifying a restyle

The Browser pane often can't composite a screenshot in this environment, so the design checks are
computed. Open the built file and run this in the console — it catches everything that has actually
gone wrong here: a network request smuggled in, the page scrolling sideways, text below the floor,
and any ink that fails AA against its **composited** background (alpha tints included, which a naive
check misses).

```javascript
(()=>{const P=c=>{const m=c.match(/[\d.]+/g).map(Number);return{r:m[0],g:m[1],b:m[2],a:m.length>3?m[3]:1}},L=v=>(v/=255,v<=.03928?v/12.92:((v+.055)/1.055)**2.4),Y=o=>.2126*L(o.r)+.7152*L(o.g)+.0722*L(o.b),O=(f,b)=>({r:f.a*f.r+(1-f.a)*b.r,g:f.a*f.g+(1-f.a)*b.g,b:f.a*f.b+(1-f.a)*b.b,a:1}),B=n=>{let a={r:11,g:12,b:15,a:1},s=[],p=n;for(;p&&p!==document.documentElement;p=p.parentElement){const c=P(getComputedStyle(p).backgroundColor);c.a>0&&s.push(c)}for(let i=s.length-1;i>=0;i--)a=O(s[i],a);return a},R=(x,y)=>{const a=Y(x),b=Y(y);return(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};let min=99,fails=[];document.querySelectorAll('#view *,#rail *,#topbar *,#drawer *,#cmdk *').forEach(n=>{if(!n.firstChild||n.firstChild.nodeType!==3||!n.textContent.trim())return;const s=getComputedStyle(n),f=parseFloat(s.fontSize);min=Math.min(min,f);const need=(f>=24||(f>=18.66&&+s.fontWeight>=700))?3:4.5,r=R(P(s.color),B(n));r<need&&fails.push([n.className||n.tagName,+r.toFixed(2),f,n.textContent.trim().slice(0,16)])});return{resources:performance.getEntriesByType('resource').length,sideways:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,minFontSize:min,contrastFails:fails}})()
```

Expected: `resources: 0` · `sideways: false` · `minFontSize ≥ 11` · `contrastFails: []`. **Run it on
every route** (`location.hash = '/leads/all'` etc., wait ~60ms for the view transition) and again at
390px wide. Tables scroll inside their own `.tw` container; the page body never scrolls sideways.

Two traps when driving it from a hidden pane: CSS animations and transitions are **paused** when the
pane isn't compositing, so the drawer and the off-canvas rail measure as still off-screen — inject
`*{animation:none!important;transition:none!important}` before measuring. And `location.reload()`
serves the pane's snapshot, so re-`navigate` with `force: true` after a rebuild and close the stale
tab, or you will audit the previous build.

## When it looks wrong

Compare against the sources before touching the renderer:

```bash
python automations/funnel.py --from <start> --to <end>
python automations/sheets/crm.py --all
```

If those disagree with the page, the bug is in `build.py`. If they agree with each other and both
look wrong, the bug is upstream in `snapshot.py` or the reader.
