"""Phase 4 (research/LOG.md entry 12): spreads. Starts from the phase 3 spec; candidates kept only if they lower
the 2024-2025 margin MAE; 2026 scored once by `final`.

    python -m research.p4 select
    python -m research.p4 final
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

from nba import model, ratings
from research import p2, p3, s1

OUT = p2.OUT


def roster_hook(c: float, base_games: pd.DataFrame):
    """M1: adjust each past team-game's points per 100 for who played vs the team's season-to-date typical."""
    def hook(g, t):
        st = p2.player_strength(base_games)[["game_id", "team_id", "played_O", "played_D"]]
        x = t.merge(st, on=["game_id", "team_id"], how="left").sort_values(["team_id", "date", "game_id"])
        grp = x.groupby(["team_id", "season"])
        for col in ("played_O", "played_D"):
            typ = grp[col].transform(lambda v: v.expanding().mean().shift())
            x[col + "_dev"] = (x[col] - typ).fillna(0.0)
        o = x[["game_id", "team_id", "played_D_dev"]].rename(columns={"team_id": "opp_id", "played_D_dev": "opp_D_dev"})
        x = x.merge(o, on=["game_id", "opp_id"], how="left")
        x["ppp_roster"] = x["ppp_luck"] - c * x["played_O_dev"] + c * x["opp_D_dev"].fillna(0.0)
        return x.drop(columns=["played_O", "played_D"])
    return hook


def blowout_hook(prev=None):
    """M3: games decided by 20+ points count half in stage 1."""
    def hook(g, t):
        t = prev(g, t) if prev else t
        m = g.set_index("game_id")
        margin = (m["home_pts"] - m["away_pts"]).abs()
        t = t.copy()
        t["wt_mult"] = np.where(t["game_id"].map(margin) >= 20, 0.5, 1.0)
        return t
    return hook


def team_hca(b: pd.DataFrame) -> pd.Series:
    """M2 (CBB team_hca_table): per (season, home team), shrunk home-minus-road residual vs the ratings over the
    three previous seasons; times venue."""
    out = []
    for s in sorted(b["season"].unique()):
        d = b[(b["season"] < s) & (b["season"] >= s - 3) & ~b["neutral"]]
        r = d["margin"] - d["pred_margin"]
        long = pd.concat([pd.DataFrame({"team": d["home_id"], "r": r}), pd.DataFrame({"team": d["away_id"], "r": -r})])
        gsum = long.groupby("team")["r"].agg(["sum", "count"])
        out.append((gsum["sum"] / (gsum["count"] + 60)).rename("team_hca").rename_axis("home_id").reset_index().assign(season=s))
    h = pd.concat(out)
    v = b[["season", "home_id"]].merge(h, on=["season", "home_id"], how="left")["team_hca"].fillna(0).to_numpy()
    return pd.Series(v * b["venue"].to_numpy(), index=b.index)


def recent_form(b: pd.DataFrame) -> pd.Series:
    """M5: each team's (result - ratings margin) over its last 10 games this season, shrunk by 10; home - away."""
    r = b["margin"] - b["pred_margin"]
    long = pd.concat([pd.DataFrame({"game_id": b["game_id"], "season": b["season"], "date": b["date"],
                                    "team": b["home_id"], "r": r}),
                      pd.DataFrame({"game_id": b["game_id"], "season": b["season"], "date": b["date"],
                                    "team": b["away_id"], "r": -r})]).sort_values(["team", "date", "game_id"])
    grp = long.groupby(["team", "season"])["r"]
    long["form"] = grp.transform(lambda v: v.shift().rolling(10, min_periods=1).sum() / (v.shift().rolling(10, min_periods=1).count() + 10)).fillna(0)
    f = long.set_index(["game_id", "team"])["form"]
    h = f.reindex(pd.MultiIndex.from_arrays([b["game_id"], b["home_id"]])).to_numpy()
    a = f.reindex(pd.MultiIndex.from_arrays([b["game_id"], b["away_id"]])).to_numpy()
    return pd.Series(np.nan_to_num(h) - np.nan_to_num(a), index=b.index)


_ST1 = {}


def build(cfg, hook_key, hook, spec) -> pd.DataFrame:
    if hook_key not in _ST1:
        _ST1[hook_key] = model.features(model.stage1(cfg, 2013, 2026, hook))
    b = p3.add_phase3(p2.add_schedule(p2.add_players(_ST1[hook_key])))
    b["team_hca"] = team_hca(b)
    b["form_diff"] = recent_form(b)
    return b


