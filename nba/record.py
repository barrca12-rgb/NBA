"""Forward record of the NBA card: every play logged at the number it first appeared, graded against the final
score and the closing line (lines/closing.csv). Totals at 4+ points are the plays; spreads at 3+ are tracked as
leans (the backtest edge on spreads was too thin to bet).

bets/plays.csv: one row per (date, game, market, side), never rewritten except to add the grade.
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
PLAYS = os.path.join(ROOT, "bets", "plays.csv")
COLS = ["bet_id", "date", "game_id", "sgo_event", "start", "home", "away", "market", "kind", "side", "pick", "line",
        "odds", "book", "model", "edge", "win_p", "logged_at", "close_line", "clv_pts", "home_score", "away_score",
        "result", "profit"]
SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"


def load() -> pd.DataFrame:
    return pd.read_csv(PLAYS, dtype={"bet_id": str}) if os.path.exists(PLAYS) else pd.DataFrame(columns=COLS)


def log(new: list[dict]) -> pd.DataFrame:
    """Add plays not logged before (same bet_id keeps its first number)."""
    p = load()
    add = [r for r in new if r["bet_id"] not in set(p["bet_id"])]
    if add:
        p = pd.concat([p, pd.DataFrame(add).reindex(columns=COLS)], ignore_index=True)
        os.makedirs(os.path.dirname(PLAYS), exist_ok=True)
        p.to_csv(PLAYS, index=False)
    return p


def finals(date: str) -> dict:
    """ESPN final scores for an ET date: game_id -> (home_score, away_score)."""
    try:
        req = urllib.request.Request(SCOREBOARD.format(date.replace("-", "")), headers={"User-Agent": "nba-card"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except Exception:
        return {}
    out = {}
    for e in d.get("events") or []:
        if not ((e.get("status") or {}).get("type") or {}).get("completed"):
            continue
        c = e["competitions"][0]["competitors"]
        sc = {x["homeAway"]: float(x["score"]) for x in c}
        out[int(e["id"])] = (sc["home"], sc["away"])
    return out


def grade(closing: pd.DataFrame) -> pd.DataFrame:
    p = load()
    if not len(p):
        return p
    todo = p["result"].isna()
    fin = {}
    for d in sorted(p.loc[todo, "date"].unique()):
        fin.update(finals(d))
    cl = closing.groupby("sgo_event")[["home_spread", "total"]].median() if len(closing) else pd.DataFrame()
    now = pd.Timestamp.now(tz="UTC")
    for i in p.index[todo]:
        r = p.loc[i]
        started = pd.to_datetime(r["start"], utc=True) <= now
        if started and r["sgo_event"] in cl.index:
            c = cl.loc[r["sgo_event"]]
            if r["market"] == "total" and pd.notna(c["total"]):
                p.loc[i, "close_line"] = c["total"]
                p.loc[i, "clv_pts"] = (c["total"] - r["line"]) * (1 if r["side"] == "over" else -1)
            elif r["market"] == "spread" and pd.notna(c["home_spread"]):
                cs = c["home_spread"] if r["side"] == "home" else -c["home_spread"]
                p.loc[i, "close_line"] = cs
                p.loc[i, "clv_pts"] = r["line"] - cs
        g = fin.get(int(r["game_id"]))
        if not g:
            continue
        hs, as_ = g
        p.loc[i, ["home_score", "away_score"]] = [hs, as_]
        if r["market"] == "total":
            x = (hs + as_ - r["line"]) * (1 if r["side"] == "over" else -1)
        else:
            x = ((hs - as_) if r["side"] == "home" else (as_ - hs)) + r["line"]
        res = "W" if x > 0 else "L" if x < 0 else "P"
        o = r["odds"] if pd.notna(r["odds"]) else -110
        win = o / 100 if o > 0 else 100 / -o
        p.loc[i, "result"] = res
        p.loc[i, "profit"] = round(win if res == "W" else -1.0 if res == "L" else 0.0, 3)
    p.to_csv(PLAYS, index=False)
    return p


def status(p: pd.DataFrame) -> dict:
    out = {}
    for name, sel in (("totals", (p["market"] == "total") & (p["kind"] == "play")),
                      ("spread leans", (p["market"] == "spread") & (p["kind"] == "lean"))):
        d = p[sel]
        g = d[d["result"].notna()]
        w, l, pu = (g["result"] == "W").sum(), (g["result"] == "L").sum(), (g["result"] == "P").sum()
        units = float(g["profit"].sum()) if len(g) else 0.0
        clv = d["clv_pts"].dropna()
        out[name] = {"bets": int(len(g)), "w": int(w), "l": int(l), "p": int(pu),
                     "win": w / (w + l) if w + l else None, "units": units,
                     "roi": units / len(g) if len(g) else None,
                     "clv_pts": float(clv.mean()) if len(clv) else None,
                     "beat_close": float((clv > 0).mean()) if len(clv) else None,
                     "open": int(d["result"].isna().sum())}
    recent = p[p["result"].notna()].sort_values("start", ascending=False).head(40)
    return {"status": out, "recent": recent.replace({np.nan: None}).to_dict("records")}
