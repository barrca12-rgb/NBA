"""Live projections for one day's slate with the frozen model (data/model.json, nba/fit.py).

Every input is what the backtest used, computed as of the morning of the game: stage 1 ratings from this season's
games before today, LUMA ARC player strength of who played in each team's previous game, rest, travel, schedule
and scoring environment. The market line is never an input.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from . import data, fit, model, players, ratings


def load_model() -> dict:
    with open(fit.SAVED) as f:
        return json.load(f)


def slate(day: pd.Timestamp, season: int) -> pd.DataFrame:
    """Games scheduled on `day` (ET date) from the hoopR schedule (refreshed)."""
    sch = data.fetch("schedule", season, refresh=True)
    sch = sch.drop_duplicates("game_id")
    d = sch[pd.to_datetime(sch["game_date"]) == day]
    d = d[d["home_id"].astype(int).isin(data.TEAMS) & d["away_id"].astype(int).isin(data.TEAMS)]
    return pd.DataFrame({
        "game_id": d["game_id"].astype(int), "season": season, "season_type": d["season_type"].astype(int),
        "date": pd.to_datetime(d["game_date"]), "start": pd.to_datetime(d["game_date_time"], utc=True),
        "home_id": d["home_id"].astype(int), "away_id": d["away_id"].astype(int),
        "home": d["home_abbreviation"], "away": d["away_abbreviation"],
        "home_name": d["home_display_name"], "away_name": d["away_display_name"],
        "neutral": d["neutral_site"].fillna(False).astype(bool),
        "home_pts": np.nan, "away_pts": np.nan, "periods": np.nan, "pace": np.nan}).reset_index(drop=True)


GAP_GAMES, GAP_MIN = 60, 20
OPENERS = os.path.join(os.path.dirname(__file__), "..", "lines", "espn_open_{}.csv")


def espn_openers(game_ids, season: int) -> pd.Series:
    """ESPN's stored opening total per completed game (free feed; median across real books), cached in
    lines/espn_open_<season>.csv so each game is fetched once."""
    from . import lines
    path = OPENERS.format(season)
    have = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["game_id", "open_total"])
    todo = [int(g) for g in game_ids if int(g) not in set(have["game_id"].astype(int))]
    if todo:
        rows = []
        for gid in todo:
            l = pd.DataFrame(lines.game_lines(gid))
            l = l[~l["book"].fillna("").isin(lines.NOT_BOOKS | {"", "fetch failed"})] if len(l) else l
            v = l["open_total"].median() if len(l) and "open_total" in l else float("nan")
            rows.append({"game_id": gid, "open_total": v})
        have = pd.concat([have, pd.DataFrame(rows)], ignore_index=True)
        have.to_csv(path, index=False)
    return have.set_index(have["game_id"].astype(int))["open_total"]


def market_gap(done: pd.DataFrame, season: int) -> float:
    """Median of (model total - opening total) over the league's last GAP_GAMES completed games with an opener
    (0 until GAP_MIN). The part of every total edge that is a disagreement about the whole league's scoring level,
    not about the game (Oct 28, 2026 rule, research/LOG.md entry 19)."""
    done = done.sort_values(["date", "game_id"]).tail(GAP_GAMES * 2)
    op = espn_openers(done["game_id"], season)
    d = done.assign(open_total=done["game_id"].map(op)).dropna(subset=["open_total", "final_total"]).tail(GAP_GAMES)
    return float((d["final_total"] - d["open_total"]).median()) if len(d) >= GAP_MIN else 0.0


def upcoming(today: pd.Timestamp, day: pd.Timestamp, season: int) -> pd.DataFrame:
    """Every unplayed game from today through `day`: the days ahead count for rest, back-to-backs and games played
    when projecting a later day (their scores stay empty, so nothing is learned from them)."""
    parts = [slate(d, season) for d in pd.date_range(today, day)]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else slate(day, season)


def team_ratings(cfg: ratings.RatingConfig, season: int, day: pd.Timestamp) -> pd.DataFrame:
    """Stage 1 ratings as of `day` (prior chained from two seasons back), for the power ratings table."""
    _, t = model._games(range(season - 2, season + 1))
    teams = sorted(data.TEAMS)
    prior = None
    for s in (season - 2, season - 1, season):
        ts = t[t["season"] == s]
        prev = t[t["season"] == s - 1] if s > season - 2 else ts
        league = {"ppp": float(prev["ppp"].mean()), "pace": float(prev["pace"].mean())}
        asof = day if s == season else ts["date"].max() + pd.Timedelta(days=1)
        r = ratings.fit(ts, asof, teams, prior, cfg, league)
        prior = pd.DataFrame({k: r[k] * cfg.carry for k in ("off", "def", "tempo")})
    out = pd.DataFrame({"off": r["off"], "def": r["def"], "tempo": r["tempo"]})
    out["net"] = out["off"] + out["def"]
    out["adj_oe"], out["adj_de"], out["adj_tempo"] = r["b0"] + out["off"], r["b0"] - out["def"], r["p0"] + out["tempo"]
    return out.sort_values("net", ascending=False)


def project(day, season: int, today=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(slate with model_margin / model_total / model_home_pts / model_away_pts, power ratings)."""
    from research import p2, p3
    day = pd.Timestamp(day)
    m = load_model()
    spec = m["spec"]
    cfg = ratings.RatingConfig(**spec["cfg"])
    sl = slate(day, season)
    if not len(sl):
        return sl, team_ratings(cfg, season, day)
    data.fetch("team_box", season, refresh=True)
    today = pd.Timestamp(today) if today is not None else day
    ext = upcoming(min(today, day), day, season) if day > today else sl
    done = set(data.season_games(season)[0]["game_id"])
    ext = ext[~ext["game_id"].isin(done)]
    b = model.features(model.stage1(cfg, season - 2, season, extra=ext.drop(columns=["home_name", "away_name"])))
    hist_games = b[b["season"] >= season - 1]
    st = players.strength([season - 1, season], hist_games, slate=ext, refresh={season})
    b = p3.add_phase3(p2.add_schedule(p2.add_players(b, st)))
    hca = {int(k): v for k, v in m["team_hca"].items()}
    b["team_hca"] = b["home_id"].map(hca).fillna(0) * b["venue"]
    for mk, col in (("margin", "final_margin"), ("total", "final_total")):
        c = m[mk]
        b[col] = c["intercept"] + sum(b[k].astype(float) * v for k, v in c.items() if k != "intercept")
    cur = b[b["season"] == season].copy()
    if spec.get("bias_k"):
        cur = p3.bias_correct(cur, spec["bias_k"])
    project.gap = market_gap(cur[cur["home_pts"].notna() & (cur["date"] < day)], season)
    out = sl.merge(cur[["game_id", "final_margin", "final_total", "home_rest", "away_rest", "home_avail_net",
                        "away_avail_net", "home_usual_net", "away_usual_net", "early"]].rename(columns={"early": "early_w"}),
                   on="game_id", how="left")
    out["model_margin"], out["model_total"] = out["final_margin"], out["final_total"]
    out["model_home_pts"] = (out["model_total"] + out["model_margin"]) / 2
    out["model_away_pts"] = (out["model_total"] - out["model_margin"]) / 2
    out["model_home_spread"] = -out["model_margin"]
    # win chance from the margin: NBA results scatter about 12.5 points around the line
    from math import erf, sqrt
    out["p_home_win"] = [0.5 * (1 + erf(x / (12.5 * sqrt(2)))) for x in out["model_margin"]]
    return out, team_ratings(cfg, season, day)


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")
    s, r = project(d, 2027)
    print(s[["start", "away", "home", "model_away_pts", "model_home_pts", "model_margin", "model_total",
             "home_avail_net", "away_avail_net"]].round(1).to_string())
    print(r.head(10).round(1).to_string())
