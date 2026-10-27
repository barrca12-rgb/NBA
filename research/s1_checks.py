"""Exploratory checks on the S1 totals result (logged in research/LOG.md entry 4; cannot change the verdict).

    python -m research.s1_checks      # needs research/out/s1_games.csv from `python -m research.s1 run`
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from nba import scorecards as sc

OUT = os.path.join(os.path.dirname(__file__), "out")


def line(name, p):
    q = p.dropna(subset=["win"])
    n, w = len(q), q["win"].sum()
    lo, hi = sc.boot_ci(p)
    return (f"| {name} | {n:,} | {w / n:.1%} | {lo:.1%} - {hi:.1%} | {100 * (w * 100 / 110 - (n - w)) / n:+.1f}% | "
            f"{p['clv'].mean():+.2f} |") if n else f"| {name} | 0 | | | | |"


def main():
    w = pd.read_csv(os.path.join(OUT, "s1_games.csv"), parse_dates=["date"])
    w["month"] = w["date"].dt.month
    p = sc.opener_plays(w, "total", 4)
    head = ["| slice | plays | win % | 95% interval | ROI | CLV |", "|---|---:|---:|---|---:|---:|"]
    md = ["# S1 totals at 4+: exploratory checks", "", "## By season and direction", ""] + head
    for s, d in p.groupby("season"):
        md.append(line(f"{s}", d))
    for side, d in p.groupby("side"):
        md.append(line("overs" if side > 0 else "unders", d))
    for (s, side), d in p.groupby(["season", "side"]):
        md.append(line(f"{s} {'overs' if side > 0 else 'unders'}", d))
    md.append(line("regular season", p[p["season_type"] == 2]))
    md.append(line("playoffs/play-in", p[p["season_type"] != 2]))
    for m, d in p.groupby("month"):
        md.append(line(f"month {m}", d))
    # Naive baselines: is the edge the model's, or a season-wide bias in openers?
    md += ["", "## Baselines at the opener (same seasons, every game with an opener)", ""] + head
    o = w.dropna(subset=["open_total"]).copy()
    for name, pred in [("always under", o["open_total"] - 10), ("always over", o["open_total"] + 10),
                       ("season scoring average so far", o["season_avg_total"]),
                       ("ratings-only total (stage 1)", o["pred_total"])]:
        b = sc.opener_plays(o.assign(final_total=pred), "total", 4)
        for part, m in (("dev", b["season"] < 2025), ("holdout", b["season"] >= 2025)):
            md.append(line(f"{name}, {part}", b[m]))
    # Opener vs close bias: mean (result - opener) and (result - close) by season
    md += ["", "## Opener and close bias by season (points: result minus line)", "",
           "| season | games | result - opener | result - close | model - opener | opener MAE | close MAE | model MAE |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s, d in o.dropna(subset=["total"]).groupby("season"):
        md.append(f"| {s} | {len(d):,} | {(d['points'] - d['open_total']).mean():+.2f} | {(d['points'] - d['total']).mean():+.2f} | "
                  f"{(d['final_total'] - d['open_total']).mean():+.2f} | {(d['points'] - d['open_total']).abs().mean():.2f} | "
                  f"{(d['points'] - d['total']).abs().mean():.2f} | {(d['points'] - d['final_total']).abs().mean():.2f} |")
    with open(os.path.join(OUT, "s1_checks.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
