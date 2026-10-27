"""The Record page (reports/record.html): every NBA play graded at the number it was logged, in the same layout as
the CBB record page (barrca12-rgb/CBB cbb/record_page.py). Totals are the bets; spread leans are tracked, not bet,
and listed separately. Display only: reads bets/plays.csv, changes nothing.

    python -m nba.record_page
"""
from __future__ import annotations

import html
import os

import pandas as pd

from . import record, report_html

OUT = os.path.join(record.ROOT, "reports", "record.html")


def _num(x, fmt="{:+.2f}", empty="–"):
    return empty if x is None or pd.isna(x) else fmt.format(x)


def summary(s: pd.DataFrame) -> dict:
    w, l, p = int((s["result"] == "W").sum()), int((s["result"] == "L").sum()), int((s["result"] == "P").sum())
    units = float(s["profit"].sum()) if len(s) else 0.0
    clv = s["clv_pts"].dropna()
    return {"rec": f"{w}–{l}" + (f"–{p}" if p else ""), "win": w / (w + l) if w + l else None, "units": units,
            "roi": units / len(s) if len(s) else None, "clv": float(clv.mean()) if len(clv) else None, "n": len(s)}


def _row(label: str, s: dict) -> str:
    c = "pos" if s["units"] > 0 else "neg" if s["units"] < 0 else ""
    return (f"<tr><td class='b'>{html.escape(label)}</td><td class='r'>{s['rec']}</td><td class='r'>{_num(s['win'], '{:.1%}')}</td>"
            f"<td class='r {c}'>{_num(s['units'])}</td><td class='r'>{_num(s['roi'], '{:+.1%}')}</td>"
            f"<td class='r'>{_num(s['clv'], '{:+.2f}')}</td></tr>")


HEAD = ("<thead><tr><th>Bets</th><th class='r'>Record</th><th class='r'>Win %</th><th class='r'>Units</th>"
        "<th class='r'>ROI</th><th class='r'>Avg CLV</th></tr></thead>")


def _logo(ab, px: int = 16) -> str:
    """ESPN team logo by abbreviation (light and dark variants); removed by the browser if it fails to load."""
    if not isinstance(ab, str) or not ab:
        return ""
    u = "https://a.espncdn.com/i/teamlogos/nba/{}/" + f"{html.escape(ab.lower())}.png"
    return (f"<picture class='tl'><source media='(prefers-color-scheme: dark)' srcset='{u.format('500-dark')}'>"
            f"<img src='{u.format('500')}' alt='' loading='lazy' width='{px}' height='{px}' onerror=\"this.closest('picture').remove()\"></picture>")


def _plays_table(d: pd.DataFrame, empty: str) -> str:
    rows = []
    for _, r in d.sort_values(["date", "logged_at"], ascending=False).iterrows():
        res = {"W": "<span class='pos b'>Win</span>", "L": "<span class='neg b'>Loss</span>", "P": "Push"}.get(str(r["result"]), "Open")
        units = _num(float(r["profit"])) if pd.notna(r["result"]) else "–"
        side_team = r["home"] if r["side"] == "home" else r["away"] if r["side"] == "away" else None
        rows.append(
            f"<tr><td class='m'>{pd.Timestamp(r['date']):%b %-d}</td><td>{_logo(r['away'])}{html.escape(str(r['away']))} @ "
            f"{_logo(r['home'])}{html.escape(str(r['home']))}</td><td class='b'>{_logo(side_team)}{html.escape(str(r['pick']))}</td>"
            f"<td>{html.escape(str(r['book']))} <span class='m'>{_num(r['odds'], '{:+.0f}')}</span></td>"
            f"<td class='r'>{_num(r['edge'], '{:.1f}')}</td><td class='r'>{_num(r['close_line'], '{:g}')}</td>"
            f"<td class='r'>{_num(r['clv_pts'], '{:+.1f}')}</td><td>{res}</td><td class='r'>{units}</td></tr>")
    if not rows:
        return f"<tbody><tr><td class='empty'>{empty}</td></tr></tbody>"
    return ("<thead><tr><th>Date</th><th>Game</th><th>Play</th><th>Book</th><th class='r'>Edge</th><th class='r'>Close</th>"
            "<th class='r'>CLV</th><th>Result</th><th class='r'>Units</th></tr></thead><tbody>" + "".join(rows) + "</tbody>")


