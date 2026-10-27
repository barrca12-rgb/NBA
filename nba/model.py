"""Walk-forward model: stage 1 ratings per game date (ratings.py), then the stage-2 ridge by season
(barrca12-rgb/CBB cbb/projection.py design). The market line is never an input.

    stage1(cfg, seasons)  -> one row per game: ratings-only margin/total as of the morning of the game
    features(b)           -> rest, back-to-backs, early-season interactions, scoring environment
    walk_forward(b)       -> final_margin / final_total, each season fit only on earlier seasons
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, ratings

BUBBLE = pd.Timestamp("2020-07-30")    # 2020 Orlando restart: no home court; treated as neutral
MARGIN_FEATURES = ["pred_margin", "pred_margin_x_early", "venue", "home_b2b", "away_b2b", "rest_diff"]
TOTAL_FEATURES = ["pred_total", "pred_total_x_early", "season_avg_total", "b2b_sum", "rest_sum"]


def _games(seasons):
    g, t = data.load(seasons)
    bub = g["date"] >= BUBBLE
    bub &= g["season"] == 2020
    g.loc[bub, "neutral"] = True
    t = t.merge(g[["game_id", "neutral"]].rename(columns={"neutral": "nn"}), on="game_id")
    t.loc[t["nn"], "venue"] = 0
    return g, t.drop(columns="nn")


def stage1(cfg: ratings.RatingConfig, first: int, last: int, hook=None) -> pd.DataFrame:
    """Ratings-only predictions for seasons first..last. Season first-1 is loaded only for the prior. hook(g, t)
    may return a modified team_games frame (e.g. an adjusted target column or per-game weights)."""
    g, t = _games(range(first - 1, last + 1))
    if hook is not None:
        t = hook(g, t)
    teams = sorted(data.TEAMS)
    out = []
    prev = t[t["season"] == first - 1]
    final = ratings.fit(prev, prev["date"].max() + pd.Timedelta(days=1), teams, None, cfg,
                        {"ppp": prev["ppp"].mean(), "pace": prev["pace"].mean()})
    for s in range(first, last + 1):
        prior = pd.DataFrame({k: final[k] * cfg.carry for k in ("off", "def", "tempo")})
        league = {"ppp": float(t.loc[t["season"] == s - 1, "ppp"].mean()),
                  "pace": float(t.loc[t["season"] == s - 1, "pace"].mean())}
        ts, gs = t[t["season"] == s], g[g["season"] == s]
        for d, day in gs.groupby("date"):
            r = ratings.fit(ts, d, teams, prior, cfg, league)
            p = ratings.predict(r, day["home_id"], day["away_id"], day["neutral"])
            out.append(day.reset_index(drop=True).join(p).assign(games_before=r["games"]))
        final = ratings.fit(ts, ts["date"].max() + pd.Timedelta(days=1), teams, prior, cfg, league)
    return pd.concat(out, ignore_index=True)


def features(b: pd.DataFrame) -> pd.DataFrame:
    b = b.sort_values(["date", "game_id"]).reset_index(drop=True)
    long = pd.concat([b[["game_id", "season", "date", "home_id"]].rename(columns={"home_id": "team"}),
                      b[["game_id", "season", "date", "away_id"]].rename(columns={"away_id": "team"})])
    long = long.sort_values(["team", "date"])
    long["rest"] = long.groupby(["team", "season"])["date"].diff().dt.days
    long["gp"] = long.groupby(["team", "season"]).cumcount()
    long["rest"] = long["rest"].fillna(7)
    for side in ("home", "away"):
        m = long.rename(columns={"team": f"{side}_id", "rest": f"{side}_rest", "gp": f"{side}_gp"})
        b = b.merge(m[["game_id", f"{side}_id", f"{side}_rest", f"{side}_gp"]], on=["game_id", f"{side}_id"])
    b["venue"] = (~b["neutral"]).astype(float)
    b["home_b2b"] = (b["home_rest"] <= 1).astype(float)
    b["away_b2b"] = (b["away_rest"] <= 1).astype(float)
    b["b2b_sum"] = b["home_b2b"] + b["away_b2b"]
    cap = lambda x: (x - 1).clip(0, 3)        # extra days off beyond a normal one-day gap, capped at 3
    b["rest_diff"] = cap(b["home_rest"]) - cap(b["away_rest"])
    b["rest_sum"] = cap(b["home_rest"]) + cap(b["away_rest"])
    b["early"] = np.clip(1 - (b["home_gp"] + b["away_gp"]) / 2 / 20, 0, 1)
    b["pred_margin_x_early"] = b["pred_margin"] * b["early"]
    b["pred_total_x_early"] = b["pred_total"] * b["early"]
    # scoring environment: this season's average total in games on earlier dates (once 100 games), else last season's
    pts = b["home_pts"] + b["away_pts"]
    day = pd.DataFrame({"season": b["season"], "date": b["date"], "pts": pts}).groupby(["season", "date"])["pts"].agg(["sum", "count"])
    cum = day.groupby(level=0).cumsum() - day
    avg = (cum["sum"] / cum["count"]).where(cum["count"] >= 100)
    b["season_avg_total"] = b.set_index(["season", "date"]).index.map(avg).to_numpy(float)
    prev = pts.groupby(b["season"]).mean().shift()
    b["season_avg_total"] = b["season_avg_total"].fillna(b["season"].map(prev)).fillna(pts.mean())
    b["margin"] = b["home_pts"] - b["away_pts"]
    b["points"] = pts
    return b


def ridge(X, y, lam=1.0):
    X1 = np.column_stack([np.ones(len(X)), X])
    pen = np.full(X1.shape[1], lam)
    pen[0] = 0
    return np.linalg.solve(X1.T @ X1 + np.diag(pen), X1.T @ y)


def ridge_w(X, y, w, lam=1.0):
    X1 = np.column_stack([np.ones(len(X)), X])
    pen = np.full(X1.shape[1], lam)
    pen[0] = 0
    W = w[:, None]
    return np.linalg.solve(X1.T @ (X1 * W) + np.diag(pen), (X1 * W).T @ y)


def walk_forward(b: pd.DataFrame, first_train: int, mf=MARGIN_FEATURES, tf=TOTAL_FEATURES,
                 season_half_life: float | None = None, margin_half_life: float | None = None) -> pd.DataFrame:
    """season_half_life: weight earlier training seasons by 0.5^((s-1-season)/half_life) (CBB d_common)."""
    b = b.copy()
    b["final_margin"], b["final_total"] = np.nan, np.nan
    for s in sorted(b["season"].unique()):
        tr = b[(b["season"] < s) & (b["season"] >= first_train)]
        if not len(tr):
            continue
        te = b["season"] == s
        w = (np.ones(len(tr)) if season_half_life is None
             else 0.5 ** ((s - 1 - tr["season"].to_numpy(float)) / season_half_life))
        wm = w if margin_half_life is None else 0.5 ** ((s - 1 - tr["season"].to_numpy(float)) / margin_half_life)
        cm = ridge_w(tr[mf].to_numpy(float), tr["margin"].to_numpy(float), wm)
        ct = ridge_w(tr[tf].to_numpy(float), tr["points"].to_numpy(float), w)
        b.loc[te, "final_margin"] = cm[0] + b.loc[te, mf].to_numpy(float) @ cm[1:]
        b.loc[te, "final_total"] = ct[0] + b.loc[te, tf].to_numpy(float) @ ct[1:]
    return b