def run(cfg, hook_key, hook, spec, seasons):
    b = build(cfg, hook_key, hook, spec)
    w = model.walk_forward(b, p2.FIRST_TRAIN, spec["margin"], spec["total"], **spec["walk_forward"])
    w = s1.with_lines(w[w["season"].isin(seasons)])
    if spec.get("bias_k"):
        w = p3.bias_correct(w, spec["bias_k"])
    return w


def select():
    with open(os.path.join(OUT, "p3_spec.json")) as f:
        spec = json.load(f)
    spec.setdefault("hook", None)
    cfg = ratings.RatingConfig(**spec["cfg"])
    base_games = p2.stage1(cfg)
    hooks = {None: None}

    def score(sp, cfg_):
        hk = sp["hook"]
        if hk not in hooks:
            c = sp["hook_c"]
            h = roster_hook(c, base_games) if hk.startswith("roster") else None
            if "blowout" in hk:
                h = blowout_hook(h)
            hooks[hk] = h
        cf = cfg_
        if hk and hk.startswith("roster"):
            from dataclasses import replace
            cf = replace(cfg_, ppp_col="ppp_roster")
        return p3.score(run(cf, (hk, repr(cf)), hooks[hk], sp, p2.SEL), p2.SEL)

    cur = score(spec, cfg)
    md = ["# Phase 4 selection (seasons 2024 and 2025 only; adoption by margin MAE)", ""] + p3.HEAD + \
         [p3.fmt("phase 3 spec", cur, "base")]
    print(md[-1], flush=True)
    adopted = []

    def trial(name, sp):
        nonlocal spec, cur
        r = score(sp, cfg)
        ok = r["margin MAE"] < cur["margin MAE"]
        md.append(p3.fmt(name, r, "yes" if ok else "no"))
        print(md[-1], flush=True)
        if ok:
            spec, cur = sp, r
            adopted.append(name)
        return ok

    # M1 roster-adjusted ratings, c in {0.5, 1.0}: the better of the two is the candidate
    best = None
    for c in (0.5, 1.0):
        sp = {**spec, "hook": f"roster{c}", "hook_c": c}
        r = score(sp, cfg)
        md.append(p3.fmt(f"M1 roster-adjusted ratings c={c}", r, ""))
        print(md[-1], flush=True)
        if best is None or r["margin MAE"] < best[1]["margin MAE"]:
            best = (sp, r)
    if best[1]["margin MAE"] < cur["margin MAE"]:
        spec, cur = best
        adopted.append(f"M1 c={spec['hook_c']}")
        md[-1 if spec['hook_c'] == 1.0 else -2] += " adopted"
    trial("M2 team-specific home court", {**spec, "margin": spec["margin"] + ["team_hca"]})
    hk = (spec["hook"] or "") + "+blowout"
    trial("M3 blowouts count half in stage 1", {**spec, "hook": hk, "hook_c": spec.get("hook_c", 0)})
    trial("M4 margin model weights recent seasons (half-life 3)",
          {**spec, "walk_forward": {**spec["walk_forward"], "margin_half_life": 3.0}})
    trial("M5 recent form", {**spec, "margin": spec["margin"] + ["form_diff"]})
    spec["adopted_phase4"] = adopted
    with open(os.path.join(OUT, "p4_spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    md += ["", "Adopted spec:", "", "```", json.dumps(spec, indent=1), "```", ""]
    with open(os.path.join(OUT, "p4_select.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))


def final():
    with open(os.path.join(OUT, "p4_spec.json")) as f:
        spec = json.load(f)
    assert not spec.get("hook"), "final() supports the adopted spec (no stage-1 hook)"
    cfg = ratings.RatingConfig(**spec["cfg"])
    w = run(cfg, (None, repr(cfg)), None, spec, p2.SEL + p2.CHECK)
    md, _ = s1.report_parts(w, "Phase 4 final spec", {"selection 2024-2025": p2.SEL, "check 2026": p2.CHECK,
                                                     "all three 2024-2026": p2.SEL + p2.CHECK})
    rows = [p3.HEAD[0], p3.HEAD[1]] + [p3.fmt(str(s), p3.score(w, [s]), "") for s in (2024, 2025, 2026)]
    md += "\n## By season\n\n" + "\n".join(rows) + "\n"
    w.to_csv(os.path.join(OUT, "p4_games.csv"), index=False)
    with open(os.path.join(OUT, "p4_final.md"), "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    {"select": select, "final": final}[sys.argv[1]]()
