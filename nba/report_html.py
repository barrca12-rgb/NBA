"""Daily NBA card as a self-contained HTML page: today's totals plays, spread leans, the odds board, the record and
the ratings. Same design as the CBB card (barrca12-rgb/CBB cbb/report_html.py): one typeface with tabular figures,
neutral surfaces, color only where it means something; light and dark follow the system setting. The Update button
starts this repo's update workflow with a GitHub token kept only in the browser.
"""
from __future__ import annotations

import html
import json
import math

import numpy as np
import pandas as pd

REPO = "barrca12-rgb/NBA"
SITE = "https://barrca12-rgb.github.io/"
SITE_URL = SITE + "NBA/"
X_HANDLE = "OffTheGlassHQ"
# Off The Glass brand, same as the CBB card (barrca12-rgb/CBB cbb/report_html.py HEAD and BRAND); site/assets is
# copied into the site by the workflow
HEAD = f"""<meta name="description" content="Off The Glass: an NBA betting model. Every play logged at the posted number, graded in public.">
<meta name="theme-color" content="#0A2C49">
<link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="64x64" href="assets/favicon-64.png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<meta property="og:site_name" content="Off The Glass">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE_URL}assets/otg-social.jpg">
<meta property="og:description" content="NBA model: every play logged at the posted number, graded in public.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@{X_HANDLE}">
<meta name="twitter:image" content="{SITE_URL}assets/otg-social.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Graduate&family=Inter:wght@400;500;600;700;800&display=swap">"""
BRAND = ('<a class="brand" href="./" aria-label="Off The Glass home"><img src="assets/otg-logo-512.png" alt="" width="34" height="34">'
         '<span class="wordmark">Off The Glass</span></a>')


def _clean(v):
    if v is None:
        return None
    if isinstance(v, list):
        return [{k: _clean(x) for k, x in o.items()} for o in v]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (np.floating, float)):
        return None if math.isnan(v) else round(float(v), 3)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v if isinstance(v, (int, str, bool)) else str(v)


def build(games: list[dict], rt: pd.DataFrame, names: dict, day: pd.Timestamp, season: int, record: dict | None,
          sgo_usage: dict | None = None) -> str:
    t = rt.reset_index(names="espn_id")
    t["team"] = t["espn_id"].map(names)
    t["rank"] = range(1, len(t) + 1)
    rat = [{k: _clean(v) for k, v in r.items()} for r in
           t[["rank", "team", "net", "adj_oe", "adj_de", "adj_tempo"]].to_dict("records")]
    data = {"date": f"{day:%Y-%m-%d}", "season": season, "repo": REPO, "site": SITE,
            "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
            "games": [_clean(g) for g in games], "ratings": rat, "record": _clean(record) if record else None,
            "usage": sgo_usage or {}}
    payload = json.dumps(data).replace("</", "<\\/")
    title = f"Off The Glass · NBA · {day:%a %b} {day.day}"
    return (TEMPLATE.replace("__HEAD__", HEAD).replace("__BRAND__", BRAND).replace("__X__", X_HANDLE)
            .replace("__TITLE__", html.escape(title)).replace("__DATA__", payload))


TEMPLATE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta property="og:title" content="__TITLE__">
__HEAD__
<style>
:root {
  --bg: #fbf6ea; --surface: #ffffff; --sunken: #f7f0e1; --line: #ebe1cd; --line-strong: #d9cbb0;
  --text: #0a2c49; --muted: #56627a; --faint: #8a93a3;
  --accent: #b84a08; --pos: #0f7b4b; --pos-bg: #e6f4ed; --neg: #c2352b; --warn: #8a5a00; --warn-bg: #fbf0d9;
  --brand: #fd6c0f; --bar: #0a2c49; --bar-text: #fbf6ea; --bar-muted: #b7c3d3;
  --font: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --display: "Graduate", "Rockwell", Georgia, serif;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #08090b; --surface: #12151a; --sunken: #181c22; --line: #242a33; --line-strong: #333b46;
    --text: #f6eedd; --muted: #a8b0bc; --faint: #6f7886;
    --accent: #ff8a3d; --pos: #3ccf8e; --pos-bg: #12301f; --neg: #ff6b5e; --warn: #f0b44a; --warn-bg: #33270f;
    --brand: #fd6c0f; --bar: #000000; --bar-text: #f6eedd; --bar-muted: #9aa2ae;
    color-scheme: dark;
  }
}
* { box-sizing: border-box }
.show-sm { display: none }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.45 var(--font); font-feature-settings: "tnum" 1, "cv11" 1; -webkit-font-smoothing: antialiased }
a { color: var(--accent); text-decoration: none } a:hover { text-decoration: underline }
.wrap { max-width: 1320px; margin: 0 auto; padding: 0 16px }

/* Top bar */
.top { background: var(--bar); border-bottom: 3px solid var(--brand); position: sticky; top: 0; z-index: 5 }
.top .wrap { display: flex; align-items: center; gap: 22px; height: 58px }
.brand { display: flex; align-items: center; gap: 10px; white-space: nowrap; color: var(--bar-text); text-decoration: none }
.brand:hover { text-decoration: none }
.brand img { width: 34px; height: 34px; border-radius: 7px; display: block }
.wordmark { font-family: var(--display); font-size: 19px; letter-spacing: .02em; text-transform: uppercase; color: var(--bar-text); line-height: 1 }
.tabs { display: flex; gap: 2px; height: 100% }
.tabs a { display: flex; align-items: center; padding: 0 12px; color: var(--bar-muted); font-weight: 600; font-size: 13px; letter-spacing: .04em;
  text-transform: uppercase; border-bottom: 3px solid transparent; margin-bottom: -3px; text-decoration: none }
