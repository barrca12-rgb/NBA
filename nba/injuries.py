"""Automatic injury and news feed for the card: ESPN's NBA injury report (free, no key), pulled on every run.

The model counts the players who played in each team's last game (players.py). For every listed player this adds:
whether he played that game (so the projection counts him), his recent minutes and LUMA ARC, and what the model's
own coefficients (data/model.json) say his absence would do to the total and the margin. Nothing here changes a
projection or a logged play; it tells you when the news has moved past the model.

Every run saves injuries/latest.csv and appends new or changed entries to injuries/log.csv (first seen time).
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np
import pandas as pd

from . import live, players

URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
DIR = os.path.join(os.path.dirname(__file__), "..", "injuries")
SHORT = {"Out": "OUT", "Doubtful": "D", "Questionable": "Q", "Probable": "P", "Day-To-Day": "DTD"}
RISKY = {"Out", "Doubtful", "Questionable", "Day-To-Day"}   # Day-To-Day here = note gave no status


def _status(status: str, comment: str) -> str:
    """ESPN files most game-time decisions as "Day-To-Day"; the note says which (probable/questionable/...)."""
    c = str(comment).lower()
    if status == "Day-To-Day":
        for word, st in (("ruled out", "Out"), ("won't play", "Out"), ("will not play", "Out"), ("doubtful", "Doubtful"),
                         ("questionable", "Questionable"), ("game-time decision", "Questionable"), ("probable", "Probable"),
                         ("expected to play", "Probable"), ("will play", "Probable"), ("is out", "Out")):
            if word in c:
                return st
    return status


def fetch() -> pd.DataFrame:
    req = urllib.request.Request(URL, headers={"User-Agent": "nba-card"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    rows = []
    for t in d.get("injuries") or []:
        for i in t.get("injuries") or []:
            a = i.get("athlete") or {}
            rows.append({"team": t.get("displayName"), "player": a.get("displayName"),
                         "status": _status(i.get("status"), i.get("shortComment") or ""),
                         "comment": i.get("shortComment") or "", "detail": i.get("longComment") or "",
                         "updated": (i.get("date") or "")[:16]})
    return pd.DataFrame(rows, columns=["team", "player", "status", "comment", "detail", "updated"])


def save(inj: pd.DataFrame) -> None:
    os.makedirs(DIR, exist_ok=True)
    inj.to_csv(os.path.join(DIR, "latest.csv"), index=False)
    path = os.path.join(DIR, "log.csv")
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=list(inj.columns) + ["first_seen"])
    key = lambda d: d["player"].astype(str) + "|" + d["status"].astype(str) + "|" + d["comment"].astype(str)
    new = inj[~key(inj).isin(set(key(old)))].assign(first_seen=pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"))
    if len(new):
        pd.concat([old, new], ignore_index=True).to_csv(path, index=False)


def last_game_roster(season: int) -> pd.DataFrame:
    """Per team: players in its most recent completed game, with expected minutes and ARC (as players.py uses)."""
    b = players.box([season])
    a = players.arc()
    b["arc_season"] = season - 1
    b = b.merge(a.rename(columns={"season": "arc_season"}), on=["arc_season", "key"], how="left")
    b2 = b[["key"]].assign(arc_season=season - 2).merge(a.rename(columns={"season": "arc_season"}), on=["arc_season", "key"], how="left")
    for c in ("net", "O", "D"):
        b[c] = b[c].fillna(pd.Series(b2[c].to_numpy(), index=b.index)).fillna(players.ROOKIE_ARC[c])
    b = b.sort_values("date")
    avg = b[b["minutes"] > 0].groupby("athlete_id")["minutes"].apply(lambda m: m.tail(10).mean())
    last = b.groupby("team_id")["date"].transform("max") == b["date"]
    r = b[last & (b["minutes"] > 0)].copy()
    r["exp_min"] = r["athlete_id"].map(avg)
    return r[["team_id", "athlete_display_name", "key", "minutes", "exp_min", "net", "O", "D"]]


def _without(r: pd.DataFrame, key: str) -> dict:
    """Change in a team's minutes-weighted strength (5 x mean ARC, as players.py) if one player is removed."""
    w = r["exp_min"].fillna(r["minutes"])
    out = {}
    for c in ("net", "O", "D"):
        full = 5 * (w * r[c]).sum() / w.sum()
        k = r["key"] != key
        out[c] = 5 * (w[k] * r.loc[k, c]).sum() / w[k].sum() - full
    return out


def annotate(games: list[dict], names: dict, season: int) -> pd.DataFrame:
    """Add <side>_injuries (short text), injury_alerts (players the model counts who are now listed) to each game."""
    try:
        inj = fetch()
    except Exception as e:
        print(f"injury feed unavailable: {e}")
        return pd.DataFrame()
    save(inj)
    roster = last_game_roster(season)
    coef = live.load_model()
    cm, ct = coef["margin"], coef["total"]
    inj["key"] = inj["player"].map(players.norm)
    by_team = {t: d for t, d in inj.groupby("team")}
    for g in games:
        alerts = []
        for sd in ("home", "away"):
            tid = int(g[f"{sd}_id"]) if g.get(f"{sd}_id") is not None else None
            d = by_team.get(names.get(tid, ""), pd.DataFrame(columns=inj.columns))
            r = roster[roster["team_id"] == tid]
            parts = []
            for _, x in d.iterrows():
                st = SHORT.get(x["status"], x["status"])
                counted = x["key"] in set(r["key"])
                # board text: players the model counts, plus game-time decisions; long-term outs the model already
                # leaves out are skipped (the injury log keeps everything)
                if counted or x["status"] in ("Questionable", "Doubtful"):
                    parts.append(f"{x['player']} {st}" + (" (played last game)" if counted else ""))
                if counted and x["status"] in RISKY:
                    p = r[r["key"] == x["key"]].iloc[0]
                    dl = _without(r, x["key"])
                    early = g.get("early_w", 0) or 0
                    sign = 1 if sd == "home" else -1
                    dm = sign * dl["net"] * (cm.get("avail_diff", 0) + cm.get("avail_diff_x_early", 0) * early - cm.get("miss_diff", 0))
                    dt = dl["O"] * (ct.get("avail_O_sum", 0) - ct.get("miss_O_sum", 0)) + dl["D"] * (ct.get("avail_D_sum", 0) - ct.get("miss_D_sum", 0))
                    alerts.append({"team": g[sd], "player": x["player"], "status": x["status"], "comment": x["comment"],
                                   "minutes": round(float(p["exp_min"] if p["exp_min"] == p["exp_min"] else p["minutes"]), 1),
                                   "arc": round(float(p["net"]), 1), "d_total": round(float(dt), 1),
                                   "d_home_margin": round(float(dm), 1)})
            g[f"{sd}_injuries"] = ", ".join(parts)
        g["injury_alerts"] = alerts
        # one line per alert for the plays table: the model counts him; what his absence would do
        if alerts:
            g["news"] = " · ".join(f"{a['team']}: {a['player']} {a['status'].lower()} — model counts him "
                                   f"({a['minutes']:.0f} min, ARC {a['arc']:+.1f}); if out, total {a['d_total']:+.1f}, "
                                   f"{g['home']} margin {a['d_home_margin']:+.1f}" for a in alerts)
    return inj
