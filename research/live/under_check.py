"""Under-bias check on the 2026-27 season so far (Oct 28 card review). The live model's total for every completed
2026-27 game (as of that morning) vs the result and ESPN's stored closing total (free feed), plus the inputs behind
tomorrow's plays.

    python -m research.live.under_check 2026-10-28
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from nba import data, lines, live, model, players, ratings
from research import p2, p3


def season_frame(day, season=2027):
    day = pd.Timestamp(day)
    m = live.load_model()
    spec = m["spec"]
    cfg = ratings.RatingConfig(**spec["cfg"])
    sl = live.slate(day, season)
    b = model.features(model.stage1(cfg, season - 2, season, extra=sl.drop(columns=["home_name", "away_name"])))
    st = players.strength([season - 1, season], b[b["season"] >= season - 1], slate=sl)
    b = p3.add_phase3(p2.add_schedule(p2.add_players(b, st)))
    hca = {int(k): v for k, v in m["team_hca"].items()}
    b["team_hca"] = b["home_id"].map(hca).fillna(0) * b["venue"]
    parts = {}
    for mk, col in (("margin", "final_margin"), ("total", "final_total")):
        c = m[mk]
        b[col] = c["intercept"] + sum(b[k].astype(float) * v for k, v in c.items() if k != "intercept")
        if mk == "total":
            for k, v in c.items():
                parts[k] = (b[k].astype(float) * v) if k != "intercept" else v
    cur = b[b["season"] == season].copy()
    return cur, m, parts


def main(day):
    cur, m, parts = season_frame(day)
    done = cur.dropna(subset=["home_pts"]).copy()
    # ESPN's stored closing totals for the completed games (free; no SGO, no Odds API)
    rows = [r for gid in done["game_id"] for r in lines.game_lines(int(gid))]
    l = pd.DataFrame(rows)
    l = l[~l["book"].fillna("").isin(lines.NOT_BOOKS | {"", "fetch failed"})]
    close = l.groupby("game_id")[["total", "open_total"]].median()
    done = done.join(close, on="game_id")
    d = done.dropna(subset=["total"])
    print(f"2026-27 completed games: {len(done)} ({len(d)} with an ESPN close)")
    print(f"  mean result total            {d['points'].mean():.1f}")
    print(f"  mean model total             {d['final_total'].mean():.1f}")
    print(f"  mean closing total           {d['total'].mean():.1f}")
    print(f"  result - model               {(d['points'] - d['final_total']).mean():+.2f}  (se {(d['points'] - d['final_total']).std() / np.sqrt(len(d)):.2f})")
    print(f"  close - model                {(d['total'] - d['final_total']).mean():+.2f}")
    print(f"  result - close               {(d['points'] - d['total']).mean():+.2f}")
    print(f"  model MAE / close MAE        {(d['points'] - d['final_total']).abs().mean():.2f} / {(d['points'] - d['total']).abs().mean():.2f}")
    e = d["final_total"] - d["total"]
    print(f"  model under the close by 4+  {(e <= -4).sum()} games, over by 4+ {(e >= 4).sum()}")
    q = d[e.abs() >= 4]
    if len(q):
        win = np.sign(q["points"] - q["total"]) == np.sign(q["final_total"] - q["total"])
        print(f"  those plays vs the close: {win.sum()}-{(~win).sum()}")
    # scoring environment inputs
    prev = data.season_games(2026)[0]
    print(f"\n2025-26 average total {(prev['home_pts'] + prev['away_pts']).mean():.1f}; 2026-27 so far {done['points'].mean():.1f}")
    print(f"stage-1 total (ratings only) on completed games: {d['pred_total'].mean():.1f}; season_avg_total input {d['season_avg_total'].mean():.1f}")
    # tomorrow's slate
    sl = cur[cur["home_pts"].isna() & (cur["date"] == pd.Timestamp(day))]
    cols = ["away", "home", "final_total", "pred_total", "season_avg_total", "avail_O_sum", "avail_D_sum", "miss_O_sum",
            "miss_D_sum", "b2b_sum", "rest_sum", "home_rest", "away_rest", "home_gp", "away_gp"]
    print("\nTomorrow's slate, model inputs:")
    print(sl[cols].round(1).to_string(index=False))
    print("\nTotal = sum of these pieces (points), tomorrow's games:")
    pc = pd.DataFrame({k: (v.loc[sl.index] if hasattr(v, "loc") else v) for k, v in parts.items()})
    pc.insert(0, "game", sl["away"] + "@" + sl["home"])
    print(pc.round(1).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
