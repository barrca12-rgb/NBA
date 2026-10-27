"""Phase 2 (research/LOG.md entry 6): candidate features scored on the selection seasons 2024-2025; the check
season 2026 is scored only for the final spec (`python -m research.p2 final`).

    python -m research.p2 select     # every candidate, cumulative, adoption by selection-season MAE
    python -m research.p2 final      # the adopted spec: selection seasons and the 2026 check, full scorecards
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace

import numpy as np
import pandas as pd

from nba import data, model, players, ratings, scorecards as sc
from research import s1

OUT = os.path.join(os.path.dirname(__file__), "out")
SEL, CHECK = [2024, 2025], [2026]
FIRST_TRAIN = 2014                  # first season with player strength (2013 is the minutes burn-in)
TZ = {**{t: 0 for t in (1, 2, 30, 5, 8, 11, 14, 18, 17, 19, 20, 28, 27)},
      **{t: -1 for t in (4, 6, 10, 29, 15, 16, 3, 25, 24)}, **{t: -2 for t in (7, 26, 21)},
      **{t: -3 for t in (9, 12, 13, 22, 23)}}
ALTITUDE = {7, 26}                  # Denver, Utah


def base_cfg() -> ratings.RatingConfig:
    with open(s1.FROZEN) as f:
        c = json.load(f)
    return ratings.RatingConfig(half_life=c["half_life"], prior_games=c["prior_games"],
                                pace_prior_games=c["prior_games"], carry=c["carry"])


_S1 = {}


def stage1(cfg) -> pd.DataFrame:
    k = repr(cfg)
    if k not in _S1:
        _S1[k] = model.features(model.stage1(cfg, 2013, 2026))
    return _S1[k]


_PS = []


def player_strength(g: pd.DataFrame) -> pd.DataFrame:
    if not _PS:
        path = os.path.join(data.CACHE, "strength_2014_2026_v3.pkl")
        if os.path.exists(path):
            _PS.append(pd.read_pickle(path))
        else:
            st = players.strength(list(range(2014, 2027)), g[g["season"] >= 2014])
            st.to_pickle(path)
            _PS.append(st)
    return _PS[0]


def add_players(b: pd.DataFrame, st: pd.DataFrame | None = None) -> pd.DataFrame:
    st = player_strength(b) if st is None else st
    for side in ("home", "away"):
        m = st.rename(columns={"team_id": f"{side}_id", **{c: f"{side}_{c}" for c in st.columns
                                                            if c not in ("game_id", "team_id")}})
        b = b.merge(m, on=["game_id", f"{side}_id"], how="left")
    for tag in ("avail", "usual", "dressed"):
        for c in ("net", "O", "D"):
            for side in ("home", "away"):
                b[f"{side}_{tag}_{c}"] = b[f"{side}_{tag}_{c}"].fillna(0.0)
        b[f"{tag}_diff"] = b[f"home_{tag}_net"] - b[f"away_{tag}_net"]
        b[f"{tag}_diff_x_early"] = b[f"{tag}_diff"] * b["early"]
        b[f"{tag}_O_sum"] = b[f"home_{tag}_O"] + b[f"away_{tag}_O"]
        b[f"{tag}_D_sum"] = b[f"home_{tag}_D"] + b[f"away_{tag}_D"]
    b["miss_diff"] = (b["home_usual_net"] - b["home_avail_net"]) - (b["away_usual_net"] - b["away_avail_net"])
    b["miss_O_sum"] = (b["home_usual_O"] - b["home_avail_O"]) + (b["away_usual_O"] - b["away_avail_O"])
    b["miss_D_sum"] = (b["home_usual_D"] - b["home_avail_D"]) + (b["away_usual_D"] - b["away_avail_D"])
    return b


def add_schedule(b: pd.DataFrame) -> pd.DataFrame:
    """3 games in 4 nights, games in the last 7 days, time zones crossed since the last game, altitude."""
    b = b.copy()
    b["venue_tz"] = b["home_id"].map(TZ)
    long = pd.concat([b[["game_id", "season", "date", "venue_tz", "home_id"]].rename(columns={"home_id": "team"}),
                      b[["game_id", "season", "date", "venue_tz", "away_id"]].rename(columns={"away_id": "team"})])
    long = long.sort_values(["team", "date"])
    grp = long.groupby(["team", "season"])
    d = long["date"]
    long["d2"] = grp["date"].shift(2)
    long["three_in_four"] = ((d - long["d2"]).dt.days <= 3).astype(float)
    long["g7"] = grp["date"].transform(lambda x: x.apply(lambda t: ((x < t) & (x >= t - pd.Timedelta(days=7))).sum()))
    long["tz_moved"] = (long["venue_tz"] - grp["venue_tz"].shift()).abs().fillna(0)
    for side in ("home", "away"):
        m = long.rename(columns={"team": f"{side}_id", "three_in_four": f"{side}_3in4", "g7": f"{side}_g7",
                                 "tz_moved": f"{side}_tz"})
        b = b.merge(m[["game_id", f"{side}_id", f"{side}_3in4", f"{side}_g7", f"{side}_tz"]],
                    on=["game_id", f"{side}_id"], how="left")
    b["fatigue_3in4_diff"] = b["home_3in4"] - b["away_3in4"]
    b["g7_diff"] = b["home_g7"] - b["away_g7"]
    b["tz_diff"] = b["home_tz"] - b["away_tz"]
    b["fatigue_3in4_sum"] = b["home_3in4"] + b["away_3in4"]
    b["g7_sum"] = b["home_g7"] + b["away_g7"]
    b["tz_sum"] = b["home_tz"] + b["away_tz"]
    b["altitude"] = (b["home_id"].isin(ALTITUDE) & ~b["neutral"]).astype(float)
    return b


# Candidates in the pre-registered order. Each: (name, margin features added, total features added, cfg changes,
# walk-forward options).
CANDIDATES = [
    ("P1 player strength", ["avail_diff", "avail_diff_x_early", "miss_diff"],
     ["avail_O_sum", "avail_D_sum", "miss_O_sum", "miss_D_sum"], {}, {}),
    ("P2 3-point luck regressed", [], [], {"ppp_col": "ppp_luck"}, {}),
    ("P3 fatigue, travel, altitude", ["fatigue_3in4_diff", "g7_diff", "tz_diff", "altitude"],
     ["fatigue_3in4_sum", "g7_sum", "tz_sum", "altitude"], {}, {}),
    ("P4 recent seasons weighted (half-life 3)", [], [], {}, {"season_half_life": 3.0}),
    ("P5 pace half-life 15 days", [], [], {"pace_half_life": 15.0}, {}),
]


def run_spec(cfg, mf, tf, wf) -> pd.DataFrame:
    b = add_schedule(add_players(stage1(cfg)))
    w = model.walk_forward(b, FIRST_TRAIN, mf, tf, **wf)
    return s1.with_lines(w[w["season"].isin(SEL + CHECK)])


def score(w: pd.DataFrame, seasons) -> dict:
    d = w[w["season"].isin(seasons)].copy()
    d.loc[s1.suspect(d), "open_home_spread"] = np.nan
    a = sc.mae(d)
    sp, to = sc.opener_card(d, "spread", 3), sc.opener_card(d, "total", 4)
    return {"margin MAE": a["model margin MAE"], "total MAE": a["model total MAE"],
            "close margin MAE": a["close margin MAE"], "close total MAE": a["close total MAE"],
            "sp3 win%": sp["win%"], "sp3 plays": sp["plays"], "sp3 clv": sp["clv"],
            "to4 win%": to["win%"], "to4 plays": to["plays"], "to4 clv": to["clv"]}


def fmt(name, r, verdict=""):
    return (f"| {name} | {r['margin MAE']:.3f} | {r['total MAE']:.3f} | {r['sp3 win%']:.1%} ({r['sp3 plays']}) | "
            f"{r['sp3 clv']:+.2f} | {r['to4 win%']:.1%} ({r['to4 plays']}) | {r['to4 clv']:+.2f} | {verdict} |")


HEAD = ["| spec | margin MAE | total MAE | spreads 3+ win % (plays) | CLV | totals 4+ win % (plays) | CLV | adopted |",
        "|---|---:|---:|---:|---:|---:|---:|---|"]


def select():
    cfg, mf, tf, wf = base_cfg(), list(model.MARGIN_FEATURES), list(model.TOTAL_FEATURES), {}
    cur = score(run_spec(cfg, mf, tf, wf), SEL)
    md = ["# Phase 2 selection (seasons 2024 and 2025 only)", "",
          f"Closing line on these games: margin MAE {cur['close margin MAE']:.3f}, total MAE {cur['close total MAE']:.3f}.",
          ""] + HEAD + [fmt("S1 base (trained from 2014)", cur, "base")]
    adopted = []
    for name, am, at, cc, ww in CANDIDATES:
        cfg2, wf2 = replace(cfg, **cc), {**wf, **ww}
        r = score(run_spec(cfg2, mf + am, tf + at, wf2), SEL)
        # margin part adopted if margin MAE drops; total part if total MAE drops; shared changes need either
        take_m = r["margin MAE"] < cur["margin MAE"]
        take_t = r["total MAE"] < cur["total MAE"]
        if am or at:
            mf2, tf2 = mf + (am if take_m else []), tf + (at if take_t else [])
            v = ", ".join(x for x, ok in (("margin", take_m and am), ("total", take_t and at)) if ok) or "no"
            keep = bool(take_m and am) or bool(take_t and at)
            if keep and not (take_m and take_t):      # re-score the partial adoption
                r = score(run_spec(cfg2, mf2, tf2, wf2), SEL)
            mf, tf = mf2, tf2
        else:
            keep = take_m and take_t or (take_m or take_t) and (r["margin MAE"] + r["total MAE"] <
                                                                  cur["margin MAE"] + cur["total MAE"])
            v = "yes" if keep else "no"
            if keep:
                cfg, wf = cfg2, wf2
        md.append(fmt(name, r, v))
        print(md[-1], flush=True)
        if keep:
            cur = r
            adopted.append(name)
    # diagnostic, not bettable at the open: dressed list instead of last game
    dm = [f.replace("avail", "dressed") for f in mf]
    dt = [f.replace("avail", "dressed") for f in tf]
    r = score(run_spec(cfg, dm, dt, wf), SEL)
    md += [fmt("diagnostic: dressed list (known near tip, not at the open)", r, "n/a"), ""]
    spec = {"cfg": cfg.__dict__, "margin": mf, "total": tf, "walk_forward": wf, "adopted": adopted}
    with open(os.path.join(OUT, "p2_spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    md += ["Adopted spec:", "", "```", json.dumps(spec, indent=1), "```", ""]
    with open(os.path.join(OUT, "p2_select.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))


def final():
    with open(os.path.join(OUT, "p2_spec.json")) as f:
        spec = json.load(f)
    cfg = ratings.RatingConfig(**spec["cfg"])
    w = run_spec(cfg, spec["margin"], spec["total"], spec["walk_forward"])
    md, res = s1.report_parts(w, "Phase 2 final spec", {"selection 2024-2025": SEL, "check 2026": CHECK,
                                                         "all three 2024-2026": SEL + CHECK})
    w.to_csv(os.path.join(OUT, "p2_games.csv"), index=False)
    with open(os.path.join(OUT, "p2_final.md"), "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    {"select": select, "final": final}[sys.argv[1]]()