.tabs a[hidden] { display: none }
.tabs a:hover { color: var(--bar-text); text-decoration: none }
.tabs a[aria-current="page"] { color: var(--bar-text); border-bottom-color: var(--brand) }
.status { margin-left: auto; display: flex; align-items: center; gap: 12px; color: var(--bar-muted); font-size: 13px; min-width: 0 }
.status a { color: var(--bar-text) }
#upd-btn { background: transparent; color: var(--bar-text); border-color: rgba(251,246,234,.35) } #upd-btn:hover { background: rgba(251,246,234,.1) }
.status span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
button { font: inherit; font-weight: 600; font-size: 13px; color: var(--text); background: var(--surface); border: 1px solid var(--line-strong);
  border-radius: 6px; padding: 6px 12px; cursor: pointer } button:hover { background: var(--sunken) } button:disabled { opacity: .5; cursor: progress }

/* Page head */
.head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px; padding: 24px 0 16px }
h1 { font-family: var(--display); font-weight: 400; font-size: 26px; letter-spacing: .01em; margin: 0; line-height: 1.15 }
.sub { color: var(--muted); margin-top: 2px }
.days { display: flex; gap: 4px; flex-wrap: wrap }
.days a, .pagebtn { padding: 5px 12px; border-radius: 6px; color: var(--text); font-weight: 600; font-size: 13px; text-decoration: none;
  border: 1px solid var(--line-strong); background: var(--surface); white-space: nowrap }
.days a:hover, .pagebtn:hover { background: var(--sunken); text-decoration: none }
.days a[aria-current="page"] { color: var(--surface); border-color: var(--text); background: var(--text) }
.notice { border: 1px solid var(--line); background: var(--warn-bg); color: var(--warn); border-radius: 8px; padding: 10px 12px; margin-bottom: 16px; font-size: 13px }

/* KPI strip */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); border: 1px solid var(--line); border-top: 3px solid var(--text); border-radius: 10px; background: var(--surface); margin-bottom: 24px; overflow: hidden; box-shadow: 0 1px 2px rgba(10,44,73,.06) }
.kpi { padding: 12px 16px; border-right: 1px solid var(--line) } .kpi:last-child { border-right: 0 }
.kpi .k { color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em } .kpi .v { font-size: 21px; font-weight: 800; margin-top: 3px; letter-spacing: -.01em }
.kpi .v small { font-size: 12px; color: var(--muted); font-weight: 500; margin-left: 4px }

/* Panels and tables */
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; margin-bottom: 24px; overflow: hidden; box-shadow: 0 1px 2px rgba(10,44,73,.06) }
.panel-h { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 16px; border-bottom: 1px solid var(--line) }
.panel-h h2 { font-size: 13px; font-weight: 800; margin: 0; text-transform: uppercase; letter-spacing: .07em; display: flex; align-items: center; gap: 8px }
.panel-h h2::before { content: ""; width: 4px; height: 14px; background: var(--brand); border-radius: 2px } .panel-h .note { color: var(--muted); font-size: 12px }
.scroll { overflow-x: auto }
table { width: 100%; border-collapse: collapse; font-size: 13px }
th { text-align: left; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; border-bottom: 1px solid var(--line); background: var(--sunken); white-space: nowrap }
td { padding: 9px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; vertical-align: middle }
tbody tr:last-child td { border-bottom: 0 }
.r { text-align: right } .c { text-align: center } .m { color: var(--muted) } .f { color: var(--faint) }
.pos { color: var(--pos) } .neg { color: var(--neg) } .b { font-weight: 600 }
.empty { padding: 28px 16px; color: var(--muted); text-align: center }
.betlink { font-weight: 600; font-size: 12px; border: 1px solid var(--line-strong); border-radius: 6px; padding: 4px 10px; color: var(--text); display: inline-block }
.betlink:hover { background: var(--sunken); text-decoration: none }
.tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--line-strong); color: var(--muted) }
.tag.bet { color: #fff; border-color: var(--brand); background: var(--brand) }

/* Segmented control */
.seg { display: inline-flex; border: 1px solid var(--line-strong); border-radius: 6px; overflow: hidden }
.seg button { border: 0; border-radius: 0; padding: 5px 12px; color: var(--muted); font-weight: 500; background: transparent }
.seg button + button { border-left: 1px solid var(--line-strong) }
.seg button[aria-pressed="true"] { background: var(--text); color: var(--surface) }
.ctrls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center }
label.chk { display: inline-flex; gap: 6px; align-items: center; color: var(--muted); font-size: 13px; cursor: pointer }