def build() -> str:
    p = record.load()
    tot = p[(p["market"] == "total") & (p["kind"] == "play")]
    lean = p[(p["market"] == "spread") & (p["kind"] == "lean")]
    st, sl = tot[tot["result"].notna()], lean[lean["result"].notna()]
    s = summary(st)
    kp = [("Record", s["rec"]), ("Win %", _num(s["win"], "{:.1%}")), ("Units", _num(s["units"])),
          ("ROI", _num(s["roi"], "{:+.1%}")), ("Avg CLV", _num(s["clv"], "{:+.2f} pts")),
          ("Open plays", str(int(tot["result"].isna().sum())))]
    kpis = "".join(f"<div class='kpi'><div class='k'>{k}</div><div class='v'>{v}</div></div>" for k, v in kp)
    rows = [_row("Totals (bets)", s), _row("Spread leans (tracked, not bet)", summary(sl))]
    months = ""
    if len(st):
        m = st.assign(mo=pd.to_datetime(st["date"]).dt.to_period("M"))
        months = "".join(_row(k.strftime("%b %Y"), summary(g)) for k, g in sorted(m.groupby("mo"), key=lambda x: x[0], reverse=True))
    now = pd.Timestamp.now(tz="America/New_York")
    R = report_html
    style = R.TEMPLATE[R.TEMPLATE.index("<style>"):R.TEMPLATE.index("</style>") + 8]
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Off The Glass · NBA Record</title>
<meta property="og:title" content="Off The Glass · NBA Record">
{R.HEAD}
{style}
<header class="top"><div class="wrap">
  {R.BRAND}
  <nav class="tabs" aria-label="Sport"><a href="https://barrca12-rgb.github.io/NFL/">NFL</a><a href="./" aria-current="page">NBA</a><a href="https://barrca12-rgb.github.io/CBB/"><span class="hide-sm">College Basketball</span><span class="show-sm">CBB</span></a></nav>
</div></header>
<main class="wrap">
  <img class="hero" src="assets/otg-banner.webp" alt="Off The Glass Hoops" width="2000" height="667">
  <div class="head"><div><h1>NBA Record</h1>
    <div class="sub">Every play at the logged number and price, graded against the final score. Updated {now:%b %-d, %-I:%M %p} ET.</div></div><a class="pagebtn" href="./">&larr; Card</a></div>
  <div class="kpis">{kpis}</div>
  <section class="panel"><div class="panel-h"><h2>Summary</h2><span class="note">Settled plays. CLV = points the line moved our way from the logged number to the close. Break-even at -110 is 52.4%.</span></div>
    <div class="scroll"><table>{HEAD}<tbody>{''.join(rows)}</tbody></table></div></section>
  {f"<section class='panel'><div class='panel-h'><h2>By month</h2><span class='note'>Totals.</span></div><div class='scroll'><table>{HEAD}<tbody>{months}</tbody></table></div></section>" if months else ""}
  <section class="panel"><div class="panel-h"><h2>Bets placed</h2><span class="note">Totals, newest first.</span></div>
    <div class="scroll"><table>{_plays_table(tot, "No plays yet.")}</table></div></section>
  <section class="panel"><div class="panel-h"><h2>Spread leans</h2><span class="note">Tracked, not bet: the backtest edge on spreads is too thin to stake yet.</span></div>
    <div class="scroll"><table>{_plays_table(lean, "No leans yet.")}</table></div></section>
  <footer>
    <div><a class="follow" href="https://x.com/{R.X_HANDLE}" target="_blank" rel="noopener"><img src="assets/otg-logo-512.png" alt="">Follow @{R.X_HANDLE} on X for every play</a></div></footer>
</main>
<script>
// phones: each table row becomes a small card, each cell labeled with its column header (styles in report_html)
document.querySelectorAll("main table").forEach((t) => {{
  const hs = [...t.querySelectorAll("thead th")].map((h) => h.textContent.trim());
  t.classList.add("stack");
  t.querySelectorAll("tbody tr").forEach((r) => [...r.children].forEach((c, k) => {{ if (hs[k]) c.dataset.l = hs[k]; }}));
}});
</script>
</html>
"""


def write() -> str:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(build())
    return OUT


if __name__ == "__main__":
    print(write())
