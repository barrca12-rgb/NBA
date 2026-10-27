"""Phase 3 (research/LOG.md entry 9): late-season/playoff scoring, recent scoring environment, LUMA subskills.
Starts from the phase 2 spec; selection on 2024-2025 (same adoption rule); 2026 scored once by `final`.

    python -m research.p3 select
    python -m research.p3 final
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

from nba import model, players, ratings, scorecards as sc
from research import p2, s1

OUT = p2.OUT
SUB_O = ["shooting", "playmaking", "ball_security", "off_rebounding"]
SUB_D = ["def_rebounding", "defense"]
THREE = ["O_sel_thr", "O_make_thr", "D_sel_thr"]


def add_phase3(b: pd.DataFrame) -> pd.DataFrame:
    b = b.copy()
    reg = b["season_type"] == 2
    b["playoff"] = (~reg).astype(float)
    b["late"] = np.where(reg, np.clip(((b["home_gp"] + b["away_gp"]) / 2 - 60) / 22, 0, 1), 0.0)
    # league's last 150 games before the date (same season) vs the season average so far
    b = b.sort_values(["date", "game_id"]).reset_index(drop=True)
    pts = (b["home_pts"] + b["away_pts"]).to_numpy(float)
    rec = np.full(len(b), np.nan)
    for s, idx in b.groupby("season").indices.items():
        d = b["date"].to_numpy()[idx]
        p = pts[idx]
        c = np.concatenate([[0], np.cumsum(p)])
        first = np.searchsorted(d, d, side="left")          # games strictly before this date
        k = first
        lo = np.maximum(k - 150, 0)
        ok = k >= 150
        rec[idx[ok]] = (c[k[ok]] - c[lo[ok]]) / 150
    b["recent_dev"] = np.where(np.isnan(rec), 0.0, rec - b["season_avg_total"])
    for c in players.SUBSKILLS:
        for side in ("home", "away"):
            col = f"{side}_avail_{c}"
            b[col] = b[col].fillna(0.0) if col in b else 0.0
        b[f"{c}_sum"] = b[f"home_avail_{c}"] + b[f"away_avail_{c}"]
        b[f"{c}_diff"] = b[f"home_avail_{c}"] - b[f"away_avail_{c}"]
    return b


CANDIDATES = [
    ("P6 late season and playoffs", ["playoff", "late"], ["playoff", "late"]),
    ("P7 recent scoring environment", [], ["recent_dev"]),
    ("P8 subskills, totals", [], [f"{c}_sum" for c in SUB_O + SUB_D]),
    ("P9 subskills, margin", [f"{c}_diff" for c in SUB_O + SUB_D], []),
    ("P10 three-point profile, totals", [], [f"{c}_sum" for c in THREE]),
]


def run_spec(cfg, mf, tf, wf, seasons) -> pd.DataFrame:
    b = add_phase3(p2.add_schedule(p2.add_players(p2.stage1(cfg))))
    w = model.walk_forward(b, p2.FIRST_TRAIN, mf, tf, **wf)
    return s1.with_lines(w[w["season"].isin(seasons)])


def score(w, seasons):
    r = p2.score(w, seasons)
    d = w[w["season"].isin(seasons)]
    t = sc.opener_plays(d, "total", 4)
    r["over share"] = (t["side"] > 0).mean()
    r["model - opener, Mar-Jun"] = (d["final_total"] - d["open_total"])[d["date"].dt.month.between(3, 6)].mean()
    return r


def fmt(name, r, v):
    return p2.fmt(name, r, v)[:-2] + f" {r['over share']:.0%} | {r['model - opener, Mar-Jun']:+.2f} |"


HEAD = [p2.HEAD[0].replace("| adopted |", "| adopted | over share | model - opener, Mar-Jun |"),
        p2.HEAD[1] + "---:|---:|"]


def spec0():
    with open(os.path.join(OUT, "p2_spec.json")) as f:
        sp = json.load(f)
    return ratings.RatingConfig(**sp["cfg"]), sp["margin"], sp["total"], sp["walk_forward"]


def select():
    cfg, mf, tf, wf = spec0()
    cur = score(run_spec(cfg, mf, tf, wf, p2.SEL), p2.SEL)
    md = ["# Phase 3 selection (seasons 2024 and 2025 only)", ""] + HEAD + [fmt("phase 2 spec", cur, "base")]
    print(md[-1], flush=True)
    adopted = []
    for name, am, at in CANDIDATES:
        r = score(run_spec(cfg, mf + am, tf + at, wf, p2.SEL), p2.SEL)
        take_m = bool(am) and r["margin MAE"] < cur["margin MAE"]
        take_t = bool(at) and r["total MAE"] < cur["total MAE"]
        if (am and not take_m) or (at and not take_t):
            if take_m or take_t:
                r = score(run_spec(cfg, mf + (am if take_m else []), tf + (at if take_t else []), wf, p2.SEL), p2.SEL)
        if take_m:
            mf = mf + am
        if take_t:
            tf = tf + at
        v = ", ".join(x for x, ok in (("margin", take_m), ("total", take_t)) if ok) or "no"
        md.append(fmt(name, r, v))
        print(md[-1], flush=True)
        if take_m or take_t:
            cur = r
            adopted.append(name)
    spec = {"cfg": cfg.__dict__, "margin": mf, "total": tf, "walk_forward": wf, "adopted": adopted}
    with open(os.path.join(OUT, "p3_spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    md += ["", "Adopted spec:", "", "```", json.dumps(spec, indent=1), "```", ""]
    with open(os.path.join(OUT, "p3_select.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))


def final():
    with open(os.path.join(OUT, "p3_spec.json")) as f:
        sp = json.load(f)
    cfg = ratings.RatingConfig(**sp["cfg"])
    w = run_spec(cfg, sp["margin"], sp["total"], sp["walk_forward"], p2.SEL + p2.CHECK)
    if sp.get("bias_k"):
        w = bias_correct(w, sp["bias_k"])
    md, _ = s1.report_parts(w, "Phase 3 final spec", {"selection 2024-2025": p2.SEL, "check 2026": p2.CHECK,
                                                     "all three 2024-2026": p2.SEL + p2.CHECK})
    rows = [HEAD[0], HEAD[1]]
    for s in (2024, 2025, 2026):
        rows.append(fmt(str(s), score(w, [s]), ""))
    md += "\n## By season\n\n" + "\n".join(rows) + "\n"
    w.to_csv(os.path.join(OUT, "p3_games.csv"), index=False)
    with open(os.path.join(OUT, "p3_final.md"), "w") as f:
        f.write(md)
    print(md)


def bias_correct(w: pd.DataFrame, k: float) -> pd.DataFrame:
    """P11: add k x the model's mean total miss over the league's last 150 games on earlier dates (same season)."""
    w = w.sort_values(["date", "game_id"]).reset_index(drop=True).copy()
    res = (w["points"] - w["final_total"]).to_numpy(float)
    adj = np.zeros(len(w))
    for s, idx in w.groupby("season").indices.items():
        d = w["date"].to_numpy()[idx]
        c = np.concatenate([[0], np.cumsum(res[idx])])
        kk = np.searchsorted(d, d, side="left")
        ok = kk >= 150
        adj[idx[ok]] = (c[kk[ok]] - c[kk[ok] - 150]) / 150
    w["final_total"] = w["final_total"] + k * adj
    return w


def select_p11():
    with open(os.path.join(OUT, "p3_spec.json")) as f:
        sp = json.load(f)
    cfg = ratings.RatingConfig(**sp["cfg"])
    w = run_spec(cfg, sp["margin"], sp["total"], sp["walk_forward"], p2.SEL)
    cur = score(w, p2.SEL)
    rows = [fmt("phase 3 spec (P6, P7)", cur, "base")]
    best = None
    for k in (0.25, 0.5, 1.0):
        r = score(bias_correct(w, k), p2.SEL)
        rows.append(fmt(f"P11 bias correction k={k}", r, ""))
        if r["total MAE"] < cur["total MAE"] and (best is None or r["total MAE"] < best[1]):
            best = (k, r["total MAE"])
    sp["bias_k"] = best[0] if best else None
    with open(os.path.join(OUT, "p3_spec.json"), "w") as f:
        json.dump(sp, f, indent=1)
    print("\n".join(HEAD + rows) + f"\n\nadopted k: {sp['bias_k']}")


if __name__ == "__main__":
    {"select": select, "select_p11": select_p11, "final": final}[sys.argv[1]]()