/* Odds board: two rows per game (away, home) */
.board td { padding-top: 6px; padding-bottom: 6px }
.board tbody.g tr:first-child td { padding-top: 10px } .board tbody.g tr:last-child td { padding-bottom: 10px; border-bottom: 1px solid var(--line) }
.board tbody.g tr:first-child td { border-bottom: 0 }
.board tbody.g:last-child tr:last-child td { border-bottom: 0 }
.board .team { font-weight: 500 }
.inj { color: var(--warn); font-size: 11px; font-weight: 500; white-space: normal; max-width: 340px; margin-top: 1px } .board .tm { width: 72px; color: var(--muted); font-size: 12px }
.board .pts { color: var(--muted); width: 40px }
.odd { display: inline-flex; flex-direction: column; align-items: flex-end; min-width: 56px; padding: 3px 6px; border-radius: 6px; line-height: 1.25; color: var(--text); text-decoration: none }
.odd small { color: var(--faint); font-size: 11px }
a.odd:hover { background: var(--sunken); text-decoration: none }
.odd.best { background: var(--pos-bg); color: var(--pos) } .odd.best small { color: var(--pos) }
.na { color: var(--faint) }
.board th.bk, .board td.bk { text-align: right; width: 84px; padding-left: 6px; padding-right: 6px }
.board td.edge { white-space: normal; min-width: 110px; max-width: 170px } .tag { white-space: normal }
.bestc { display: none; text-align: right } .tm-sm { display: none; color: var(--faint); font-size: 11px }
@media (max-width: 1100px) { .bk-minor, .hide-md { display: none } .board .bestc { display: table-cell } }
.bestc small { display: block; color: var(--faint); font-size: 11px }
.board tbody.g.has-bet { background: linear-gradient(90deg, var(--brand) 0 3px, transparent 3px) }

details.panel > summary { list-style: none; cursor: pointer; padding: 12px 16px; font-weight: 600; font-size: 15px; display: flex; justify-content: space-between }
details.panel > summary::after { content: "Show"; color: var(--accent); font-size: 13px; font-weight: 500 }
details.panel[open] > summary::after { content: "Hide" }
details.panel[open] > summary { border-bottom: 1px solid var(--line) }
footer { color: var(--muted); font-size: 12px; padding: 8px 0 40px; max-width: 80ch }
.follow { display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; font-weight: 700; color: var(--text) }
.follow img { width: 22px; height: 22px; border-radius: 5px }
.tl img { width: auto; vertical-align: -3px; margin-right: 5px; object-fit: contain }
.pick .tl img { vertical-align: -5px; margin-right: 6px }
.hero { display: block; height: 120px; width: auto; max-width: 100%; object-fit: contain; border-radius: 10px; margin-top: 18px; border: 1px solid var(--line) }
@media (max-width: 720px) { .hero { height: auto; width: 100% } }

@media (max-width: 860px) {
  .top .wrap { gap: 10px } .status span { display: none }
  .wordmark { display: none } .tabs a { padding: 0 8px; font-size: 12px }
  h1 { font-size: 21px }
  .kpi { border-right: 0; border-bottom: 1px solid var(--line) } .kpi:last-child { border-bottom: 0 }
  .hide-sm { display: none } .show-sm { display: inline }
  td, th { padding-left: 10px; padding-right: 10px }
  #t-plays td:first-child, #t-leans td:first-child { white-space: normal; min-width: 150px }
  .board .bk, .board .pts { display: none } .bestc { display: table-cell }
  .board .tm { width: 52px; font-size: 11px } .board td.edge { min-width: 0; max-width: 104px }
  .board td, .board th { padding-left: 6px; padding-right: 6px } .board .team { white-space: normal; min-width: 0 }
  .board .tag { font-size: 10px; padding: 1px 4px } .board .tl img { width: 14px; height: 14px; margin-right: 4px }
  .board .tm { display: none } .tm-sm { display: block } .board td.edge { max-width: 104px }
  table.stack thead { display: none }
  table.stack tbody tr { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 12px; padding: 12px; border-bottom: 1px solid var(--line) }
  table.stack tbody tr:last-child { border-bottom: 0 }
  table.stack td { display: block; border: 0; padding: 0; white-space: normal; text-align: left; min-width: 0 }
  table.stack td:first-child { grid-column: 1 / -1; min-width: 0 }
  table.stack td[data-l]::before { content: attr(data-l); display: block; font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: var(--faint); margin-bottom: 1px }
  table.stack td:first-child::before { display: none }
  table.stack td.hide-sm, table.stack td:empty { display: none }
  table.stack td.empty { grid-column: 1 / -1; text-align: center }
}
</style>

<header class="top"><div class="wrap">
  __BRAND__
  <nav class="tabs" aria-label="Sport"><a href="https://barrca12-rgb.github.io/NFL/">NFL</a><a href="./" aria-current="page">NBA</a><a href="https://barrca12-rgb.github.io/CBB/"><span class="hide-sm">College Basketball</span><span class="show-sm">CBB</span></a></nav>
  <div class="status"><span id="upd-status"></span><button id="upd-btn" type="button">Update</button></div>
</div></header>

