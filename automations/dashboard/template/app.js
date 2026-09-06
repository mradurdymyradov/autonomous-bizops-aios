/* =============================================================================
   VAIOS console — one classic <script>, no modules, no dependencies.

   WHY IT LOOKS LIKE THIS
   ----------------------
   file:// gives the document an opaque origin. That blocks fetch(), XHR, module
   <script src>, workers, and (in Firefox/Safari) localStorage. So: one IIFE, all
   data inlined by build.py, storage behind a shim that degrades to memory, and
   HASH routing — never pushState, which throws on an opaque origin and 404s on
   refresh. The same bytes then run unchanged from Cloudflare Pages with no
   _redirects file.

   BUILD.PY COMPUTES, THIS FILE DRAWS. Every rank, rate and rollup arrives
   pre-derived. If a number looks wrong, fix it in Python — the moment a
   derivation lives here too, the two drift.
   ========================================================================== */
(function () {
"use strict";

var D = DATA, S = D.stored, C = D.crm, B = D.business || {};
var LEADS = (C && C.leads) || [];
var PIPE = B.pipeline || [];

/* ------------------------------------------------------------------ utils */
function esc(s){ return s == null ? "" : String(s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }

var nf = new Intl.NumberFormat("en-US");
function n(v){ return v == null ? "—" : nf.format(v); }
function money(v,d){ return v == null ? "—" : "$" + v.toFixed(d == null ? 2 : d); }
function pct(v,d){ return v == null ? "—" : v.toFixed(d == null ? 1 : d) + "%"; }
function dur(sec){
  if (!sec) return "0m";
  var m = Math.floor(sec/60), s = sec%60;
  return m >= 60 ? Math.floor(m/60)+"h "+(m%60)+"m" : m ? m+"m "+(s?s+"s":"") : s+"s";
}
function mins(m){
  if (m == null) return "—";
  if (m < 60) return Math.round(m)+"m";
  if (m < 1440) return (m/60).toFixed(1)+"h";
  return (m/1440).toFixed(1)+"d";
}
function ago(d){ return d == null ? "—" : d === 0 ? "today" : d === 1 ? "1d" : d+"d"; }
function dshort(iso){ return iso ? iso.slice(8,10)+"."+iso.slice(5,7) : "—"; }
function dtime(ts){ return ts ? ts.slice(8,10)+"."+ts.slice(5,7)+" "+ts.slice(11,16) : "—"; }
function phoneHref(dig){ return dig ? "tel:+" + dig : null; }
function el(id){ return document.getElementById(id); }
function on(node, ev, fn){ node && node.addEventListener(ev, fn); }
function daysBetween(a,b){ return Math.round((new Date(b) - new Date(a)) / 864e5); }

/* Chrome allows localStorage on file:// (one shared bucket for every file: doc,
   hence the namespace); Firefox and Safari throw. Degrade to memory silently. */
var store = (function(){
  try { localStorage.setItem("_t","1"); localStorage.removeItem("_t"); return localStorage; }
  catch(e){ var m = {}; return { getItem:function(k){return m[k]==null?null:m[k];},
    setItem:function(k,v){m[k]=String(v);}, removeItem:function(k){delete m[k];} }; }
})();
function sget(k){ return store.getItem("vaios.dash."+k); }
function sset(k,v){ store.setItem("vaios.dash."+k, v); }

/* --------------------------------------------------------------- charts */
/* All SVG, authored in real pixel space so 1px rules stay crisp. The +0.5
   offset is the whole reason hand-rolled charts usually look soft: whole-number
   SVG coordinates fall BETWEEN device pixels, so a 1px line renders as two
   half-opacity rows. */
function px(v){ return Math.round(v) + 0.5; }

/* Bars over a daily series. Three distinct states, never collapsed:
   value > 0 -> a bar · value === 0 -> a ghost stub (measured zero) ·
   null/missing -> nothing at all (the reader failed; drawing 0 would lie). */
function dayBars(series, key, opts){
  opts = opts || {};
  var W = 100, H = opts.h || 64, pad = 3, n = series.length;
  var vals = series.map(function(s){ return s.missing ? null : s[key]; });
  var max = 0; vals.forEach(function(v){ if (v != null && v > max) max = v; });
  if (!max) max = 1;
  var bw = (W - pad*2) / n, gap = Math.min(1.1, bw*0.22), out = "";
  for (var i = 0; i < n; i++){
    var v = vals[i], x = pad + i*bw + gap/2, w = Math.max(bw - gap, 0.6);
    if (v == null){ continue; }
    if (v === 0){ out += '<rect class="bar ghost" x="'+x.toFixed(2)+'" y="'+(H-2)+'" width="'+w.toFixed(2)+'" height="2" rx="0.6"/>'; continue; }
    var h = Math.max(2, (v/max) * (H-10));
    out += '<rect class="bar '+(opts.cls||"")+'" x="'+x.toFixed(2)+'" y="'+(H-h).toFixed(2)+'" width="'+w.toFixed(2)+'" height="'+h.toFixed(2)+'" rx="'+Math.min(1.2,w/2).toFixed(2)+'"/>';
  }
  var hits = "";
  for (var j = 0; j < n; j++){
    hits += '<rect class="hit" data-i="'+j+'" x="'+(pad+j*bw).toFixed(2)+'" y="0" width="'+bw.toFixed(2)+'" height="'+H+'"/>';
  }
  return '<svg class="chart" viewBox="0 0 100 '+H+'" preserveAspectRatio="none" height="'+H+'" data-chart="days" data-key="'+key+'">'
    + '<line class="zero-l" x1="0" y1="'+(H-0.5)+'" x2="100" y2="'+(H-0.5)+'" vector-effect="non-scaling-stroke"/>'
    + out + hits + '</svg>';
}

/* A dual histogram around a shared baseline: leads arriving (up) against calls
   going out (down), by hour of the Ashgabat day. The GAP between the two humps
   is the finding — a single median hides it entirely. */
function hourChart(byHour){
  var W = 720, H = 168, padL = 26, padR = 8, padT = 14, padB = 26;
  var mid = padT + (H - padT - padB) / 2;
  var maxA = 1, maxC = 1;
  byHour.forEach(function(h){ if (h.arrived > maxA) maxA = h.arrived; if (h.called > maxC) maxC = h.called; });
  var bw = (W - padL - padR) / 24, gap = 3, half = (H - padT - padB) / 2 - 6;
  var s = "";
  for (var i = 0; i < 24; i++){
    var h = byHour[i], x = padL + i*bw + gap/2, w = bw - gap;
    if (h.arrived){
      var ha = Math.max(2, h.arrived / maxA * half);
      s += '<rect class="bar live" x="'+x.toFixed(1)+'" y="'+(mid-ha).toFixed(1)+'" width="'+w.toFixed(1)+'" height="'+ha.toFixed(1)+'" rx="2"/>';
    }
    if (h.called){
      var hc = Math.max(2, h.called / maxC * half);
      s += '<rect class="bar" x="'+x.toFixed(1)+'" y="'+mid.toFixed(1)+'" width="'+w.toFixed(1)+'" height="'+hc.toFixed(1)+'" rx="2"/>';
    }
    if (i % 3 === 0) s += '<text x="'+(x + w/2).toFixed(1)+'" y="'+(H-8)+'" text-anchor="middle">'+i+'</text>';
  }
  s += '<line class="zero-l" x1="'+padL+'" y1="'+px(mid)+'" x2="'+(W-padR)+'" y2="'+px(mid)+'"/>';
  s += '<text x="2" y="'+(mid-half+4)+'">in</text><text x="2" y="'+(mid+half)+'">out</text>';
  return '<div class="cscroll"><svg class="chart" viewBox="0 0 '+W+' '+H+'" '
    + 'style="height:auto;aspect-ratio:'+W+'/'+H+'">'+s+'</svg></div>';
}

function barRows(obj, opts){
  opts = opts || {};
  var entries = Array.isArray(obj) ? obj : Object.keys(obj).map(function(k){ return [k, obj[k]]; });
  if (!entries.length) return '<p class="note dim">Nothing recorded.</p>';
  var max = 0, total = 0;
  entries.forEach(function(e){ if (e[1] > max) max = e[1]; total += e[1]; });
  return '<div class="rows">' + entries.map(function(e, i){
    var cls = opts.hiFirst && i === 0 ? " hi" : (opts.on && opts.on.indexOf(e[0]) >= 0 ? " on" : "");
    var share = total ? Math.round(100*e[1]/total) : 0;
    return '<div class="brow'+cls+'"><div class="k" title="'+esc(e[0])+'">'+esc(e[0])+'</div>'
      + '<div class="track"><div class="fill" style="width:'+(max ? (100*e[1]/max) : 0).toFixed(1)+'%"></div></div>'
      + '<div class="v">'+n(e[1])+(opts.share!==false?'<em>'+share+'%</em>':'')+'</div></div>';
  }).join("") + '</div>';
}

function activityStrip(cells){
  var today = D.today;
  return '<div class="act">' + cells.map(function(c){
    var t = c.date + " · " + c.leads + " lead" + (c.leads===1?"":"s") + ", " + c.calls + " call" + (c.calls===1?"":"s")
      + (c.spend ? ", $" + c.spend.toFixed(2) : "") + (c.captured ? "" : " · no snapshot");
    return '<div class="cell'+(c.date===today?" today":"")+'" data-l="'+c.level+'" title="'+esc(t)+'"></div>';
  }).join("") + '</div><div class="actlab"><span>'+dshort(cells[0].date)+'</span><span>leads · calls</span><span>today</span></div>';
}

function srail(i, small){
  var s = "";
  for (var k = 0; k < D.stages.length; k++)
    s += '<i class="'+(k < i ? "done" : k === i ? "at" : "")+'"></i>';
  return '<span class="srail'+(small?" sm":"")+'" title="'+esc(D.stages[i])+'">'+s+'</span>';
}

/* --------------------------------------------------------------- pieces */
function panel(title, sub, body, right, flush){
  return '<section class="panel"><div class="panel-h"><h2>'+esc(title)+'</h2>'
    + (sub ? '<span class="sub">'+esc(sub)+'</span>' : "")
    + (right ? '<div class="right">'+right+'</div>' : "")
    + '</div><div class="panel-b'+(flush?" flush":"")+'">'+body+'</div></section>';
}
function stat(label, value, sub, cls){
  return '<div class="stat '+(cls||"")+'"><span class="lab">'+esc(label)+'</span>'
    + '<span class="stat-v">'+value+'</span>'
    + (sub ? '<span class="sub" title="'+esc(sub)+'">'+esc(sub)+'</span>' : "") + '</div>';
}
function emptyState(t, d){
  return '<div class="empty-s"><span class="t">'+esc(t)+'</span><span class="d">'+esc(d)+'</span></div>';
}

/* ----------------------------------------------------------------- state */
var ROUTES = {
  today:     { title:"Today",     sub:"what needs you this morning", tabs:[] },
  pipeline:  { title:"Pipeline",  sub:"seven pilots, one at a time",
               tabs:[["board","Board"],["table","Table"]] },
  leads:     { title:"Leads",     sub:"the Sheet CRM is truth for заявки",
               tabs:[["all","All"],["callbacks","Callbacks"],["uncalled","Uncalled"],["won","Interested"],["speed","Speed"]] },
  funnel:    { title:"Funnel",    sub:"impressions → заявка, five sources reconciled",
               tabs:[["chain","Chain"],["creatives","Creatives"],["segments","Segments"]] },
  marketing: { title:"Marketing", sub:"ads, site, profile, content",
               tabs:[["ads","Ads"],["traffic","Traffic"],["instagram","Instagram"],["content","Content"]] },
  system:    { title:"System",    sub:"where every number came from, and how old it is",
               tabs:[["health","Health"],["sources","Sources"],["loops","Open loops"],["tasks","Tasks"]] }
};
var NAV = [
  ["today","Today",     '<svg viewBox="0 0 16 16" width="15" height="15"><path d="M2.5 8.5l5-5 6 6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 8v5.5h8V8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>'],
  ["pipeline","Pipeline",'<svg viewBox="0 0 16 16" width="15" height="15"><rect x="2" y="3" width="4" height="10" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="7.5" y="3" width="4" height="6.5" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M13 3v10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" opacity=".45"/></svg>'],
  ["leads","Leads",     '<svg viewBox="0 0 16 16" width="15" height="15"><circle cx="6" cy="5.5" r="2.6" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M1.8 13.5c0-2.4 1.9-3.9 4.2-3.9s4.2 1.5 4.2 3.9" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><path d="M11.5 5.5h3M13 4v3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>'],
  ["funnel","Funnel",   '<svg viewBox="0 0 16 16" width="15" height="15"><path d="M2 3h12l-4.4 5.2v4.3L6.4 14V8.2z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>'],
  ["marketing","Marketing",'<svg viewBox="0 0 16 16" width="15" height="15"><path d="M2.5 6.5h2.6L10 3.2v9.6L5.1 9.5H2.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M12.4 5.6a3.4 3.4 0 010 4.8" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>'],
  ["system","System",   '<svg viewBox="0 0 16 16" width="15" height="15"><rect x="2" y="2.5" width="12" height="4.5" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="2" y="9" width="12" height="4.5" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.3"/><circle cx="4.6" cy="4.75" r=".8" fill="currentColor"/><circle cx="4.6" cy="11.25" r=".8" fill="currentColor"/></svg>']
];

var route = { sec:"today", tab:"", q:new URLSearchParams() };

function parseHash(){
  var raw = location.hash.slice(1) || "/today";
  var qi = raw.indexOf("?");
  var path = (qi < 0 ? raw : raw.slice(0, qi)).replace(/^\/+/, "").split("/");
  var q = new URLSearchParams(qi < 0 ? "" : raw.slice(qi+1));
  var sec = ROUTES[path[0]] ? path[0] : "today";
  var tabs = ROUTES[sec].tabs, tab = path[1] || (tabs.length ? tabs[0][0] : "");
  if (tabs.length && !tabs.some(function(t){ return t[0] === tab; })) tab = tabs[0][0];
  return { sec:sec, tab:tab, q:q };
}
function href(sec, tab, params){
  var s = "#/" + sec + (tab ? "/" + tab : "");
  if (params){ var p = new URLSearchParams(params).toString(); if (p) s += "?" + p; }
  return s;
}
/* replaceState for filter tweaks so Back doesn't walk through every keystroke.
   Chromium reports a file: document's origin as "file://" and allows a
   hash-only replaceState; other engines treat it as opaque and throw. Falling
   back to location.hash costs a history entry, never a broken filter. */
function setQuery(mutate, push){
  var q = new URLSearchParams(route.q);
  mutate(q);
  var url = href(route.sec, route.tab, q);
  if (push){ location.hash = url.slice(1); return; }
  try { history.replaceState(null, "", url); }
  catch (e) { location.hash = url.slice(1); return; }
  route.q = q; render();
}

/* ------------------------------------------------------------------ nav */
function counts(){
  return {
    today: D.queue.filter(function(x){ return x.sev === "act"; }).length,
    pipeline: PIPE.filter(function(p){ return p.blocker; }).length,
    leads: C ? C.debt.length + C.calls.never_dialled : 0,
    funnel: 0, marketing: 0,
    system: (D.drifted||[]).length + (S.health.missing||[]).length + (S.alarms.function_errors||0)
  };
}
function drawNav(){
  var c = counts();
  el("nav").innerHTML = '<div class="nav-sec">Operate</div>'
    + NAV.slice(0,3).map(navItem).join("")
    + '<div class="nav-sec">Measure</div>'
    + NAV.slice(3).map(navItem).join("");
  function navItem(x){
    var k = x[0], hot = (k === "today" || k === "leads") && c[k] > 0;
    return '<a class="nav-a" href="'+href(k,"")+'" data-sec="'+k+'"'+(hot?' data-hot="1"':"")+'>'
      + x[2] + '<span class="lbl">'+esc(x[1])+'</span>'
      + (c[k] ? '<span class="cnt">'+c[k]+'</span>' : "") + '</a>';
  }
}
function drawFreshness(){
  var snapAge = daysBetween(S.window.end, D.today);
  var crmAge = D.crm_fetched_at ? Math.floor((Date.now() - new Date(D.crm_fetched_at)) / 36e5) : null;
  var dr = (D.drifted||[]).length;
  function row(cls, txt){ return '<div class="fr"><span class="dot '+cls+'"></span>'+esc(txt)+'</div>'; }
  el("freshness").innerHTML =
      row(snapAge > 1 ? "warn" : "", "snapshot " + (snapAge <= 0 ? "today" : snapAge + "d old"))
    + row(crmAge == null ? "bad" : crmAge > 48 ? "warn" : "", "CRM " + (crmAge == null ? "not cached" : crmAge < 1 ? "just now" : crmAge + "h old"))
    + row(dr ? "warn" : "", dr ? "projection behind ×" + dr : "projection in sync")
    + '<div class="fr dim">built ' + esc(D.built_at.slice(5,16).replace("T"," ")) + '</div>';
}

/* ------------------------------------------------------------------ hero */
function heroToday(){
  var act = D.queue.filter(function(x){ return x.sev === "act"; });
  var inFlight = PIPE.reduce(function(a,p){ return a + (p.deal_usd||0); }, 0);
  var revenue = (B.money && B.money.revenue_usd) || 0;
  var dark = S.last_lead_day ? daysBetween(S.last_lead_day, D.today) : null;

  var last = sget("lastVisit");
  var newLeads = last ? LEADS.filter(function(L){ return L.ts && L.ts > last; }).length : 0;

  function card(cls, lab, val, unit, sub, link, delta){
    return '<a class="hero-c '+cls+'" href="'+link+'"><span class="lab">'+esc(lab)+'</span>'
      + '<span class="hero-v">'+val+(unit?'<span class="unit">'+esc(unit)+'</span>':"")+'</span>'
      + (delta ? '<span class="hero-delta">'+esc(delta)+'</span>' : "")
      + '<span class="sub">'+esc(sub)+'</span></a>';
  }
  return '<div class="hero">'
    + card(act.length ? "is-live" : "", "Needs you", act.length, "",
        act.length ? "leads, callbacks and blocked pilots" : "queue is clear",
        "#/today", newLeads ? "+" + newLeads + " new since last visit" : "")
    + card("", "In flight", "$" + n(inFlight), "",
        revenue ? "$" + n(revenue) + " collected" : "nothing collected yet · " + PIPE.length + " pilots at $" + n(B.offer ? B.offer.deal_usd : 500),
        "#/pipeline")
    + card(dark != null && dark > 3 ? "is-dang" : "", "Days dark", dark == null ? "—" : dark, "d",
        S.last_lead_day ? "since the last заявка (" + dshort(S.last_lead_day) + ") · ads off since " + dshort(S.last_spend_day)
                        : "no заявка in the stored window",
        "#/marketing/ads")
    + '</div>';
}

/* ----------------------------------------------------------------- views */
var GROUPS = {
  broken:  ["Money on the floor", "A deployed page whose form goes nowhere loses a real заявка silently."],
  uncalled:["Never dialled",      "Already paid for at the current cost per заявка."],
  callback:["Owed a second touch","Half of every recorded note is a deferral. Oldest first."],
  blocked: ["Blocked pilots",     "One question or one file each."],
  pilot:   ["Pilots moving",      "Builds run one at a time, in rank order."],
  loop:    ["Open loops",         "From STATE.md, high severity only."],
  task:    ["Tasks",              "From TODO.md, high importance only."]
};

function queueRow(x){
  var old = x.days != null && x.days >= 7;
  return '<div class="q" data-sev="'+esc(x.sev)+'" data-href="'+esc(x.href||"")+'">'
    + '<span class="flag"></span>'
    + '<div class="q-main"><div class="q-t"><b>'+esc(x.title)+'</b>'
    + (x.meta ? '<span class="meta">'+esc(x.meta)+'</span>' : "") + '</div>'
    + (x.why ? '<div class="q-w">'+esc(x.why)+'</div>' : "")
    + (x.action ? '<div class="q-a">'+esc(x.action)+'</div>' : "")
    + '</div><div class="q-side">'
    + (x.days != null ? '<span class="q-age'+(old?" old":"")+'">'+ago(x.days)+'</span>' : "")
    + (x.tel ? '<a class="q-btn" href="'+esc(phoneHref(x.tel))+'" onclick="event.stopPropagation()">Call</a>'
             : '<span class="q-btn">Open</span>')
    + '</div></div>';
}

function viewToday(){
  var q = D.queue, groups = [], seen = {};
  q.forEach(function(x){ if (!seen[x.group]){ seen[x.group] = []; groups.push(x.group); } seen[x.group].push(x); });

  var body = "";
  if (!q.length){
    body = '<div class="done-s"><span class="tick">✓</span><div><div class="t">Nothing is waiting on you.</div>'
      + '<div class="d">No uncalled leads, no owed callbacks, no blocked pilots. Next build action: '
      + esc((PIPE.find(function(p){ return !p.blocker; }) || {}).next_action || "—") + '</div></div></div>';
  } else {
    groups.forEach(function(g){
      var items = seen[g], meta = GROUPS[g] || [g, ""];
      var shown = items.slice(0, 6), rest = items.length - shown.length;
      body += '<div class="qgroup"><div class="qhead"><span class="lab">'+esc(meta[0])+'</span>'
        + '<span class="n">'+items.length+'</span><span class="why">'+esc(meta[1])+'</span></div>'
        + '<div class="qlist">' + shown.map(queueRow).join("")
        + (rest > 0 ? '<div class="q" data-href="'+(g==="callback"?"#/leads/callbacks":g==="uncalled"?"#/leads/uncalled":"#/pipeline")+'">'
            + '<span class="flag"></span><div class="q-main"><div class="q-t"><b class="dim">+ '+rest+' more</b></div></div>'
            + '<div class="q-side"><span class="q-btn">Open</span></div></div>' : "")
        + '</div></div>';
    });
  }

  var ins = D.insights.slice(0, 3).map(function(i){
    return '<div class="ins" data-sev="'+esc(i.sev)+'"><div class="ins-b">'
      + '<h3>'+esc(i.headline)+'</h3>'
      + '<div class="ev">'+esc(i.evidence)+'</div>'
      + '<div class="rec">'+esc(i.recommend)+'</div>'
      + (i.href ? '<a class="go" href="'+esc(i.href)+'">Open →</a>' : "") + '</div></div>';
  }).join("");

  var mini = PIPE.map(function(p){
    return '<div class="pcard" data-rec="'+esc(p.slug)+'"><div class="pc-top">'
      + '<span class="pc-rank">'+p.rank+'</span><span class="pc-name">'+esc(p.name)+'</span>'
      + '<div class="pc-right">'+srail(p.stage_i, true)
      + (p.state === "broken" ? '<span class="badge bad">leaking</span>'
        : p.state === "blocked" ? '<span class="badge warn">blocked</span>'
        : '<span class="badge">'+esc(p.stage)+'</span>')
      + '</div></div></div>';
  }).join("");

  var counts2 = C ? stat("Real leads", n(C.leads_real), "Sheet CRM · truth")
      + stat("Answered", n(C.calls.answered), n(C.calls.dialled) + " dialled")
      + stat("Talk time", dur(C.calls.talk_seconds), C.calls.conversations + " conversations")
      + stat("Interested", n(C.won.length), "said да on the phone", "acc") : "";

  return '<div class="stack">'
    + heroToday()
    + (ins ? '<div class="stack">' + ins + '</div>' : "")
    + '<div class="split"><div class="stack">' + body + '</div>'
    + '<div class="stack">'
      + panel("Pipeline", PIPE.length + " pilots", mini, "", true)
      + panel("Activity", "last 30 days", activityStrip(D.activity))
      + (counts2 ? panel("Lifetime", "since 21.07", '<div class="stats">'+counts2+'</div>', "", true) : "")
    + '</div></div></div>';
}

function viewPipeline(){
  if (route.tab === "table"){
    var rows = PIPE.map(function(p){
      return '<tr data-rec="'+esc(p.slug)+'"><td class="n dim">'+p.rank+'</td>'
        + '<td class="strong">'+esc(p.name)+'</td><td class="dim">'+esc(p.niche||"")+'</td>'
        + '<td>'+srail(p.stage_i, true)+'</td>'
        + '<td>'+(p.state==="broken"?'<span class="badge bad">leaking</span>':p.state==="blocked"?'<span class="badge warn">blocked</span>':'<span class="badge live">moving</span>')+'</td>'
        + '<td class="n">'+ago(p.idle)+'</td>'
        + '<td class="n">$'+n(p.deal_usd)+'</td>'
        + '<td class="n">'+p.free_campaigns_used+' / '+(B.offer?B.offer.free_campaigns_per_client:3)+'</td>'
        + '<td class="dim">'+esc(p.deploy_url ? p.deploy_url.replace("https://","") : "—")+'</td></tr>';
    }).join("");
    return panel("Seven pilots", "click a row for the full record",
      '<div class="tw"><table><thead><tr><th class="n no-sort">#</th><th class="no-sort">Client</th>'
      + '<th class="no-sort">Niche</th><th class="no-sort">Stage</th><th class="no-sort">State</th>'
      + '<th class="n no-sort">Idle</th><th class="n no-sort">Deal</th><th class="n no-sort">Free camp.</th>'
      + '<th class="no-sort">Deployed</th></tr></thead><tbody>'+rows+'</tbody></table></div>', "", true);
  }

  var byStage = {};
  D.stages.forEach(function(s){ byStage[s] = 0; });
  PIPE.forEach(function(p){ byStage[p.stage] = (byStage[p.stage]||0) + 1; });
  var railRow = '<div class="rowflex" style="gap:14px">' + D.stages.map(function(s,i){
    var c = byStage[s];
    return '<div style="flex:1;min-width:64px"><div class="lab" style="margin-bottom:6px">'+esc(s)+'</div>'
      + '<div style="height:4px;border-radius:2px;background:'+(c?"var(--live)":"rgba(255,255,255,.08)")+'"></div>'
      + '<div class="stat-v" style="font-size:17px;margin-top:8px;color:'+(c?"var(--ink-1)":"var(--ink-4)")+'">'+c+'</div></div>';
  }).join("") + '</div>';

  var cards = PIPE.map(function(p){
    return '<div class="pcard" data-rec="'+esc(p.slug)+'">'
      + '<div class="pc-top"><span class="pc-rank">'+p.rank+'</span>'
      + '<span class="pc-name">'+esc(p.name)+'</span>'
      + '<span class="pc-niche">'+esc(p.niche||"")+'</span>'
      + '<div class="pc-right">'
        + (p.noindex ? '<span class="badge">noindex</span>' : "")
        + (p.state === "broken" ? '<span class="badge bad">заявки в никуда</span>'
          : p.state === "blocked" ? '<span class="badge warn">blocked</span>'
          : '<span class="badge live">moving</span>')
        + srail(p.stage_i)
      + '</div></div>'
      + '<div class="pc-body">'
      + (p.blocker ? '<div class="pc-blk">'+esc(p.blocker)+'</div>' : "")
      + (p.next_action ? '<div class="pc-next">'+esc(p.next_action)+'</div>' : "")
      + '<div class="pc-meta"><span>stage · '+esc(p.stage)+'</span><span>idle '+ago(p.idle)+'</span>'
      + '<span>$'+n(p.deal_usd)+'</span>'
      + (p.deploy_url ? '<a href="'+esc(p.deploy_url)+'" target="_blank" rel="noopener" onclick="event.stopPropagation()">'+esc(p.deploy_url.replace("https://",""))+'</a>' : "")
      + '</div></div></div>';
  }).join("");

  return '<div class="stack">'
    + panel("Stages", "agreed → decision", railRow)
    + panel("Seven pilots", "ranked by closeness to a build · click for the record", cards, "", true)
    + '</div>';
}

/* ------------------------------------------------------------- leads ---- */
var SORTS = {
  ts:function(a,b){ return (a.ts||"").localeCompare(b.ts||""); },
  business:function(a,b){ return coll.compare(a.business||"", b.business||""); },
  followers:function(a,b){ return (a.followers||-1) - (b.followers||-1); },
  talk:function(a,b){ return a.talk - b.talk; },
  mtc:function(a,b){ return (a.mtc==null?1e9:a.mtc) - (b.mtc==null?1e9:b.mtc); },
  dialled:function(a,b){ return a.dialled - b.dialled; },
  category:function(a,b){ return coll.compare(a.category||"яя", b.category||"яя"); },
  language:function(a,b){ return coll.compare(a.language||"", b.language||""); },
  creative:function(a,b){ return coll.compare(a.creative||"", b.creative||""); }
};
var coll = new Intl.Collator("ru", { numeric:true, sensitivity:"base" });

function leadSubset(tab){
  if (!C) return [];
  if (tab === "callbacks") return C.debt.map(function(i){ return LEADS[i]; });
  if (tab === "uncalled")  return C.never_dialled.map(function(i){ return LEADS[i]; });
  if (tab === "won")       return C.won.map(function(i){ return LEADS[i]; });
  return LEADS.slice();
}
function applyFilters(list){
  var q = (route.q.get("q")||"").trim().toLowerCase();
  var cr = route.q.get("cr"), lg = route.q.get("lg"), bs = route.q.get("bs");
  return list.filter(function(L){
    if (cr && L.creative !== cr) return false;
    if (lg && L.language !== lg) return false;
    if (bs && L.business !== bs) return false;
    if (q){
      var hay = [L.business, L.language, L.handle, L.name, L.note, L.phone, L.category, L.creative, L.label]
        .join(" ").toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });
}
function viewLeads(){
  if (!C) return panel("Leads", "", emptyState("No CRM payload cached.",
    "Run python automations/dashboard/build.py --live with the VPN up."));
  if (route.tab === "speed") return viewSpeed();

  var base = leadSubset(route.tab), list = applyFilters(base);
  var sk = route.q.get("s") || "ts", dir = route.q.get("d") === "a" ? 1 : -1;
  if (SORTS[sk]) list.sort(function(a,b){ return SORTS[sk](a,b) * dir; });

  var chips = "";
  function chipGroup(param, obj, prefix){
    var cur = route.q.get(param);
    return Object.keys(obj).slice(0,5).map(function(k){
      return '<button class="chip" data-filter="'+param+'" data-val="'+esc(k)+'" aria-pressed="'+(cur===k)+'">'
        + esc(prefix ? prefix + k : k) + '<b>' + obj[k] + '</b></button>';
    }).join("");
  }
  chips = chipGroup("cr", C.by_creative) + chipGroup("lg", C.by_language);
  var any = route.q.get("cr") || route.q.get("lg") || route.q.get("bs") || route.q.get("q");

  var bar = '<div class="filters">'
    + '<label class="srch"><svg viewBox="0 0 16 16" width="13" height="13"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>'
    + '<input id="lead-q" placeholder="Search business, note, handle, phone…" value="'+esc(route.q.get("q")||"")+'"></label>'
    + chips
    + (any ? '<button class="chip" data-clear="1"><span class="x">×</span>clear</button>' : "")
    + '<span class="tiny dim" style="margin-left:auto">'+list.length+' of '+base.length+'</span></div>';

  function th(key, label, cls){
    var active = sk === key;
    return '<th class="'+(cls||"")+'" data-sort="'+key+'"'+(active?' aria-sort="'+(dir>0?"ascending":"descending")+'"':"")+'>'
      + esc(label) + '<span class="ar">'+(dir>0?"▲":"▼")+'</span></th>';
  }
  var rows = list.map(function(L){
    return '<tr data-rec="'+L.i+'"><td class="dim mono">'+esc(L.label||("#"+(L.i+1)))+'</td>'
      + '<td class="mono dim">'+dtime(L.ts)+'</td>'
      + '<td class="strong" title="'+esc(L.business||"")+'">'+esc(L.business||"—")+'</td>'
      + '<td class="dim">'+esc(L.language||"—")+'</td>'
      + '<td>'+(L.creative?'<span class="badge'+(L.creative==="video"?" live":"")+'">'+esc(L.creative)+'</span>':'<span class="dim">—</span>')+'</td>'
      + '<td class="mono dim" title="'+esc(L.handle_status||"")+'">'+(L.handle?"@"+esc(L.handle):"—")+'</td>'
      + '<td class="n">'+(L.followers==null?'<span class="dim">—</span>':n(L.followers))+'</td>'
      + '<td class="n">'+(L.dialled?L.dialled:'<span class="dim">0</span>')+'</td>'
      + '<td class="n">'+(L.talk?dur(L.talk):'<span class="dim">—</span>')+'</td>'
      + '<td class="n">'+(L.mtc==null?'<span class="dim">—</span>':mins(L.mtc))+'</td>'
      + '<td>'+(L.category?'<span class="badge'+(L.category==="интерес"?" live":L.category==="нет ответа"?"":" warn")+'">'+esc(L.category)+'</span>':'<span class="dim">—</span>')+'</td></tr>';
  }).join("");

  var table = '<div class="tw"><table><thead><tr>'
    + '<th class="no-sort">ID</th>' + th("ts","When") + th("business","Business")
    + th("language","Lang") + th("creative","Creative") + '<th class="no-sort">Instagram</th>'
    + th("followers","Followers","n") + th("dialled","Calls","n") + th("talk","Talk","n")
    + th("mtc","To 1st call","n") + th("category","Outcome")
    + '</tr></thead><tbody>'+rows+'</tbody></table>'
    + (list.length ? "" : '<div class="empty">Nothing matches these filters.</div>') + '</div>';

  var head = { all:["Every lead","61 real заявки, test rows and duplicate numbers excluded"],
    callbacks:["Owed a second touch","перезвонит сам · думает · отложил — oldest first, all already paid for"],
    uncalled:["Never dialled","no outgoing call on the phone log"],
    won:["Said да","note category интерес — these became the pilot board"] }[route.tab] || ["Leads",""];

  return '<div class="stack">' + bar + panel(head[0], head[1], table, "", true) + '</div>';
}

function viewSpeed(){
  var sp = C.speed, thin = sp.measured < D.confidence_n;
  var stats = '<div class="stats">'
    + stat("Median to first call", mins(sp.median_minutes), "across " + sp.measured + " measured leads")
    + stat("Inside an hour", sp.within_hour + " / " + sp.measured, thin ? "n below " + D.confidence_n + " · preliminary" : "", sp.within_hour/sp.measured < .3 ? "bad" : "")
    + stat("Never dialled", n(C.calls.never_dialled), "of " + C.leads_real + " real leads")
    + stat("They rang back", n(C.calls.called_back), C.calls.missed_from_them + " missed calls from leads")
    + '</div>';
  var legend = '<div class="legend"><span><i style="background:var(--live)"></i>заявки arriving</span>'
    + '<span><i style="background:var(--ink-3)"></i>calls going out</span></div>';
  return '<div class="stack">'
    + panel("Speed to lead", "hour of the Ashgabat day", stats, "", true)
    + panel("The gap", "when leads arrive vs when they get called",
        legend + hourChart(sp.by_hour)
        + '<p class="note" style="margin-top:14px">The two humps do not overlap. Leads land through the night and '
        + 'get dialled in one batch in the afternoon — that shape is a sleep cycle, not neglect, and it is a '
        + 'schedule change rather than an effort problem.</p>')
    + '</div>';
}

/* ------------------------------------------------------------- funnel --- */
function viewFunnel(){
  if (route.tab === "creatives") return viewCreatives();
  if (route.tab === "segments")  return viewSegments();

  var f = S.funnel, r = S.rates, m = S.money;
  /* Four orders of magnitude between stage 1 and stage 5. On one linear scale
     four of five bars pin to the floor; log or sqrt would flatter the data. So
     the scale BREAKS after impressions and the break is drawn and named. */
  var head = f[0], rest = f.slice(1);
  var restMax = Math.max.apply(null, rest.map(function(s){ return s.value || 0; })) || 1;
  var zoom = head.value && restMax ? Math.round(head.value / restMax) : null;

  function row(s, w, prev){
    var conv = prev && prev.value ? (100 * (s.value||0) / prev.value) : null;
    return (prev ? '<div class="fdrop"><div></div><div class="mid"><span class="tick"></span>'
        + '<span class="txt"><b>'+(conv==null?"—":conv.toFixed(conv<10?1:0)+"%")+'</b> of '+esc(prev.label.toLowerCase())+'</span>'
        + '</div><div></div></div>' : "")
      + '<div class="fstage'+(s.truth?" truth":"")+'"><div class="k"><b>'+esc(s.label)+'</b><span>'+esc(s.source)+'</span></div>'
      + '<div><div class="bar" style="width:'+w.toFixed(2)+'%"></div></div>'
      + '<div class="v">'+n(s.value)+(s.truth?'<em>truth</em>':"")+'</div></div>';
  }
  var body = row(head, 100, null)
    + '<div class="fdrop" style="margin:6px 0"><div></div><div class="mid" style="gap:10px">'
      + '<span style="flex:1;height:1px;background:repeating-linear-gradient(90deg,var(--hair3) 0 4px,transparent 4px 8px)"></span>'
      + '<span class="txt">scale break · the four stages below are drawn against link clicks'+(zoom?" (×"+n(zoom)+" zoom)":"")+'</span>'
      + '<span style="flex:1;height:1px;background:repeating-linear-gradient(90deg,var(--hair3) 0 4px,transparent 4px 8px)"></span>'
      + '</div><div></div></div>';
  rest.forEach(function(s, i){
    body += row(s, Math.max(0.6, 100 * (s.value||0) / restMax), i === 0 ? head : rest[i-1]);
  });

  var rec = S.reconciliation;
  var recBody = '<div class="rows">'
    + '<div class="brow"><div class="k">Meta pixel</div><div class="track"><div class="fill" style="width:'+(100*rec.meta_leads/Math.max(rec.crm_leads_real,1)).toFixed(1)+'%"></div></div><div class="v">'+n(rec.meta_leads)+'</div></div>'
    + '<div class="brow"><div class="k">GA4 submits</div><div class="track"><div class="fill" style="width:'+(100*rec.ga4_generate_lead/Math.max(rec.crm_leads_real,1)).toFixed(1)+'%"></div></div><div class="v">'+n(rec.ga4_generate_lead)+'</div></div>'
    + '<div class="brow on"><div class="k">Sheet CRM</div><div class="track"><div class="fill" style="width:100%"></div></div><div class="v">'+n(rec.crm_leads_real)+'</div></div>'
    + '</div><p class="note" style="margin-top:12px">Only the Sheet is truth. Meta reports '+n(rec.meta_leads)
    + ' against '+n(rec.crm_leads_real)+' real — a '+Math.abs(100*(rec.meta_leads-rec.crm_leads_real)/Math.max(rec.crm_leads_real,1)).toFixed(1)
    + '% gap. The old "pixel undercounts by 18%" rule was attribution lag inside a running campaign, not a systematic bias. Do not correct pixel figures.</p>';

  var eff = '<div class="stats">'
    + stat("Spend", money(m.spend), "lifetime, this window")
    + stat("Per link click", money(m.cost_per_link_click, 3), "")
    + stat("Per real заявка", money(m.cost_per_real_lead), "Sheet CRM denominator", "acc")
    + stat("Per answered call", C ? money(m.spend / Math.max(C.calls.answered,1)) : "—", C ? C.calls.answered + " answered" : "")
    + stat("Per closed pilot", money(m.spend / Math.max(PIPE.length,1)), PIPE.length + " pilots agreed", "acc")
    + '</div>';

  return '<div class="stack">'
    + panel("Efficiency", "what the money actually bought", eff, "", true)
    + panel("The chain", S.window.start + " → " + S.window.end, body)
    + '<div class="grid g2">'
      + panel("Three counts of the same event", "and why only one is truth", recBody)
      + panel("Not in this line, deliberately", "two stages that would lie",
          '<dl class="kv"><dt>Meta LPV</dt><dd>runs ~44% low against GA4 — the Instagram in-app browser drops the pixel while the GA4 tag survives. Stored, never divided by.</dd>'
          + '<dt>CF pageviews</dt><dd>~7× bot-inflated on the Free plan, which has no bot-management field to filter on. A ceiling, not a count.</dd></dl>')
    + '</div></div>';
}

function viewCreatives(){
  var q = C ? C.quality : [];
  var rows = q.map(function(x){
    return '<tr><td class="strong">'+esc(x.creative)+'</td>'
      + '<td class="n">'+n(x.leads)+'</td><td class="n">'+n(x.dialled)+'</td><td class="n">'+n(x.answered)+'</td>'
      + '<td class="n">'+(x.avg_talk?dur(x.avg_talk):'<span class="dim">—</span>')+'</td>'
      + '<td class="n">'+n(x.over3)+'</td><td class="n">'+n(x.deferred)+'</td>'
      + '<td class="n '+(x.won?"strong":"dim")+'">'+n(x.won)+'</td></tr>';
  }).join("");
  return '<div class="stack">'
    + panel("Creative quality, not creative volume",
        "average talk time is the column that changed the decision",
        '<div class="tw"><table><thead><tr><th class="no-sort">Creative</th><th class="n no-sort">Leads</th>'
        + '<th class="n no-sort">Dialled</th><th class="n no-sort">Answered</th><th class="n no-sort">Avg talk</th>'
        + '<th class="n no-sort">Over 3 min</th><th class="n no-sort">Deferred</th><th class="n no-sort">Interested</th>'
        + '</tr></thead><tbody>'+rows+'</tbody></table></div>', "", true)
    + '<div class="grid g2">'
      + panel("Share of leads", "all 7 pilots came in on video",
          C ? barRows(C.by_creative, { on:["video"] }) : "")
      + panel("Landing variant", "which page they actually saw",
          C ? barRows(C.by_variant, { hiFirst:true }) : "")
    + '</div></div>';
}

function viewSegments(){
  if (!C) return "";
  return '<div class="grid g2">'
    + panel("Business type", "niche-agnostic holds", barRows(C.by_business))
    + panel("Language", "what they chose in the chat", barRows(C.by_language, { hiFirst:true }))
    + panel("Call outcome", "note category, " + C.noted + " of " + C.leads_real + " noted", barRows(C.categories))
    + panel("Objections raised", "only " + C.objection_leads + " leads raised one at all",
        Object.keys(C.objections).length ? barRows(C.objections, { share:false })
        : emptyState("No objections recorded.", "Which is itself the finding — most calls end without one."))
    + '</div>';
}

/* ---------------------------------------------------------- marketing --- */
function viewMarketing(){
  var ads = B.ads || {};
  if (route.tab === "traffic"){
    return '<div class="stack">'
      + panel("Sessions", "GA4 · all traffic", dayBars(S.series, "sessions", { cls:"acc", h:80 }) + axl())
      + panel("Form submits", "GA4 generate_lead — the on-page event, not the Sheet",
          dayBars(S.series, "generate_lead", { cls:"live", h:64 }) + axl())
      + '<div class="grid g3">'
        + panel("Totals", "this window", '<div class="stats">'
            + stat("Sessions", n(S.totals.sessions), "")
            + stat("Paid social", n(S.totals.paid_sessions), "")
            + stat("Engaged", n(S.totals.engaged), "") + '</div>', "", true)
        + panel("Page conversion", "submits ÷ all sessions",
            '<div class="stats">' + stat("Rate", pct(S.rates.page_conversion), "GA4 ÷ GA4")
            + stat("Survives to CRM", pct(S.rates.survives), "real ÷ submits") + '</div>', "", true)
        + panel("Key events", "config, not reality",
            S.alarms.key_events_configured === false
              ? '<p class="note">generate_lead is <b>not</b> marked as a key event, so every conversion metric in the property reads 0 by configuration. Toggling it is not retroactive — July stays 0 forever.</p>'
              : '<p class="note">generate_lead is a key event. Figures accrue from the day it was toggled; earlier days stay 0.</p>')
      + '</div></div>';
  }
  if (route.tab === "instagram"){
    return '<div class="stack">'
      + panel("Profile", "@voronka.tm · organic only", '<div class="stats">'
          + stat("Followers", n(S.ig.followers), "capture-time, not date-time")
          + stat("Posts live", n(S.ig.posts_live), "")
          + '</div>', "", true)
      + panel("Why there is no organic chart here", "an honest gap",
          '<p class="note">Instagram gates the daily <span class="mono">follower_count</span> metric until roughly 100 followers, so every stored row carries '
          + 'today\'s number rather than that day\'s. Charting it as growth would draw a flat line and call it data. '
          + 'Account-level reach also mixes ad traffic with organic — over the 28 days to 26.07 it was 5,939 ad reach against 156 organic, '
          + 'so the reach spike on 23–25 July is the campaign, not the grid working. Run <span class="mono">/check-ig</span> for the split.</p>')
      + '</div>';
  }
  if (route.tab === "content"){
    var rows = (B.content||[]).map(function(c){
      return '<tr><td class="strong">'+esc(c.batch)+'</td>'
        + '<td>'+(c.done?'<span class="badge live">shipped</span>':'<span class="badge warn">open</span>')+'</td>'
        + '<td style="white-space:normal;max-width:none" class="dim">'+esc(c.state)+'</td></tr>';
    }).join("");
    return panel("Content batches", "generation rules live in the content-batch skill",
      '<div class="tw"><table><thead><tr><th class="no-sort">Batch</th><th class="no-sort">State</th>'
      + '<th class="no-sort">Detail</th></tr></thead><tbody>'+rows+'</tbody></table></div>', "", true);
  }

  var paused = ads.paused_since ? daysBetween(ads.paused_since, D.today) : null;
  var badge = ads.status === "PAUSED" ? '<span class="badge warn">paused '+(paused!=null?paused+"d":"")+'</span>' : '<span class="badge live">running</span>';
  return '<div class="stack">'
    + panel("test-01", (ads.ran_from||"").slice(0,10) + " → " + (ads.ran_to||"").slice(0,10),
        '<div class="stats">'
        + stat("Spend", money(S.money.spend), "lifetime")
        + stat("Impressions", n(S.totals.impressions), n(S.totals.reach) + " reach")
        + stat("Link clicks", n(S.totals.link_clicks), "CTR " + pct(S.rates.link_ctr))
        + stat("CPC", S.ads_latest ? money(S.ads_latest.cpc, 3) : "—", "last delivering day")
        + stat("Per real заявка", money(S.money.cost_per_real_lead), "Sheet denominator", "acc")
        + '</div>', badge, true)
    + panel("Spend", "$ per Ashgabat day · a hairline stub is a measured zero, a gap is a day with no data",
        dayBars(S.series, "spend", { cls:"acc", h:76 }) + axl())
    + panel("Real заявки", "Sheet CRM per day", dayBars(S.series, "leads", { cls:"live", h:64 }) + axl())
    + '<div class="grid g2">'
      + panel("Why campaign.py cannot build this", "and what would unlock it",
          '<p class="note">'+esc(ads.campaign_py_blocked||"")+' Likely unlock: a client with a registered business granting partner access.</p>')
      + panel("Standing rule", "learning phase",
          '<p class="note">Never edit a live campaign without saying so — an edit resets the learning phase. And a metric read mid-flight is a hypothesis, not a number: the 26.07 snapshot said $0.28 per заявка; the closed campaign says '+money(S.money.cost_per_real_lead)+'.</p>')
    + '</div></div>';
}
function axl(){
  var s = S.series;
  return '<div class="axl"><span>'+dshort(s[0].date)+'</span><span>'+dshort(s[Math.floor(s.length/2)].date)+'</span><span>'+dshort(s[s.length-1].date)+'</span></div>';
}

/* ------------------------------------------------------------- system --- */
function viewSystem(){
  if (route.tab === "loops"){
    var loops = (B.open_loops||[]).map(function(L){
      return '<div class="ins" data-sev="'+(L.severity==="high"?"act":L.severity==="medium"?"watch":"")+'"><div class="ins-b">'
        + '<h3>'+esc(L.n)+' · '+esc(L.title)+'</h3>'
        + (L.text ? '<div class="rec">'+esc(L.text)+'</div>' : "")
        + '<div class="ev">severity '+esc(L.severity)+'</div></div></div>';
    }).join("");
    return '<div class="stack">'+loops+'</div>';
  }
  if (route.tab === "tasks"){
    var rows = (B.todo||[]).map(function(t){
      return '<tr><td class="n dim">'+t.n+'</td><td class="strong">'+esc(t.title)+'</td>'
        + '<td>'+(t.importance==="высокая"?'<span class="badge live">высокая</span>':'<span class="badge">'+esc(t.importance)+'</span>')+'</td>'
        + '<td class="dim">'+esc(t.urgency)+'</td><td class="mono dim">'+esc(t.where)+'</td>'
        + '<td class="dim">'+esc(t.status)+'</td></tr>';
    }).join("");
    return panel("TODO.md", "importance moves revenue; urgency is tied to an event, not a date",
      '<div class="tw"><table><thead><tr><th class="n no-sort">#</th><th class="no-sort">Задача</th>'
      + '<th class="no-sort">Важность</th><th class="no-sort">Срочность</th><th class="no-sort">Где</th>'
      + '<th class="no-sort">Статус</th></tr></thead><tbody>'+rows+'</tbody></table></div>', "", true);
  }
  if (route.tab === "sources"){
    var src = [
      ["Meta Marketing API","meta-ads/report.py","spend, impressions, link clicks, CPC/CTR","estimate"],
      ["GA4 Data API","ga4/report.py","sessions, paid sessions, generate_lead","estimate"],
      ["Google Sheet CRM","sheets/crm.py","real заявки, chat answers, notes","TRUTH"],
      ["Phone XML export","sheets/calls.py","dialled, answered, talk seconds","manual export"],
      ["Instagram Graph","ig-insights/report.py","followers, organic vs ad reach","gated under ~100 followers"],
      ["Cloudflare","cloudflare/report.py","function errors, origin 5xx","alarms only, UTC"]
    ].map(function(s){
      return '<tr><td class="strong">'+esc(s[0])+'</td><td class="mono dim">'+esc(s[1])+'</td>'
        + '<td class="dim" style="white-space:normal;max-width:none">'+esc(s[2])+'</td>'
        + '<td>'+(s[3]==="TRUTH"?'<span class="badge live">truth</span>':'<span class="badge">'+esc(s[3])+'</span>')+'</td></tr>';
    }).join("");
    return '<div class="stack">'
      + panel("Six readers, one row", "snapshot-schema.md is law for the shape",
        '<div class="tw"><table><thead><tr><th class="no-sort">Source</th><th class="no-sort">Reader</th>'
        + '<th class="no-sort">Contributes</th><th class="no-sort">Standing</th></tr></thead><tbody>'+src+'</tbody></table></div>', "", true)
      + panel("Three tiers, and the page says which is which", "",
        '<dl class="kv"><dt>Stored rows</dt><dd>'+S.window.rows+' days, '+S.window.start+' → '+S.window.end+'. Always available, no network. Rows stay mutable for three days, then freeze.</dd>'
        + '<dt>CRM</dt><dd>'+(D.crm_fetched_at ? "fetched " + esc(D.crm_fetched_at.replace("T"," ").slice(0,16)) + " UTC" : "no cache")+'. Live only behind --live.</dd>'
        + '<dt>Projection</dt><dd>business.json, written by /dashboard from STATE.md, TODO.md and the client folders. Carries a SHA-1 of every source; a mismatch banners the page.</dd></dl>')
      + '</div>';
  }

  var h = S.health, missing = h.missing||[], moving = h.moving||[];
  var drift = (D.drifted||[]);
  var checks = '<div class="stats">'
    + stat("Function errors", n(S.alarms.function_errors), "Cloudflare, this window", S.alarms.function_errors ? "bad":"")
    + stat("Origin 5xx", n(S.alarms.origin_5xx), "", S.alarms.origin_5xx ? "bad":"")
    + stat("Missing captures", missing.length, missing.length ? missing.map(dshort).join(", ") : "none", missing.length ? "bad":"")
    + stat("Still moving", moving.length, "rows younger than 3 days")
    + stat("Reader failures", Object.keys(h.failures||{}).length, Object.keys(h.failures||{}).join(", ") || "none",
        Object.keys(h.failures||{}).length ? "bad":"")
    + stat("Projection drift", drift.length, drift.length ? drift.map(function(d){return d.file;}).join(", ") : "in sync", drift.length ? "bad":"")
    + '</div>';

  var dq = C ? '<dl class="kv">'
    + '<dt>Raw rows</dt><dd>'+n(C.rows)+' in the sheet</dd>'
    + '<dt>Real leads</dt><dd>'+n(C.leads_real)+' after removing '+n(C.duplicate_phones)+' duplicate numbers and '+n(C.tests_hidden)+' test row'+(C.tests_hidden===1?"":"s")+'</dd>'
    + '<dt>No phone</dt><dd>'+n(C.no_phone)+' — the chat fired but the submit never landed. That is a capture bug, not a lead.</dd>'
    + '<dt>Notes written</dt><dd>'+n(C.noted)+' of '+n(C.leads_real)+'. A blank is "no note yet", never "went nowhere".</dd>'
    + '</dl>' : "";

  return '<div class="stack">'
    + panel("Checks", "everything that can quietly go wrong", checks, "", true)
    + '<div class="grid g2">'
      + panel("Lead data quality", "what the 61 is net of", dq)
      + panel("Rules that are easy to get wrong", "snapshot-schema.md",
        '<dl class="kv"><dt>Null ≠ zero</dt><dd>A failed reader stores null. "The tunnel dropped" and "reach was zero" must never collapse into the same value — a gap is drawn as a gap.</dd>'
        + '<dt>Ashgabat dates</dt><dd>Meta, GA4 and the Sheet all report in it, so they line up day for day. Cloudflare is UTC and sits 5 hours off, which is why nothing from it enters the funnel.</dd>'
        + '<dt>Three-day thaw</dt><dd>GA4 backfills ~48h and Meta lags hours. A row is not final until D+3, so never call a trend off the last three days.</dd></dl>')
    + '</div></div>';
}

/* ------------------------------------------------------------- drawer --- */
function openRec(id){ setQuery(function(q){ q.set("rec", id); }); }
function closeRec(){ setQuery(function(q){ q.delete("rec"); }); }

function drawerLead(L){
  var callRows = L.calls.length ? '<ul class="tl">' + L.calls.map(function(c){
    var out = c.event === "исходящий";
    return '<li><span class="pip '+(out?"in":"ok")+'"></span><div><div class="d">'+esc(c.event)
      + (c.duration ? ' · ' + dur(c.duration) : ' · no answer') + '</div>'
      + '<div class="t">'+esc((c.ts||"").replace("T"," ").slice(0,16))+'</div></div></li>';
  }).join("") + '</ul>' : '<p class="note dim">No calls on the phone log.</p>';

  var qa = L.qa.length ? '<ul class="tl">' + L.qa.map(function(r){
    return '<li><span class="pip"></span><div><div class="t">'+esc(r.q)+'</div><div class="d">'+esc(r.a)+'</div></div></li>';
  }).join("") + '</ul>' : "";

  var prof = L.handle ? '<dl class="kv">'
    + '<dt>Handle</dt><dd class="mono">@'+esc(L.handle)+'</dd>'
    + (L.name ? '<dt>Name</dt><dd>'+esc(L.name)+'</dd>' : "")
    + (L.followers != null ? '<dt>Followers</dt><dd>'+n(L.followers)+(L.posts!=null?' · '+n(L.posts)+' posts':"")+'</dd>' : "")
    + (L.er != null ? '<dt>Engagement</dt><dd>'+L.er+'% · median '+n(L.median_views||0)+' views</dd>' : "")
    + (L.last_post ? '<dt>Last post</dt><dd>'+esc(L.last_post)+'</dd>' : "")
    + (L.handle_status ? '<dt>Resolution</dt><dd class="dim">'+esc(L.handle_status)+'</dd>' : "")
    + '</dl>' : '<p class="note dim">Handle never resolved'+(L.handle_raw?' — they typed «'+esc(L.handle_raw)+'»':"")+'.</p>';

  return '<div class="dsec"><div class="dact">'
      + (L.digits ? '<a class="btn pri" href="'+esc(phoneHref(L.digits))+'">Call '+esc(L.phone)+'</a>' : "")
      + (L.handle ? '<a class="btn" href="https://instagram.com/'+esc(L.handle)+'" target="_blank" rel="noopener">Instagram</a>' : "")
      + '</div></div>'
    + '<div class="dsec"><span class="lab">Заявка</span><dl class="kv">'
      + '<dt>Arrived</dt><dd>'+esc((L.ts||"").replace("T"," "))+' · '+ago(L.days)+' ago</dd>'
      + '<dt>Business</dt><dd>'+esc(L.business||"—")+'</dd>'
      + '<dt>Language</dt><dd>'+esc(L.language||"—")+'</dd>'
      + '<dt>Creative</dt><dd>'+esc(L.creative||"unattributed")+(L.variant?' · variant '+esc(L.variant):"")+'</dd>'
      + '</dl></div>'
    + (L.category || L.note ? '<div class="dsec"><span class="lab">What was said</span>'
      + (L.category ? '<div class="rowflex"><span class="badge'+(L.category==="интерес"?" live":" warn")+'">'+esc(L.category)+'</span>'
        + L.objections.map(function(o){ return '<span class="badge bad">'+esc(o)+'</span>'; }).join("") + '</div>' : "")
      + (L.note ? '<div class="quote">'+esc(L.note)+'</div>' : "")
      + (L.follow_up ? '<p class="note">→ '+esc(L.follow_up)+'</p>' : "") + '</div>' : "")
    + '<div class="dsec"><span class="lab">Calls</span>'
      + '<dl class="kv"><dt>To first call</dt><dd>'+mins(L.mtc)+'</dd>'
      + '<dt>Talk total</dt><dd>'+dur(L.talk)+(L.talk_longest?' · longest '+dur(L.talk_longest):"")+'</dd>'
      + '<dt>They rang back</dt><dd>'+(L.called_back?"yes":"no")+(L.missed_from_them?' · '+L.missed_from_them+' missed from them':"")+'</dd></dl>'
      + callRows + '</div>'
    + '<div class="dsec"><span class="lab">Instagram</span>'+prof+(L.bio?'<div class="quote">'+esc(L.bio)+'</div>':"")+'</div>'
    + (qa ? '<div class="dsec"><span class="lab">Chat log</span>'+qa+'</div>' : "");
}

function drawerPilot(p){
  return '<div class="dsec"><div class="rowflex">'
      + srail(p.stage_i)
      + (p.state==="broken"?'<span class="badge bad">заявки в никуда</span>':p.state==="blocked"?'<span class="badge warn">blocked</span>':'<span class="badge live">moving</span>')
      + (p.noindex?'<span class="badge">noindex</span>':"")
      + '</div>'
      + (p.deploy_url ? '<div class="dact" style="margin-top:10px"><a class="btn pri" href="'+esc(p.deploy_url)+'" target="_blank" rel="noopener">Open the page</a></div>' : "")
      + '</div>'
    + (p.blocker ? '<div class="dsec"><span class="lab">Blocker</span><div class="quote">'+esc(p.blocker)+'</div></div>' : "")
    + (p.next_action ? '<div class="dsec"><span class="lab">Next action</span><p class="note" style="color:var(--ink-2)">'+esc(p.next_action)+'</p></div>' : "")
    + (p.highlight ? '<div class="dsec"><span class="lab">What is built</span><p class="note">'+esc(p.highlight)+'</p></div>' : "")
    + '<div class="dsec"><span class="lab">Record</span><dl class="kv">'
      + '<dt>Rank</dt><dd>'+p.rank+' of '+PIPE.length+'</dd>'
      + '<dt>Stage</dt><dd>'+esc(p.stage)+'</dd>'
      + '<dt>Niche</dt><dd>'+esc(p.niche||"—")+'</dd>'
      + '<dt>Deal</dt><dd>$'+n(p.deal_usd)+' + '+(B.offer?B.offer.free_campaigns_per_client:3)+' free campaigns ('+p.free_campaigns_used+' used)</dd>'
      + '<dt>Last touch</dt><dd>'+esc(p.last_touch||"—")+' · idle '+ago(p.idle)+'</dd>'
      + (p.deployed_on ? '<dt>Deployed</dt><dd>'+esc(p.deployed_on)+'</dd>' : "")
      + '<dt>Slug</dt><dd class="mono">'+esc(p.slug)+'</dd>'
      + (p.build_repo ? '<dt>Build repo</dt><dd class="mono">'+esc(p.build_repo)+'</dd>' : "")
      + '</dl></div>';
}

function drawDrawer(){
  var rec = route.q.get("rec"), d = el("drawer");
  if (!rec){ d.hidden = true; el("scrim").hidden = true; return; }
  var title = "", sub = "", body = "";
  if (route.sec === "leads" && LEADS[+rec]){
    var L = LEADS[+rec];
    title = L.business || L.phone || "Заявка";
    sub = (L.label ? L.label + " · " : "") + dtime(L.ts) + " · " + (L.phone || "no phone");
    body = drawerLead(L);
  } else {
    var p = PIPE.filter(function(x){ return x.slug === rec; })[0];
    if (!p){ d.hidden = true; el("scrim").hidden = true; return; }
    title = p.name; sub = p.slug; body = drawerPilot(p);
  }
  el("drawer-title").innerHTML = '<b>'+esc(title)+'</b><span>'+esc(sub)+'</span>';
  el("drawer-body").innerHTML = body;
  el("drawer-body").scrollTop = 0;
  d.hidden = false; el("scrim").hidden = false;
}

/* ------------------------------------------------------------- render --- */
var VIEWS = { today:viewToday, pipeline:viewPipeline, leads:viewLeads,
              funnel:viewFunnel, marketing:viewMarketing, system:viewSystem };

function paint(){
  var meta = ROUTES[route.sec];
  el("page-title").textContent = meta.title;
  el("page-sub").textContent = meta.sub;
  document.title = meta.title + " · VAIOS";

  var tabCounts = {};
  if (C){ tabCounts.callbacks = C.debt.length; tabCounts.uncalled = C.calls.never_dialled;
          tabCounts.won = C.won.length; tabCounts.all = C.leads_real; }
  el("tabs").innerHTML = meta.tabs.map(function(t){
    return '<a class="tab" role="tab" href="'+href(route.sec, t[0])+'" aria-selected="'+(t[0]===route.tab)+'">'
      + esc(t[1]) + (tabCounts[t[0]] != null ? '<b>'+tabCounts[t[0]]+'</b>' : "") + '</a>';
  }).join("");

  [].forEach.call(document.querySelectorAll(".nav-a"), function(a){
    if (a.dataset.sec === route.sec) a.setAttribute("aria-current","page");
    else a.removeAttribute("aria-current");
  });

  el("view").innerHTML = VIEWS[route.sec]();
  el("view").scrollTop = 0;
  drawDrawer();
  wireView();
}
function render(){
  /* Same-document view transitions turn a hash change into something that
     reads as an app rather than a reload. Keyboard-initiated navigation skips
     it on purpose: motion on an action you perform 100 times a day reads as
     lag, not polish. */
  if (document.startViewTransition && !kbNav) document.startViewTransition(paint);
  else paint();
  kbNav = false;
}
var kbNav = false;

/* -------------------------------------------------------------- wiring -- */
var cursor = -1;

/* #view survives every paint — only its innerHTML changes. So this delegated
   listener is attached ONCE at boot. Re-attaching it per render silently
   stacks handlers, and a chip that toggles twice looks like a chip that does
   nothing. */
function wireOnce(){
  el("view").addEventListener("click", function(e){
    var chip = e.target.closest("[data-filter]");
    if (chip){
      var p = chip.dataset.filter, val = chip.dataset.val;
      setQuery(function(q){ q.get(p) === val ? q.delete(p) : q.set(p, val); });
      return;
    }
    if (e.target.closest("[data-clear]")){
      setQuery(function(q){ ["q","cr","lg","bs"].forEach(function(k){ q.delete(k); }); });
      return;
    }
    var th = e.target.closest("th[data-sort]");
    if (th){
      var k = th.dataset.sort, cur = route.q.get("s") || "ts";
      setQuery(function(q){ q.set("s", k); q.set("d", cur === k && route.q.get("d") !== "a" ? "a" : "d"); });
      return;
    }
    var rec = e.target.closest("[data-rec]");
    if (rec){ openRec(rec.dataset.rec); return; }
    var q = e.target.closest(".q[data-href]");
    if (q && q.dataset.href){ location.hash = q.dataset.href.slice(1); return; }
  });
}

/* Per-paint wiring: everything below hangs off nodes that innerHTML just
   replaced, so it must run again — and only these. */
function wireView(){
  var lq = el("lead-q");
  if (lq){
    var t;
    lq.addEventListener("input", function(){
      clearTimeout(t);
      t = setTimeout(function(){
        var pos = lq.selectionStart, val = lq.value;
        setQuery(function(q){ val ? q.set("q", val) : q.delete("q"); });
        var again = el("lead-q");
        if (again){ again.focus(); again.setSelectionRange(pos, pos); }
      }, 160);
    });
  }
  cursor = -1;
  wireCharts();
}

/* One delegated mousemove per chart beats one invisible rect per bar. */
var tip;
function wireCharts(){
  if (!tip){ tip = document.createElement("div"); tip.className = "tip"; document.body.appendChild(tip); }
  [].forEach.call(document.querySelectorAll('svg[data-chart="days"]'), function(svg){
    var key = svg.dataset.key;
    svg.addEventListener("mousemove", function(e){
      var r = svg.getBoundingClientRect();
      var i = Math.floor((e.clientX - r.left) / r.width * S.series.length);
      if (i < 0 || i >= S.series.length) return;
      var s = S.series[i], val = s.missing ? null : s[key];
      tip.innerHTML = '<b>' + s.date + '</b><br>'
        + (s.missing ? "no snapshot written"
           : val == null ? "reader failed: " + (s.failed||[]).join(", ")
           : (key === "spend" ? "$" + val.toFixed(2) : n(val)) + " " + key.replace("_"," ")
             + (s.final ? "" : " · still moving"));
      tip.style.left = Math.min(Math.max(e.clientX - 60, 8), innerWidth - 190) + "px";
      tip.style.top = (r.top - 52) + "px";
      tip.classList.add("on");
    });
    svg.addEventListener("mouseleave", function(){ tip.classList.remove("on"); });
  });
}

/* --------------------------------------------------------- cmd palette -- */
var CMDS = [];
function buildCommands(){
  CMDS = [];
  Object.keys(ROUTES).forEach(function(k){
    var r = ROUTES[k];
    CMDS.push({ g:"Go to", label:r.title, hint:"g " + k[0], key:r.title + " " + r.sub, go:href(k,"") });
    r.tabs.forEach(function(t){
      CMDS.push({ g:"Go to", label:r.title + " · " + t[1], hint:"", key:r.title+" "+t[1], go:href(k,t[0]) });
    });
  });
  PIPE.forEach(function(p){
    CMDS.push({ g:"Pilots", label:p.name, hint:p.stage,
      key:[p.name,p.slug,p.niche,p.blocker,p.next_action].join(" "),
      go:href("pipeline","board",{rec:p.slug}) });
  });
  LEADS.forEach(function(L){
    CMDS.push({ g:"Leads", label:(L.business||L.phone||"заявка") + (L.handle?" · @"+L.handle:""),
      hint:L.category || dshort(L.day),
      key:[L.business,L.handle,L.name,L.phone,L.note,L.category,L.language,L.label].join(" "),
      go:href("leads","all",{rec:L.i}) });
  });
  (B.open_loops||[]).forEach(function(L){
    CMDS.push({ g:"Open loops", label:L.title, hint:L.severity, key:L.title+" "+(L.text||""), go:href("system","loops") });
  });
  (B.todo||[]).forEach(function(t){
    CMDS.push({ g:"Tasks", label:t.title, hint:t.importance, key:t.title+" "+(t.where||""), go:href("system","tasks") });
  });
}

/* Subsequence match with adjacency, word-start and prefix bonuses. Enough to
   rank "перезв" above a substring hit halfway through a note, and small enough
   to inline. */
function score(hay, needle){
  var h = hay.toLowerCase(), q = needle.toLowerCase();
  if (!q) return 0;
  if (h.indexOf(q) === 0) return 1000;
  var direct = h.indexOf(q);
  if (direct > 0) return 600 - Math.min(direct, 200);
  var hi = 0, s = 0, run = 0;
  for (var qi = 0; qi < q.length; qi++){
    var f = h.indexOf(q[qi], hi);
    if (f < 0) return -1;
    if (f === hi && qi > 0){ run += 5; s += 5 + run; }
    else { run = 0; s += 1; if (f === 0 || /[\s@._\-/·]/.test(h[f-1])) s += 10; }
    hi = f + 1;
  }
  return s;
}
function cmdkRender(){
  var q = el("cmdk-q").value.trim();
  var list = CMDS;
  if (q){
    list = CMDS.map(function(c){ return { c:c, s:score(c.label + " " + c.key, q) }; })
      .filter(function(x){ return x.s > 0; })
      .sort(function(a,b){ return b.s - a.s; })
      .slice(0, 40).map(function(x){ return x.c; });
  } else {
    list = CMDS.filter(function(c){ return c.g === "Go to"; }).slice(0, 12);
  }
  var out = "", lastG = null;
  list.forEach(function(c, i){
    if (c.g !== lastG){ out += '<li class="grp" aria-hidden="true">'+esc(c.g)+'</li>'; lastG = c.g; }
    out += '<li role="option" id="cmd-'+i+'" data-go="'+esc(c.go)+'" aria-selected="'+(i===cmdkI)+'">'
      + '<b>'+esc(c.label)+'</b>' + (c.hint ? '<span class="h">'+esc(c.hint)+'</span>' : "") + '</li>';
  });
  el("cmdk-list").innerHTML = out || '<div class="none">Nothing matches «'+esc(q)+'»</div>';
  var sel = el("cmdk-list").querySelector('[aria-selected="true"]');
  if (sel) sel.scrollIntoView({ block:"nearest" });
  el("cmdk-q").setAttribute("aria-activedescendant", sel ? sel.id : "");
}
var cmdkI = 0;
function cmdkOpen(){
  cmdkI = 0; buildCommands();
  var d = el("cmdk"); d.showModal(); el("cmdk-q").value = ""; cmdkRender(); el("cmdk-q").focus();
}
function cmdkMove(dir){
  var items = el("cmdk-list").querySelectorAll('[role="option"]');
  if (!items.length) return;
  cmdkI = (cmdkI + dir + items.length) % items.length;
  cmdkRender();
}
function cmdkGo(){
  var sel = el("cmdk-list").querySelector('[aria-selected="true"]');
  if (!sel) return;
  el("cmdk").close();
  location.hash = sel.dataset.go.slice(1);
}

/* ------------------------------------------------------------ keyboard -- */
var chord = null, chordAt = 0;
var KEYS = [
  ["Command palette","⌘K"],["Search this page","/"],["Shortcuts","?"],
  ["Today","g t"],["Pipeline","g p"],["Leads","g l"],["Funnel","g f"],
  ["Marketing","g m"],["System","g s"],["Move down / up","j k"],
  ["Open record","↵"],["Close","esc"],["Collapse sidebar","["],["Density","d"]
];
function drawKeys(){
  el("keys-body").innerHTML = KEYS.map(function(k){
    return '<div>'+esc(k[0])+'<span>'+k[1].split(" ").map(function(x){ return '<kbd>'+esc(x)+'</kbd>'; }).join("")+'</span></div>';
  }).join("");
}
function moveCursor(dir){
  var rows = el("view").querySelectorAll("tbody tr, .q, .pcard");
  if (!rows.length) return;
  if (cursor >= 0 && rows[cursor]) rows[cursor].classList.remove("cursor-row");
  cursor = Math.max(0, Math.min(rows.length - 1, cursor + dir));
  rows[cursor].classList.add("cursor-row");
  rows[cursor].scrollIntoView({ block:"nearest" });
}
function activateCursor(){
  var rows = el("view").querySelectorAll("tbody tr, .q, .pcard");
  if (cursor < 0 || !rows[cursor]) return;
  var r = rows[cursor];
  if (r.dataset.rec) openRec(r.dataset.rec);
  else if (r.dataset.href) location.hash = r.dataset.href.slice(1);
}

document.addEventListener("keydown", function(e){
  var t = e.target, typing = /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable;

  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k"){ e.preventDefault(); cmdkOpen(); return; }

  if (el("cmdk").open){
    if (e.key === "ArrowDown"){ e.preventDefault(); cmdkMove(1); }
    else if (e.key === "ArrowUp"){ e.preventDefault(); cmdkMove(-1); }
    else if (e.key === "Enter"){ e.preventDefault(); cmdkGo(); }
    else setTimeout(function(){ cmdkI = 0; cmdkRender(); }, 0);
    return;
  }
  if (typing){
    if (e.key === "Escape"){ t.blur(); }
    return;
  }
  if (e.metaKey || e.ctrlKey || e.altKey) return;

  if (chord === "g" && performance.now() - chordAt < 1200){
    var map = { t:"today", p:"pipeline", l:"leads", f:"funnel", m:"marketing", s:"system" };
    chord = null;
    if (map[e.key]){ e.preventDefault(); kbNav = true; location.hash = href(map[e.key], "").slice(1); }
    return;
  }
  chord = null;

  switch (e.key){
    case "g": chord = "g"; chordAt = performance.now(); break;
    case "?": e.preventDefault(); drawKeys(); el("keys").showModal(); break;
    case "/": e.preventDefault();
      var f = el("lead-q"); if (f) f.focus(); else cmdkOpen(); break;
    case "j": e.preventDefault(); moveCursor(1); break;
    case "k": e.preventDefault(); moveCursor(-1); break;
    case "Enter": activateCursor(); break;
    case "Escape":
      if (!el("drawer").hidden) closeRec();
      else if (document.documentElement.dataset.rail === "open") document.documentElement.dataset.rail = "";
      break;
    case "[": toggleRail(); break;
    case "d":
      var dn = document.documentElement.dataset.density === "compact" ? "comfortable" : "compact";
      document.documentElement.dataset.density = dn; sset("density", dn); break;
  }
});

function toggleRail(){
  var r = document.documentElement.dataset.rail === "collapsed" ? "" : "collapsed";
  document.documentElement.dataset.rail = r; sset("rail", r);
}

/* ---------------------------------------------------------------- boot -- */
function boot(){
  var savedRail = sget("rail"); if (savedRail) document.documentElement.dataset.rail = savedRail;
  var savedD = sget("density"); if (savedD) document.documentElement.dataset.density = savedD;

  drawNav(); drawFreshness(); drawKeys(); wireOnce();

  on(el("rail-toggle"), "click", toggleRail);
  on(el("rail-open"), "click", function(){
    document.documentElement.dataset.rail = document.documentElement.dataset.rail === "open" ? "" : "open";
  });
  on(el("open-cmdk"), "click", cmdkOpen);
  on(el("open-cmdk-2"), "click", cmdkOpen);
  on(el("cmdk-list"), "click", function(e){
    var li = e.target.closest("[data-go]"); if (!li) return;
    el("cmdk").close(); location.hash = li.dataset.go.slice(1);
  });
  on(el("cmdk"), "click", function(e){ if (e.target === el("cmdk")) el("cmdk").close(); });
  on(el("keys"), "click", function(e){ if (e.target === el("keys")) el("keys").close(); });
  on(el("drawer-close"), "click", closeRec);
  on(el("scrim"), "click", closeRec);
  on(el("nav"), "click", function(){ if (innerWidth <= 820) document.documentElement.dataset.rail = ""; });
  /* The off-canvas dimmer is #main::before, so its taps arrive here. Capture,
     so the tap closes the rail instead of hitting whatever sits underneath. */
  el("main").addEventListener("click", function(e){
    if (document.documentElement.dataset.rail !== "open") return;
    e.preventDefault(); e.stopPropagation();
    document.documentElement.dataset.rail = "";
  }, true);

  window.addEventListener("hashchange", function(){ route = parseHash(); render(); });
  route = parseHash();
  paint();

  /* Stamp the visit AFTER the first paint so "new since last visit" compares
     against the previous session, not this one. */
  setTimeout(function(){ sset("lastVisit", new Date().toISOString()); }, 1200);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();

})();
