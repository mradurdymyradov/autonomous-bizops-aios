# Build Context: The End User's Internet & Device

**Read this before writing a single line of the landing page.** This page is not built for a developer on fiber. It is built for the harshest realistic mobile-web environment. Every design and engineering decision below flows from this reality. If a choice trades polish for load speed or resilience, choose load speed and resilience.

---

## Who opens this page

A small-business owner in **Turkmenistan**. They see an ad on Instagram, tap it, and the page opens **inside Instagram's in-app browser** (an Android WebView) — not Chrome, not Safari. They are on a phone, on mobile data, almost always through a VPN. You get one shot before they bounce back to their feed. The click was paid for, so a slow load is money already spent and lost.

## The connection reality (assume the worst, because it's common)

- **Country: Turkmenistan** — one of the slowest, most censored, most restricted internet environments on earth. State-monopoly ISP. Expensive, metered, unreliable data.
- **VPN is mandatory.** Instagram and most of the global web are blocked in-country. So **100% of your traffic arrives through a VPN** — usually a *free* one — just to have seen the ad at all.
- **Free VPN = worst-case network:** distant exit node (Europe/US/Asia), so **high round-trip latency (assume 250–450 ms RTT)**, **throttled bandwidth**, packet loss, and **connections that drop mid-load**.
- **Effective throughput: ~1–2 Mb/s** (≈125–250 KB/s), often lower. Treat 2 Mb/s as the *good* case, not the average.
- **Consequence of high RTT + slow start:** because of TCP slow-start, small transfers never reach full speed. Even 80 KB of fonts can take 2–3 round trips (~0.6–1s) *regardless* of nominal bandwidth. **Latency and number-of-round-trips hurt more than raw bytes.** Fewer requests and fewer origins beat clever compression.

## The device reality

- **Non-flagship Android.** Common phones: Tecno, Infinix, low-end Xiaomi Redmi, older Samsung A-series. **Weak CPU, limited RAM, older Android/WebView versions, small cheap screens.**
- Heavy JavaScript, large frameworks, and main-thread-blocking work are *expensive* here — a script that parses in 20 ms on your laptop can take 150–300 ms on this CPU.
- Design mobile-first for a **~360 px wide** viewport. Assume touch, assume thumb reach, assume glare on a cheap screen (need strong contrast).

## The entry point: Instagram in-app browser (WebView)

- **Cold every time.** The in-app browser does not share the system browser's cache. Assume **nothing is cached** — every visitor is a first visit, downloading everything.
- It's a stripped WebView: fewer features, occasional quirks with fonts, autoplay, and complex JS. Test mentally against a plain WebView, not desktop Chrome.
- Users can't easily reload or open dev tools. If it hangs, they leave.

## The censorship constraint — THIS IS A HARD RULE

Many global CDNs and third-party hosts are **blocked or throttled in Turkmenistan**. A page that pulls assets from an external origin can **hang or break entirely** for these users.

**Therefore: self-host everything. Zero third-party origins for anything on the critical path.**

- ❌ No Google Fonts CDN, no external font hosts → self-host fonts (subset + `woff2`).
- ❌ No external CSS/JS CDNs (jsDelivr, unpkg, cdnjs, etc.) → bundle and self-host.
- ❌ No YouTube/Vimeo embeds, no Google Maps embeds.
- ❌ No third-party form/booking widgets (Typeform, Calendly, etc.) — they may be blocked; build the form natively and self-host the submit.
- ⚠️ Even analytics (Google gtag / `googletagmanager.com`) may be throttled or blocked in-country and may silently not fire. If you include analytics, load it **truly async / non-blocking**, and never let its failure affect the page. Prefer an edge/first-party or single-beacon analytics option if one is available.

## What this means for the build (the rules that follow)

1. **One origin.** Ideally every byte comes from the page's own domain. Each extra origin = another DNS + TLS handshake through the VPN = ~0.6–1s of dead time.
2. **Ruthless byte budget.** Keep total first-visit transfer small (see targets below). Inline the critical CSS. Ship minimal JS — prefer no framework runtime; vanilla or a tiny bit of JS beats React/Vue payloads here.
3. **Above-the-fold renders with HTML + inline CSS alone.** The headline, the core value line, and the primary CTA must be visible and tappable **without waiting on JavaScript, web fonts, or images.** If JS never loads, the pitch and the button still work.
4. **Fonts: assume they might not arrive.** Self-host, subset to the languages actually used (Cyrillic + Latin), few weights, `font-display: swap` so text is readable instantly in a fallback. Seriously consider a **system-font stack** to skip font downloads entirely — on the worst connections this is the single biggest win.
5. **Images:** modern format (WebP/AVIF), sized for a small screen (don't ship a 1600px hero to a 360px phone), **lazy-load everything below the fold**, and never let an image block first paint or the CTA.
6. **Defer/async all non-critical scripts.** Nothing render-blocking except a tiny critical CSS.
7. **Resilience to drops:** the page must be readable and the CTA usable even if late-loading resources fail. No core content should depend on a request that might time out.
8. **Robust lead capture:** the form submit must survive a flaky connection — clear success/failure feedback, forgiving of a slow or dropped request, self-hosted endpoint. This is the money moment; it cannot silently fail.
9. **Long-cache immutable assets** (`Cache-Control: immutable`) via a `_headers` file, so a returning visitor or a re-scroll doesn't re-fetch.

## Performance targets (for the worst-case user described above)

| Target | Aim for |
|---|---|
| Total first-visit transfer | **< 100 KB** (hard ceiling **150 KB** — raised from ~130 KB by user decision 2026-07-16 for the v3 rebuild; gate: `voronka/tools/budget.mjs`) |
| Number of requests | **< 15** |
| Number of origins | **1** (self only) |
| First Contentful Paint | **< 2.0s** on ~1.5 Mb/s + 300 ms RTT |
| Largest Contentful Paint | **< 2.5s** on the same |
| Blocking JS on main thread | **near zero** — text + CTA never wait on JS |

## Baseline to match or beat (don't regress below this)

**Current live baseline — v3 (2026-07-16):**

- **74.4 KB** total transfer, **7 requests**, served over Brotli (measured by `voronka/tools/budget.mjs`, brotli q5).
- Self-hosted fonts, subsetted — 4 `woff2` files: Unbounded 700 cyr/lat + Golos variable cyr/lat (~52.6 KB, the bulk of the weight), `font-display: swap`, 2 cyrillic files preloaded.
- All CSS inline in the HTML; JS deferred; page fully readable and forms usable with zero JS.

(Historical: v1 was ~93 KB / 10 requests.) If a change pushes past 150 KB, adds any third-party origin, or makes the CTA depend on JS/fonts, it is a **regression** for this audience — stop and reconsider.

## The one-line test persona

> Budget Android phone, Instagram in-app browser, **free VPN throttling to ~1.5 Mb/s with 300 ms latency and occasional drops, nothing cached.** If it's fast and readable for them, it's fast for everyone.
