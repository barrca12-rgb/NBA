"""Freeze the live model: the phase 4 spec (research/out/p4_spec.json) with stage 2 fit on every season
2014-2026, plus each team's home-court edge for the next season. Writes data/model.json for nba/live.py.

    python -m nba.fit 2027      # re-run after each season with the new season number
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

from . import model, ratings

ROOT = os.path.join(os.path.dirname(__file__), "..")
SAVED = os.path.join(ROOT, "data", "model.json")
SPEC = os.path.join(ROOT, "research", "out", "p4_spec.json")


def main(next_season: int):
    from research import p4
    with open(SPEC) as f:
        spec = json.load(f)
    cfg = ratings.RatingConfig(**spec["cfg"])
    b = p4.build(cfg, (None, repr(cfg)), None, spec)
    b = b[(b["season"] >= 2014) & (b["season"] < next_season)].dropna(subset=["margin"])
    mf, tf, wf = spec["margin"], spec["total"], spec["walk_forward"]
    yrs = (next_season - 1 - b["season"].to_numpy(float))
    wt = np.ones(len(b)) if wf.get("season_half_life") is None else 0.5 ** (yrs / wf["season_half_life"])
    wm = wt if wf.get("margin_half_life") is None else 0.5 ** (yrs / wf["margin_half_life"])
    cm = model.ridge_w(b[mf].to_numpy(float), b["margin"].to_numpy(float), wm)
    ct = model.ridge_w(b[tf].to_numpy(float), b["points"].to_numpy(float), wt)
    # each team's home edge for next season (p4.team_hca for a season after the data)
    nxt = b.tail(30).copy()
    nxt["season"], nxt["home_id"], nxt["venue"] = next_season, list(range(1, 31)), 1.0
    both = pd.concat([b.assign(neutral=b["neutral"].astype(bool)), nxt.assign(neutral=False)], ignore_index=True)
    hca = p4.team_hca(both).to_numpy()[-30:]
    out = {"next_season": next_season, "fitted_on": [2014, next_season - 1], "spec": spec,
           "margin": dict(zip(["intercept"] + mf, map(float, cm))),
           "total": dict(zip(["intercept"] + tf, map(float, ct))),
           "team_hca": {str(t): round(float(v), 3) for t, v in zip(range(1, 31), hca)}}
    with open(SAVED, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ("margin", "total", "team_hca")}, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]))
