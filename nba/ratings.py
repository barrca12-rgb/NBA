"""Stage 1: opponent- and venue-adjusted efficiency and pace ratings, time-decayed ridge (barrca12-rgb/CBB
cbb/ratings.py, without the Four Factors). Per team-game:

    points per 100 possessions = b0 + hca * venue + off[team] - def[opp]       (venue: +1 home, -1 away, 0 neutral)
    pace (possessions per 48)  = p0 + tempo[team] + tempo[opp]

A game's weight halves every `half_life` days; the ridge shrinks toward a preseason prior (last season's final
ratings times `carry`), so on opening night a team starts where the prior says and moves as games come in.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RatingConfig:
    half_life: float = 60.0
    prior_games: float = 10.0       # strength of the preseason prior on off/def, in games
    pace_prior_games: float = 10.0
    carry: float = 0.6              # share of last season's final rating kept in the prior
    hca_prior: float = 1.5          # home edge per side, points per 100 possessions (~3 pts/game margin)
    pace_half_life: float | None = None   # separate decay for pace (default: half_life)
    ppp_col: str = "ppp"            # "ppp_luck" regresses 3-point luck


def _solve(X, y, w, lam, beta0):
    XtW = X.T * w
    return np.linalg.solve(XtW @ X + np.diag(lam), XtW @ y + lam * beta0)


def fit(tg: pd.DataFrame, asof, teams: list[int], prior: pd.DataFrame | None, cfg: RatingConfig,
        league: dict) -> dict:
    """Ratings from team-games strictly before `asof`. prior: index team id, columns off/def/tempo (deviations).
    league: {"ppp", "pace"} baseline used before the season has games."""
    asof = pd.Timestamp(asof)
    h = tg[tg["date"] < asof]
    k = len(teams)
    idx = pd.Series(np.arange(k), index=teams)
    pr = (prior if prior is not None else pd.DataFrame(index=teams)).reindex(teams)
    pr = pr.reindex(columns=["off", "def", "tempo"]).fillna(0.0)
    n = len(h)
    beta0 = np.concatenate([[league["ppp"], cfg.hca_prior], pr["off"], pr["def"]])
    p0 = np.concatenate([[league["pace"]], pr["tempo"]])
    if not n:
        b, bp = beta0, p0
    else:
        ti, oi = idx[h["team_id"]].to_numpy(), idx[h["opp_id"]].to_numpy()
        w = 0.5 ** ((asof - h["date"]).dt.days.to_numpy() / cfg.half_life)
        if "wt_mult" in h:            # optional per-game weight (e.g. blowouts down-weighted)
            w = w * h["wt_mult"].to_numpy(float)
        wbar = w.mean()
        rows = np.arange(n)
        X = np.zeros((n, 2 + 2 * k))
        X[:, 0] = 1.0
        X[:, 1] = h["venue"].to_numpy()
        X[rows, 2 + ti] = 1.0
        X[rows, 2 + k + oi] = -1.0
        y = h[cfg.ppp_col].to_numpy(float)
        lam = np.full(2 + 2 * k, cfg.prior_games * wbar)
        lam[0] = 1e-6
        lam[1] = 20 * wbar
        beta0[0] = y.mean()
        b = _solve(X, y, w, lam, beta0)
        P = np.zeros((n, 1 + k))
        P[:, 0] = 1.0
        P[rows, 1 + ti] += 1.0
        P[rows, 1 + oi] += 1.0
        if cfg.pace_half_life:
            w = 0.5 ** ((asof - h["date"]).dt.days.to_numpy() / cfg.pace_half_life)
            wbar = w.mean()
        yp = h["pace"].to_numpy(float)
        lamp = np.full(1 + k, cfg.pace_prior_games * wbar)
        lamp[0] = 1e-6
        p0[0] = yp.mean()
        bp = _solve(P, yp, w, lamp, p0)
    return {"b0": b[0], "hca": b[1], "p0": bp[0], "off": pd.Series(b[2:2 + k], index=teams),
            "def": pd.Series(b[2 + k:], index=teams), "tempo": pd.Series(bp[1:], index=teams), "games": n // 2}


def predict(r: dict, home, away, neutral) -> pd.DataFrame:
    home, away = np.asarray(home), np.asarray(away)
    v = np.where(np.asarray(neutral, dtype=bool), 0.0, 1.0)
    poss = r["p0"] + r["tempo"].reindex(home).to_numpy() + r["tempo"].reindex(away).to_numpy()
    hp = r["b0"] + r["hca"] * v + r["off"].reindex(home).to_numpy() - r["def"].reindex(away).to_numpy()
    ap = r["b0"] - r["hca"] * v + r["off"].reindex(away).to_numpy() - r["def"].reindex(home).to_numpy()
    return pd.DataFrame({"pred_margin": poss * (hp - ap) / 100, "pred_total": poss * (hp + ap) / 100,
                         "pred_pace": poss})