<main class="wrap">
  <div class="head">
    <div><h1 id="h1"></h1><div class="sub" id="sub"></div></div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><nav class="days" id="days" aria-label="Days"></nav><a class="pagebtn" href="record.html">Record</a></div>
  </div>

  <div class="notice" id="early" hidden>Early lines: books posted these numbers and have taken them down until closer to the game. Edges are shown so you can see what's coming; nothing is logged as a play until a book reopens the line.</div>
  <div class="notice" id="stale" hidden>Live lines unavailable on the last update (SportsGameOdds). Lines shown are the last ones stored; no new plays were logged.</div>

  <div class="kpis" id="kpis"></div>

  <section class="panel" aria-labelledby="plays-h">
    <div class="panel-h"><h2 id="plays-h">Plays</h2><span class="note">Totals only: edge 4+ pts vs the best number, price −130 or better, 1 unit each, at most 3 overs and 3 unders a day (largest edges first; the rest show as Capped on the board), and the edge must still be 3+ after removing the league-wide gap between the model and openers (shown in the KPI strip). Win % = backtest rate at that edge vs openers. A play is logged at the number it first appears.</span></div>
    <div class="scroll"><table id="t-plays"></table></div>
  </section>

  <section class="panel" aria-labelledby="board-h">
    <div class="panel-h"><h2 id="board-h">Odds board</h2>
      <div class="ctrls">
        <div class="seg" role="group" aria-label="Market"><button data-m="spread">Spread</button><button data-m="total" aria-pressed="true">Total</button><button data-m="ml">Moneyline</button></div>
        <label class="chk"><input type="checkbox" id="only-plays"> Plays only</label>
      </div>
    </div>
    <div class="scroll"><table class="board" id="t-board"></table></div>
  </section>

  <section class="panel" aria-labelledby="news-h" id="news-sec" hidden>
    <div class="panel-h"><h2 id="news-h">Injury news</h2><span class="note">ESPN injury report, refreshed every update. Listed players who played in their team's last game: the projection still counts them. "If out" = what the model's own weights say his absence does.</span></div>
    <div class="scroll"><table id="t-news"></table></div>
  </section>

  <section class="panel" aria-labelledby="watch-h" id="watch-sec">
    <div class="panel-h"><h2 id="watch-h">Watch list</h2><span class="note">Total becomes a play if the line reaches the number shown (edge 4+ and 3+ after the league-wide gap).</span></div>
    <div class="scroll"><table id="t-watch"></table></div>
  </section>

  <section class="panel" aria-labelledby="rec-h" id="rec-sec" hidden>
    <div class="panel-h"><h2 id="rec-h">Record</h2><span class="note">Forward test from Oct 27, 2026. Every play graded at the number it first appeared. CLV = points better than the closing line.</span></div>
    <div class="scroll"><table id="t-rec"></table></div>
  </section>

  <details class="panel" id="recent-sec" hidden><summary>Recent results</summary><div class="scroll"><table id="t-recent"></table></div></details>
  <details class="panel" id="leans-sec"><summary>Spread leans (tracked, not bet)</summary><div class="scroll"><table id="t-leans"></table></div></details>
  <details class="panel"><summary>Power ratings</summary><div class="scroll"><table id="t-rat"></table></div></details>

  <footer>
    <div><a class="follow" href="https://x.com/__X__" target="_blank" rel="noopener"><img src="assets/otg-logo-512.png" alt="">Follow @__X__ on X for every play</a></div>
  </footer>
</main>

