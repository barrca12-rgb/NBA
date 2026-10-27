"""The pre-registered scorecards (research/LOG.md): MAE vs the close, information beyond the close, results and
CLV at the opener. Mirrors barrca12-rgb/CBB research/originator/d_common.py and cbb/evaluate.py."""
from __future__ import annotations

import numpy as np
import pandas as pd

BREAKEVEN = 110 / 210      # 52.38% at -110
SPREAD_EDGES = (2, 3, 4)
TOTAL_EDGES = (3, 4, 5)


def mae(d: pd.DataFrame) -> dict:
    s = d.dropna(subset=["home_spread"])
    t = d.dropna(subset=["total"])
    return {"games (spread)": len(s),
            "model margin MAE": (s["margin"] - s["final_margin"]).abs().mean(),
            "close margin MAE": (s["margin"] + s["home_spread"]).abs().mean(),
            "games (total)": len(t),
            "model total MAE": (t["points"] - t["final_total"]).abs().mean(),
            "close total MAE": (t["points"] - t["total"]).abs().mean()}


def _ols_cluster(x, y, groups):
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    bread = np.linalg.inv(X.T @ X)
    s = pd.DataFrame(X * e[:, None]).groupby(groups).sum().to_numpy()
    se = np.sqrt(np.diag(bread @ (s.T @ s) @ bread))
    return b[1], se[1]


def beyond_close(d: pd.DataFrame) -> dict:
    """OLS of (result - close) on (model - close), standard errors clustered by date. A slope > 0 means the model
    knows something the close does not."""
    out = {}
    s = d.dropna(subset=["home_spread"])
    line = -s["home_spread"]
    out["margin slope"], out["margin se"] = _ols_cluster((s["final_margin"] - line).to_numpy(),
                                                         (s["margin"] - line).to_numpy(), s["date"].to_numpy())
    t = d.dropna(subset=["total"])
    out["total slope"], out["total se"] = _ols_cluster((t["final_total"] - t["total"]).to_numpy(),
                                                       (t["points"] - t["total"]).to_numpy(), t["date"].to_numpy())
    return out


def opener_plays(d: pd.DataFrame, market: str, edge: float) -> pd.DataFrame:
    """One row per play at the opener: side (+1 home/over, -1 away/under), win (1/0, pushes dropped), clv."""
    if market == "spread":
        p = d.dropna(subset=["open_home_spread"]).copy()
        p["edge"] = p["final_margin"] + p["open_home_spread"]          # model margin - opener's margin
        p["res"] = p["margin"] + p["open_home_spread"]
        p["move"] = p["open_home_spread"] - p["home_spread"]           # + = close moved toward home
    else:
        p = d.dropna(subset=["open_total"]).copy()
        p["edge"] = p["final_total"] - p["open_total"]
        p["res"] = p["points"] - p["open_total"]
        p["move"] = p["total"] - p["open_total"]                        # + = close moved toward the over
    p = p[p["edge"].abs() >= edge]
    p["side"] = np.sign(p["edge"])
    p["clv"] = p["move"] * p["side"]
    r = np.sign(p["res"]) * p["side"]
    p["win"] = np.where(r > 0, 1.0, np.where(r < 0, 0.0, np.nan))
    return p


def boot_ci(p: pd.DataFrame, reps: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% interval for win % from a bootstrap that resamples game dates (plays on one date move together)."""
    q = p.dropna(subset=["win"])
    if not len(q):
        return np.nan, np.nan
    by = q.groupby("date")["win"].agg(["sum", "count"])
    w, n = by["sum"].to_numpy(), by["count"].to_numpy()
    rng = np.random.default_rng(seed)
    i = rng.integers(0, len(by), size=(reps, len(by)))
    pct = w[i].sum(1) / n[i].sum(1)
    return float(np.percentile(pct, 2.5)), float(np.percentile(pct, 97.5))


def opener_card(d: pd.DataFrame, market: str, edge: float) -> dict:
    p = opener_plays(d, market, edge)
    q = p.dropna(subset=["win"])
    n, w = len(q), q["win"].sum()
    lo, hi = boot_ci(p)
    c = p["clv"].dropna()
    return {"plays": n, "win%": w / n if n else np.nan, "ci lo": lo, "ci hi": hi,
            "roi%": 100 * (w * 100 / 110 - (n - w)) / n if n else np.nan,
            "clv": c.mean() if len(c) else np.nan, "clv plays": len(c)}
