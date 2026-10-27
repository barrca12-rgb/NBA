"""Specification S1 (research/LOG.md entry 2): stage-1 grid on development results, then the frozen walk-forward
model and the pre-registered scorecards.

    python -m research.s1 grid       # 18 stage-1 configs, scored on 2014-2024 results only
    python -m research.s1 run        # frozen config -> research/out/s1.md and s1_games.csv
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

from nba import data, lines, model, ratings, scorecards as sc

OUT = os.path.join(os.path.dirname(__file__), "out")
DEV, HOLD = list(range(2014, 2025)), [2025, 2026]
FROZEN = os.path.join(OUT, "s1_config.json")


def grid():
    rows = []
    for hl, pg, carry in itertools.product((30, 60, 120), (5, 10, 20), (0.5, 0.75)):
        cfg = ratings.RatingConfig(half_life=hl, prior_games=pg, pace_prior_games=pg, carry=carry)
        b = model.stage1(cfg, 2013, 2024)
        d = b[b["season"].isin(DEV)]
        m = (d["home_pts"] - d["away_pts"] - d["pred_margin"]).abs().mean()
        t = (d["home_pts"] + d["away_pts"] - d["pred_total"]).abs().mean()
        rows.append({"half_life": hl, "prior_games": pg, "carry": carry, "margin MAE": m, "total MAE": t,
                     "sum": m + t})
        print(rows[-1], flush=True)
    g = pd.DataFrame(rows).sort_values("sum")
    os.makedirs(OUT, exist_ok=True)
    g.to_csv(os.path.join(OUT, "s1_grid.csv"), index=False)
    best = g.iloc[0]
    with open(FROZEN, "w") as f:
        json.dump({"half_life": float(best["half_life"]), "prior_games": float(best["prior_games"]),
                   "carry": float(best["carry"])}, f)
    print(g.to_string(index=False))


def with_lines(b: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for s in sorted(b["season"].unique()):
        g, _ = data.season_games(s)
        parts.append(lines.consensus(pd.read_csv(os.path.join(lines.OUT, f"espn_{s}.csv")), g))
    return b.merge(pd.concat(parts), on="game_id", how="left")


def suspect(d: pd.DataFrame) -> pd.Series:
    """Opener favors the other team from the model, and they disagree by 10+ points (CBB swapped(), model only)."""
    line = -d["open_home_spread"]
    return (np.sign(d["final_margin"]) != np.sign(line)) & ((d["final_margin"] - line).abs() >= 10) & line.notna()


def build(cfg: ratings.RatingConfig, mf=model.MARGIN_FEATURES, tf=model.TOTAL_FEATURES) -> pd.DataFrame:
    b = model.features(model.stage1(cfg, 2013, 2026))
    w = model.walk_forward(b, 2013, mf, tf)
    return with_lines(w[w["season"] >= 2014])


def report(w: pd.DataFrame, title: str) -> tuple[str, dict]:
    return report_parts(w, title, {"development 2014-2024": DEV, "holdout 2025-2026": HOLD})


def report_parts(w: pd.DataFrame, title: str, seasons: dict) -> tuple[str, dict]:
    sus = suspect(w)
    ws = w.copy()
    ws.loc[sus, ["open_home_spread"]] = np.nan
    md = [f"# {title}", "", f"Suspect spread records excluded (opener favors the other team from the model by 10+): "
          f"{int(sus.sum())} ({', '.join(f'{s}: {n}' for s, n in sus.groupby(w['season']).sum().items() if n)}).", ""]
    res = {}
    parts = {k: w["season"].isin(v) for k, v in seasons.items()}
    md += ["## 1. Accuracy vs the closing line", "", "| sample | games | model margin MAE | close margin MAE | "
           "model total MAE | close total MAE |", "|---|---:|---:|---:|---:|---:|"]
    for k, m in parts.items():
        a = sc.mae(w[m])
        md.append(f"| {k} | {a['games (spread)']:,} | {a['model margin MAE']:.2f} | {a['close margin MAE']:.2f} | "
                  f"{a['model total MAE']:.2f} | {a['close total MAE']:.2f} |")
    md += ["", "## 2. Beyond the close: OLS of (result - close) on (model - close), date-clustered SE", "",
           "| sample | margin slope (se) | total slope (se) |", "|---|---:|---:|"]
    for k, m in parts.items():
        o = sc.beyond_close(w[m])
        md.append(f"| {k} | {o['margin slope']:.3f} ({o['margin se']:.3f}) | {o['total slope']:.3f} ({o['total se']:.3f}) |")
    md += ["", "## 3-4. At the opener: win %, ROI at -110, 95% date-bootstrap interval, opener CLV", "",
           "| market | edge | sample | plays | win % | 95% interval | ROI | CLV (pts) |", "|---|---|---|---:|---:|---|---:|---:|"]
    for market, edges in (("spread", sc.SPREAD_EDGES), ("total", sc.TOTAL_EDGES)):
        for e in edges:
            for k, m in parts.items():
                c = sc.opener_card(ws[m], market, e)
                res[(market, e, k)] = c
                md.append(f"| {market} | {e}+ | {k} | {c['plays']:,} | {c['win%']:.1%} | {c['ci lo']:.1%} - "
                          f"{c['ci hi']:.1%} | {c['roi%']:+.1f}% | {c['clv']:+.2f} |")
    md += ["", "Opener scorecards use only seasons that have openers.", ""]
    return "\n".join(md), res


def verdict(res: dict) -> tuple[bool, list[str]]:
    out, ok_any = [], False
    for market, e in (("spread", 3), ("total", 4)):
        d, h = res[(market, e, "development 2014-2024")], res[(market, e, "holdout 2025-2026")]
        checks = {"dev win% > 52.4%": d["win%"] > sc.BREAKEVEN, "holdout win% > 52.4%": h["win%"] > sc.BREAKEVEN,
                  "holdout CI low > 50%": h["ci lo"] > 0.5, "dev CLV > 0": d["clv"] > 0, "holdout CLV > 0": h["clv"] > 0}
        ok = all(checks.values())
        ok_any |= ok
        out.append(f"* {market}s at {e}+: " + ", ".join(f"{k} {'yes' if v else 'NO'}" for k, v in checks.items())
                   + f" -> {'PASS' if ok else 'fail'}")
    return ok_any, out


def run():
    with open(FROZEN) as f:
        cfg = ratings.RatingConfig(**{k: v for k, v in json.load(f).items()})
    cfg.pace_prior_games = cfg.prior_games
    w = build(cfg)
    md, res = report(w, f"S1 results (stage 1: {cfg})")
    ok, lines_ = verdict(res)
    md += "\n## Pass rule\n\n" + "\n".join(lines_) + f"\n\n**Verdict: {'PASS' if ok else 'KILL'}**\n"
    w.to_csv(os.path.join(OUT, "s1_games.csv"), index=False)
    with open(os.path.join(OUT, "s1.md"), "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    {"grid": grid, "run": run}[sys.argv[1]]()