<script id="data" type="application/json">__DATA__</script>
<script>
(() => {
  const D = JSON.parse(document.getElementById("data").textContent);
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const sgn = (x, d = 1) => x == null ? "–" : (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(d).replace(/\.0+$/, "");
  const ln = (x) => x == null ? "–" : Math.abs(x) < 0.05 ? "PK" : sgn(x);
  const num = (x, d = 1) => x == null ? "–" : Number(x).toFixed(d).replace(/\.0$/, "");
  const odds = (x) => x == null ? "" : (x > 0 ? "+" : "−") + Math.abs(Math.round(x));
  const pct = (x) => x == null ? "–" : (100 * x).toFixed(1) + "%";
  const playAt = (v, higherBetter) => v == null ? null : (higherBetter ? Math.ceil(v * 2 - 1e-9) : Math.floor(v * 2 + 1e-9)) / 2;
  const day = new Date(D.date + "T12:00:00");
  const tip = (g) => g.start ? new Date(g.start).toLocaleTimeString("en-US", {hour: "numeric", minute: "2-digit", timeZone: "America/New_York"}) : "";
  const stack = (id) => { const t = $(id); if (!t) return; const hs = [...t.querySelectorAll("thead th")].map((h) => h.textContent.trim());
    t.classList.add("stack"); t.querySelectorAll("tbody tr").forEach((r) => [...r.children].forEach((c, k) => { if (hs[k]) c.dataset.l = hs[k]; })); };
  // ESPN logos by team abbreviation; a logo that fails to load is removed
  const logo = (ab, px) => !ab ? "" : "<picture class='tl'><source media='(prefers-color-scheme: dark)' srcset='https://a.espncdn.com/i/teamlogos/nba/500-dark/" +
    esc(String(ab).toLowerCase()) + ".png'><img src='https://a.espncdn.com/i/teamlogos/nba/500/" + esc(String(ab).toLowerCase()) + ".png' alt='' loading='lazy' width='" + px +
    "' height='" + px + "' onerror=\"this.closest('picture').remove()\"></picture>";
  const matchupL = (g) => logo(g.away, 14) + esc(g.away) + (g.neutral ? " vs " : " @ ") + logo(g.home, 14) + esc(g.home);
  const BOOKS = ["FanDuel", "DraftKings", "BetMGM", "Caesars", "Fanatics", "bet365", "theScore Bet"];
  const bl = (g, bk) => (g.book_lines || []).find((x) => x.book === bk);

  $("h1").textContent = day.toLocaleDateString("en-US", {weekday: "long", month: "long", day: "numeric"});
  const withLines = D.games.filter((g) => g.n_books > 0).length;
  $("sub").textContent = D.games.length + " games · " + withLines + " with lines · " + (D.season - 1) + "–" + String(D.season).slice(2) + " season";

  const navDays = (list) => {
    $("days").innerHTML = list.slice(-7).map((d) => '<a href="nba_' + d + '.html"' + (d === D.date ? ' aria-current="page"' : "") + ">" +
      new Date(d + "T12:00:00").toLocaleDateString("en-US", {weekday: "short", month: "short", day: "numeric"}) + "</a>").join("");
  };
  navDays([D.date]);
  $("stale").hidden = !(D.usage && D.usage.error);
  $("early").hidden = !D.games.some((g) => g.early);
  fetch("days.json", {cache: "no-store"}).then((r) => r.json()).then((j) => navDays(j.days)).catch(() => {});

  // Plays (totals) and leans (spreads)
  const P = D.games.filter((g) => g.total_verdict === "BET").map((g) => ({g, bet: g.total_pick + " " + num(g.total_line), price: g.total_odds, book: g.total_book,
    link: g.total_link, edge: g.total_edge, p: g.total_p, ev: g.total_ev, model: num(g.model_total), to: num(playAt(g.total_good_to, g.total_pick === "Under")),
    open: g.open_total == null ? null : num(g.open_total), units: g.total_units}));
  P.sort((a, b) => String(a.g.start).localeCompare(String(b.g.start)) || b.edge - a.edge);
  // other books' totals for the play's side, best first (same "Also:" line as the CBB card)
  const also = (g) => { const ou = String(g.total_pick || "").toLowerCase(); const pay = (o) => o == null ? -1 : (o > 0 ? o / 100 : 100 / -o);
    const L = (g.book_lines || []).filter((x) => x.total != null && x.book !== g.total_book).map((x) => ({book: x.book, key: ou === "over" ? -x.total : x.total, total: x.total, price: x[ou + "_odds"]}))
      .sort((p, q) => q.key - p.key || pay(q.price) - pay(p.price));
    return L.length ? "Also: " + L.map((x) => x.book + " " + ou[0] + num(x.total) + (x.price != null ? " (" + odds(x.price) + ")" : "")).join(" · ") : ""; };
  const rest = (g) => "Rest " + (g.away_rest == null ? "–" : Math.min(g.away_rest, 7) + "d") + " / " + (g.home_rest == null ? "–" : Math.min(g.home_rest, 7) + "d");
  const missing = (g) => ["away", "home"].map((sd) => { const u = g[sd + "_usual_net"], a = g[sd + "_avail_net"];
    return u != null && a != null && u - a > 1 ? g[sd] + " short-handed in last game (" + sgn(a - u) + " ARC)" : ""; }).filter(Boolean).join(" · ");
  $("t-plays").innerHTML = P.length ? "<thead><tr><th>Bet</th><th>Book</th><th class='r hide-sm hide-md'>Model</th><th class='r'>Edge</th><th class='r hide-sm'>Win %</th><th class='r'>EV</th><th class='r'>Bet to</th><th class='r hide-sm hide-md'>Opened</th><th class='r hide-sm hide-md'>Units</th></tr></thead><tbody>" +
    P.map((p) => "<tr><td><div class='b pick'>" + esc(p.bet) + (p.g.early ? " <span class='tag'>Early line</span>" : "") + "</div><div class='f' style='font-size:12px'>" + matchupL(p.g) + " · " + esc(tip(p.g)) + " · Total · " + esc(rest(p.g)) + "</div>" +
      (also(p.g) ? "<div class='f' style='font-size:12px'>" + esc(also(p.g)) + "</div>" : "") +
      (missing(p.g) ? "<div class='inj'>" + esc(missing(p.g)) + "</div>" : "") +
      (p.g.total_warn ? "<div class='inj'>&#9888; " + esc(p.g.total_warn) + "</div>" : "") +
      (p.g.news ? "<div class='inj'>&#9888; " + esc(p.g.news) + "</div>" : "") + "</td><td>" +
      esc(p.book || "–") + (p.price != null ? " <span class='m'>" + esc(odds(p.price)) + "</span>" : "") + "</td><td class='r m hide-sm hide-md'>" + esc(p.model) + "</td><td class='r pos b'>" + sgn(p.edge) +
      "</td><td class='r m hide-sm'>" + pct(p.p) + "</td><td class='r'>" + (p.ev == null ? "–" : sgn(100 * p.ev) + "%") +
      "</td><td class='r'>" + esc(p.to) + "</td><td class='r m hide-sm hide-md'>" + esc(p.open ?? "–") + "</td><td class='r hide-sm hide-md'>" + num(p.units, 2) + "</td></tr>").join("") + "</tbody>"
    : "<tbody><tr><td class='empty'>" + (withLines ? "No plays. No total is far enough from the model." : "No lines posted yet. Openers usually post the night before.") + "</td></tr></tbody>";

  const Lz = D.games.filter((g) => g.spread_verdict === "LEAN");
  if (!Lz.length) $("leans-sec").hidden = true;
  else $("t-leans").innerHTML = "<thead><tr><th>Lean</th><th>Best number</th><th class='r'>Model</th><th class='r'>Edge</th><th class='r hide-sm'>Opened</th></tr></thead><tbody>" +
    Lz.map((g) => "<tr><td><div class='b pick'>" + logo(g[g.spread_side], 20) + esc(g.spread_pick + " " + ln(g.spread_line)) + "</div><div class='f' style='font-size:12px'>" + matchupL(g) + " · " + esc(tip(g)) + "</div></td><td>" +
      esc(g.spread_book) + (g.spread_odds != null ? " <span class='m'>" + esc(odds(g.spread_odds)) + "</span>" : "") + "</td><td class='r m'>" +
      ln(g.spread_side === "home" ? g.model_home_spread : -g.model_home_spread) + "</td><td class='r b'>" + sgn(g.spread_edge) + "</td><td class='r m hide-sm'>" +
      (g.open_home_spread == null ? "–" : ln(g.spread_side === "home" ? g.open_home_spread : -g.open_home_spread)) + "</td></tr>").join("") + "</tbody>";

  // KPIs
  const st = D.record ? D.record.status : null;
  const rec = (s) => s && s.bets ? s.w + "–" + s.l + (s.p ? "–" + s.p : "") : "0–0";
  const T = st && st.totals, S = st && st["spread leans"];
  const NP = P.filter((p) => !p.g.early).length;
  const kp = [["Plays today", NP + "<small>" + NP + "u" + (P.length > NP ? " · " + (P.length - NP) + " early" : "") + "</small>"],
    ["Totals", rec(T) + "<small>" + (T && T.win != null ? pct(T.win) : "") + "</small>"],
    ["Spread leans", rec(S) + "<small>" + (S && S.win != null ? pct(S.win) : "") + "</small>"],
    ["Units", "<span class='" + (T && T.units > 0 ? "pos" : T && T.units < 0 ? "neg" : "") + "'>" + sgn(T ? T.units : 0, 2) + "</span>"],
    ["Avg CLV", T && T.clv_pts != null ? sgn(T.clv_pts, 2) + "<small>pts</small>" : "–"],
    ["League gap", (() => { const g = D.games.find((x) => x.market_gap != null); return g ? sgn(g.market_gap) + "<small>model vs openers</small>" : "–"; })()]];
  $("kpis").innerHTML = kp.map(([k, v]) => "<div class='kpi'><div class='k'>" + k + "</div><div class='v'>" + v + "</div></div>").join("");

  // Odds board
  let market = "total";
  const cell = (val, price, link, best) => val == null ? "<span class='na'>–</span>" :
    "<" + (link ? "a href='" + esc(link) + "' target='_blank' rel='noopener'" : "span") + " class='odd" + (best ? " best" : "") + "'>" + esc(val) +
    (price != null ? "<small>" + esc(odds(price)) + "</small>" : "") + "</" + (link ? "a" : "span") + ">";
  // best number (then price) across books for one side, for the phone layout's single column
  const best = (g, sd, i) => {
    const pay = (o) => o == null ? -1 : (o > 0 ? o / 100 : 100 / -o);
    let top = null;
    for (const x of (g.book_lines || [])) {
      let v, pr, txt;
      if (market === "spread") { if (x.home_spread == null) continue; v = sd === "home" ? x.home_spread : -x.home_spread; pr = x[sd + "_spread_odds"]; txt = ln(v); }
      else if (market === "total") { if (x.total == null) continue; const ou = i === 0 ? "over" : "under"; v = ou === "over" ? -x.total : x.total; pr = x[ou + "_odds"]; txt = ou[0] + num(x.total); }
      else { pr = x[sd + "_ml"]; if (pr == null) continue; v = pay(pr); txt = odds(pr); }
      const key = [v, pay(pr)];
      if (!top || key[0] > top.key[0] || (key[0] === top.key[0] && key[1] > top.key[1])) top = {key, txt, pr, book: x.book};
    }
    return top ? esc(top.txt) + (market !== "ml" && top.pr != null ? " <span class='m'>" + esc(odds(top.pr)) + "</span>" : "") + "<small>" + esc(top.book) + "</small>" : "<span class='na'>–</span>";
  };
  const board = () => {
    const only = $("only-plays").checked;
    const G = D.games.filter((g) => !only || g.total_verdict === "BET")
      .sort((a, b) => String(a.start).localeCompare(String(b.start)) || a.home.localeCompare(b.home));
    const mh = {spread: "Model", total: "Model", ml: "Win %"}[market];
    let h = "<thead><tr><th class='tm'>Time</th><th>Team</th><th class='r pts'>Proj</th><th class='r'>" + mh + "</th>" +
      BOOKS.map((b, j) => "<th class='bk" + (j >= 4 ? " bk-minor" : "") + "'>" + b + "</th>").join("") + "<th class='bestc'>Best</th><th class='r edge'>Edge</th></tr></thead>";
    if (!G.length) { $("t-board").innerHTML = h + "<tbody><tr><td class='empty' colspan='" + (BOOKS.length + 6) + "'>No games.</td></tr></tbody>"; return; }
    h += G.map((g) => {
      const hasBet = market === "total" && g.total_verdict === "BET";
      const rows = ["away", "home"].map((sd, i) => {
        const pts = g["model_" + sd + "_pts"] == null ? "–" : Math.round(g["model_" + sd + "_pts"]);
        let model, bookCells, edge = "";
        if (market === "spread") {
          model = ln(sd === "home" ? g.model_home_spread : -g.model_home_spread);
          const pick = g.spread_side === sd && g.spread_verdict === "LEAN";
          bookCells = BOOKS.map((bk) => { const x = bl(g, bk); if (!x || x.home_spread == null) return cell(null);
            const v = sd === "home" ? x.home_spread : -x.home_spread;
            return cell(ln(v), x[sd + "_spread_odds"], x[sd + "_spread_link"], pick && g.spread_book === bk && v === g.spread_line); });
          if (pick) edge = "<span class='tag'>Lean " + sgn(g.spread_edge) + "</span>";
        } else if (market === "total") {
          const ou = i === 0 ? "over" : "under";
          model = i === 0 ? num(g.model_total) : "";
          const pick = (g.total_pick || "").toLowerCase() === ou && ["BET", "WATCH", "CAPPED"].includes(g.total_verdict);
          bookCells = BOOKS.map((bk) => { const x = bl(g, bk); if (!x || x.total == null) return cell(null);
            return cell((i === 0 ? "o" : "u") + num(x.total), x[ou + "_odds"], x[ou + "_link"], pick && g.total_book === bk && x.total === g.total_line); });
          if (pick && g.total_verdict === "BET") edge = g.early ? "<span class='tag'>Early " + sgn(g.total_edge) + "</span>" : "<span class='tag bet'>BET " + sgn(g.total_edge) + "</span>";
          else if (pick && g.total_verdict === "CAPPED") edge = "<span class='tag'>Capped " + sgn(g.total_edge) + "</span>";
          else if (pick) edge = "<span class='tag'>Watch · bet at " + ou[0] + num(playAt(g.total_good_to, ou === "under")) + "</span>";
        } else {
          const p = sd === "home" ? g.p_home_win : 1 - g.p_home_win;
          model = p == null ? "–" : Math.round(100 * p) + "%";
          const prices = BOOKS.map((bk) => (bl(g, bk) || {})[sd + "_ml"]);
          const ok = prices.filter((v) => v != null), top = Math.max(...ok);
          bookCells = BOOKS.map((bk, j) => { const x = bl(g, bk); return x && x[sd + "_ml"] != null ? cell(odds(x[sd + "_ml"]), null, x[sd + "_ml_link"], prices[j] === top && ok.length > 1) : cell(null); });
        }
        return "<tr>" + (i === 0 ? "<td class='tm' rowspan='2'>" + esc(tip(g)) + "</td>" : "") +
          "<td class='team'>" + (i === 0 ? "<div class='tm-sm'>" + esc(tip(g)) + "</div>" : "") + (i === 1 && !g.neutral ? "<span class='f'>@ </span>" : "") +
          logo(g[sd], 18) + esc(g[sd]) + (g[sd + "_injuries"] ? "<div class='inj'>" + esc(g[sd + "_injuries"]) + "</div>" : "") + "</td><td class='r pts'>" + pts + "</td><td class='r b'>" + model + "</td>" +
          bookCells.map((c, j) => "<td class='bk" + (j >= 4 ? " bk-minor" : "") + "'>" + c + "</td>").join("") + "<td class='bestc'>" + best(g, sd, i) + "</td><td class='r edge'>" + edge + "</td></tr>";
      }).join("");
      return "<tbody class='g" + (hasBet ? " has-bet" : "") + "'>" + rows + "</tbody>";
    }).join("");
    $("t-board").innerHTML = h;
  };
  document.querySelectorAll(".seg button").forEach((b) => b.onclick = () => {
    market = b.dataset.m; document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", x === b)); board(); });
  $("only-plays").onchange = board;
  board();

  // Injury news: listed players the model still counts
  const NW = [];
  D.games.forEach((g) => (g.injury_alerts || []).forEach((a) => NW.push({g, a})));
  if (NW.length) {
    $("news-sec").hidden = false;
    $("t-news").innerHTML = "<thead><tr><th>Player</th><th>Status</th><th>Game</th><th class='r hide-sm'>Min</th><th class='r hide-sm'>ARC</th><th class='r'>If out: total</th><th class='r'>If out: margin</th></tr></thead><tbody>" +
      NW.map(({g, a}) => "<tr><td><div class='b'>" + logo(a.team, 16) + esc(a.player) + "</div><div class='f' style='font-size:12px;white-space:normal;max-width:420px'>" + esc(a.comment) + "</div></td><td>" + esc(a.status) +
        "</td><td>" + matchupL(g) + " · " + esc(tip(g)) + (g.total_verdict === "BET" ? " <span class='tag bet'>Play</span>" : "") + "</td><td class='r m hide-sm'>" + num(a.minutes, 0) + "</td><td class='r m hide-sm'>" + sgn(a.arc) +
        "</td><td class='r b'>" + sgn(a.d_total) + "</td><td class='r'>" + esc(g.home) + " " + sgn(a.d_home_margin) + "</td></tr>").join("") + "</tbody>";
  }

  // Watch list
  const W = D.games.filter((g) => g.total_verdict === "WATCH");
  if (!W.length) $("watch-sec").hidden = true;
  else $("t-watch").innerHTML = "<thead><tr><th>Time</th><th>Game</th><th>Side</th><th class='r'>Now</th><th class='r'>Play at</th><th class='r'>Edge now</th></tr></thead><tbody>" +
    W.map((g) => "<tr><td class='m'>" + esc(tip(g)) + "</td><td>" + matchupL(g) + (g.total_gap_note ? "<div class='f' style='font-size:12px;white-space:normal'>" + esc(g.total_gap_note) + "</div>" : "") + "</td><td class='b'>" + esc(g.total_pick) + "</td><td class='r'>" + num(g.total_line) +
      "</td><td class='r'>" + num(playAt(g.total_good_to, g.total_pick === "Under")) + "</td><td class='r m'>" + sgn(g.total_edge) + "</td></tr>").join("") + "</tbody>";

  // Record
  if (st) {
    $("rec-sec").hidden = false;
    $("t-rec").innerHTML = "<thead><tr><th>Market</th><th class='r'>Record</th><th class='r'>Win %</th><th class='r'>Units</th><th class='r'>ROI</th><th class='r'>Avg CLV</th><th class='r'>Beat close</th><th class='r'>Open</th></tr></thead><tbody>" +
      Object.entries(st).map(([mk, s]) => "<tr><td>" + mk[0].toUpperCase() + mk.slice(1) + "</td><td class='r'>" + rec(s) + "</td><td class='r'>" + pct(s.win) + "</td><td class='r " +
        (s.units > 0 ? "pos" : s.units < 0 ? "neg" : "") + "'>" + sgn(s.units, 2) + "</td><td class='r'>" + pct(s.roi) + "</td><td class='r'>" + (s.clv_pts == null ? "–" : sgn(s.clv_pts, 2)) +
        "</td><td class='r'>" + pct(s.beat_close) + "</td><td class='r m'>" + s.open + "</td></tr>").join("") + "</tbody>";
    const R = D.record.recent || [];
    if (R.length) {
      $("recent-sec").hidden = false;
      $("t-recent").innerHTML = "<thead><tr><th>Date</th><th>Game</th><th>Bet</th><th>Book</th><th class='r'>Close</th><th class='r'>CLV</th><th class='r'>Final</th><th class='r'>Result</th><th class='r'>Units</th></tr></thead><tbody>" +
        R.map((x) => "<tr><td class='m'>" + esc(x.date) + "</td><td>" + logo(x.away, 14) + esc(x.away) + " @ " + logo(x.home, 14) + esc(x.home) + "</td><td class='b'>" + esc(x.pick) + (x.kind === "lean" ? " <span class='tag'>Lean</span>" : "") + "</td><td>" + esc(x.book || "–") +
          "</td><td class='r'>" + num(x.close_line) + "</td><td class='r'>" + sgn(x.clv_pts) + "</td><td class='r m'>" + esc(x.away_score) + "–" + esc(x.home_score) +
          "</td><td class='r b " + (x.result === "W" ? "pos" : x.result === "L" ? "neg" : "") + "'>" + esc(x.result) + "</td><td class='r'>" + sgn(x.profit, 2) + "</td></tr>").join("") + "</tbody>";
    }
  }

  ["t-plays", "t-leans", "t-watch", "t-rec", "t-recent"].forEach(stack);

  // Ratings
  $("t-rat").innerHTML = "<thead><tr><th class='r'>#</th><th>Team</th><th class='r'>Net</th><th class='r'>Offense</th><th class='r'>Defense</th><th class='r'>Pace</th></tr></thead><tbody>" +
    D.ratings.map((r) => "<tr><td class='r m'>" + r.rank + "</td><td>" + esc(r.team) + "</td><td class='r b'>" + sgn(r.net) + "</td><td class='r'>" + num(r.adj_oe) +
      "</td><td class='r'>" + num(r.adj_de) + "</td><td class='r'>" + num(r.adj_tempo) + "</td></tr>").join("") + "</tbody>";

  // Update: starts the "Update NBA card" workflow (token for this repo kept only in this browser)
  const REPO = D.repo, WF = "update.yml", API = "https://api.github.com/repos/" + REPO + "/actions";
  const RUNS_URL = "https://github.com/" + REPO + "/actions/workflows/" + WF;
  const store = { get: () => { try { return localStorage.getItem("gh_token_nba") || ""; } catch (e) { return ""; } },
                  set: (v) => { try { v ? localStorage.setItem("gh_token_nba", v) : localStorage.removeItem("gh_token_nba"); } catch (e) {} } };
  const gen = new Date(D.generated_at);
  const ago = (d) => { const m = Math.round((Date.now() - d) / 60000);
    return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.round(m / 60) + " hr ago" : Math.round(m / 1440) + " days ago"; };
  const say = (t) => { $("upd-status").innerHTML = t; };
  say("Updated " + gen.toLocaleString("en-US", {weekday: "short", hour: "numeric", minute: "2-digit"}) + " · " + ago(gen));
  const askKey = () => { const t = prompt("Paste a GitHub fine-grained token for " + REPO + " with Actions: Read and write.\nIt is saved only in this browser. Leave blank to remove it.", store.get());
    if (t !== null) store.set(t.trim()); return store.get(); };
  const gh = (path, opts) => fetch(API + path, Object.assign({ headers: { Accept: "application/vnd.github+json",
    Authorization: "Bearer " + store.get(), "X-GitHub-Api-Version": "2022-11-28" } }, opts || {}));
  const followRun = (since) => {
    const btn = $("upd-btn"); btn.disabled = true; const t0 = Date.now();
    const tick = async () => {
      try {
        const run = (await (await gh("/workflows/" + WF + "/runs?per_page=1")).json()).workflow_runs?.[0];
        const mins = Math.floor((Date.now() - t0) / 60000);
        if (!run || new Date(run.created_at) < since) say("Starting…");
        else if (run.status !== "completed") say("Updating… " + mins + " min · <a href='" + run.html_url + "' target='_blank' rel='noopener'>details</a>");
        else if (run.conclusion === "success") { say("Done. Reloading…"); setTimeout(() => location.replace(location.pathname + "?t=" + Date.now()), 4000); return; }
        else { say("Update failed · <a href='" + run.html_url + "' target='_blank' rel='noopener'>details</a>"); btn.disabled = false; return; }
      } catch (e) { say("Reconnecting…"); }
      setTimeout(tick, 10000);
    };
    tick();
  };
  $("upd-btn").onclick = async () => {
    if (!store.get() && !askKey()) { window.open(RUNS_URL, "_blank", "noopener"); say("No token: use Run workflow on GitHub"); return; }
    const since = new Date(Date.now() - 5000);
    say("Starting…");
    const branch = (await (await fetch("https://api.github.com/repos/" + REPO)).json().catch(() => ({}))).default_branch || "main";
    const r = await gh("/workflows/" + WF + "/dispatches", { method: "POST", body: JSON.stringify({ ref: branch }) }).catch(() => null);
    if (r && r.status === 204) followRun(since);
    else if (r && [401, 403, 404].includes(r.status)) { store.set(""); say("Token refused (" + r.status + "). Click Update to enter a new one."); }
    else say("Couldn't reach GitHub");
  };
  if (store.get()) gh("/workflows/" + WF + "/runs?per_page=1").then((r) => r.json()).then((j) => {
    const run = j.workflow_runs?.[0]; if (run && run.status !== "completed") followRun(new Date(run.created_at)); }).catch(() => {});

})();
</script>
"""
