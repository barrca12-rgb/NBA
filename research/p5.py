"""Phase 5 (research/LOG.md entry 17): early-season pace/efficiency for totals, rookie LOKI, joint re-tune of the
stage-1 settings. Selection on accuracy over 2015-2025; 2026 scored once by `final`.

    python -m research.p5 select       # all candidates in the logged order -> research/out/p5_select.md, p5_spec.json
    python -m research.p5 final        # check season 2026 + betting scorecards 2024-2026 -> p5_final.md
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace

import numpy as np
import pandas as pd

from nba import model, players, ratings
from research import p2, p3, p4, s1

OUT = p2.OUT
SEL = list(range(2015, 2026))
CHECK = [2026]
BET = [2024, 2025, 2026]


def add_p5(b: pd.DataFrame) -> pd.DataFrame:
    b = b.copy()
    b["pred_eff"] = 100 * b["pred_total"] / b["pred_pace"]
    b["pred_pace_x_early"] = b["pred_pace"] * b["early"]
    b["pred_eff_x_early"] = b["pred_eff"] * b["early"]
    return b


_B = {}


def frame(cfg, loki_pre: bool) -> pd.DataFrame:
    key = (repr(cfg), loki_pre)
    if key not in _B:
        st1 = model.features(model.stage1(cfg, 2013, 2026))
        st = strength(loki_pre)
        b = p3.add_phase3(p2.add_schedule(p2.add_players(st1, st)))
        b["team_hca"] = p4.team_hca(b)
        b["form_diff"] = p4.recent_form(b)
        _B[key] = add_p5(b)
    return _B[key]


_ST = {}


def strength(loki_pre: bool) -> pd.DataFrame:
    if loki_pre not in _ST:
        if not loki_pre:
            _ST[False] = p2.player_strength(None)
        else:
            path = os.path.join(p2.data.CACHE, "strength_2014_2026_lokipre.pkl")
            if os.path.exists(path):
                _ST[True] = pd.read_pickle(path)
            else:
                players.LOKI_PRE = True
                try:
                    g = model._games(range(2014, 2027))[0]
                    st = players.strength(list(range(2014, 2027)), g)
                finally:
                    players.LOKI_PRE = False
                st.to_pickle(path)
                _ST[True] = st
    return _ST[loki_pre]


def run(spec: dict, seasons) -> pd.DataFrame:
    cfg = ratings.RatingConfig(**spec["cfg"])
    b = frame(cfg, spec.get("loki_pre", False))
    w = model.walk_forward(b, p2.FIRST_TRAIN, spec["margin"], spec["total"], **spec["walk_forward"])
    w = w[w["season"].isin(seasons)]
    if spec.get("bias_k"):
        w = p3.bias_correct(w, spec["bias_k"])
    return w


def mae(w: pd.DataFrame, seasons=None) -> dict:
    d = w if seasons is None else w[w["season"].isin(seasons)]
    d = d.dropna(subset=["margin", "final_margin"])
    return {"margin": float((d["margin"] - d["final_margin"]).abs().mean()),
            "total": float((d["points"] - d["final_total"]).abs().mean()), "games": len(d)}


def row(name, r, v, extra=""):
    return f"| {name} | {r['margin']:.4f} | {r['total']:.4f} | {r['games']:,} | {v} | {extra} |"


def select():
    with open(os.path.join(OUT, "p4_spec.json")) as f:
        spec = json.load(f)
    spec.pop("adopted_phase4", None)
    spec.pop("hook", None)
    spec.pop("hook_c", None)
    spec["loki_pre"] = False
    cur = mae(run(spec, SEL))
    md = ["# Phase 5 selection (accuracy on 2015-2025, about 12,000 games)", "",
          "| spec | margin MAE | total MAE | games | adopted | note |", "|---|---:|---:|---:|---|---|", row("phase 4 spec", cur, "base")]
    print(md[-1], flush=True)
    adopted = []

    def trial(name, sp, kind, seasons=SEL, note=""):
        nonlocal spec, cur
        base = cur if seasons is SEL else mae(run(spec, seasons))
        r = mae(run(sp, seasons))
        better = {"margin": r["margin"] < base["margin"], "total": r["total"] < base["total"],
                  "both": r["margin"] + r["total"] < base["margin"] + base["total"]}[kind]
        md.append(row(name, r, "yes" if better else "no", note + (f" (base on these seasons: {base['margin']:.4f} / {base['total']:.4f})" if seasons is not SEL else "")))
        print(md[-1], flush=True)
        if better:
            spec = sp
            cur = mae(run(spec, SEL)) if seasons is not SEL else r
            adopted.append(name)
        return better

    # 1. early-season pace and efficiency (totals)
    trial("T1 early-season level (totals)", {**spec, "total": spec["total"] + ["early"]}, "total")
    trial("T2 possessions x early, efficiency x early (totals)",
          {**spec, "total": spec["total"] + ["pred_pace_x_early", "pred_eff_x_early"]}, "total")
    # 3. stage-1 settings, one at a time, two passes
    grid = {"half_life": [20.0, 30.0, 45.0, 60.0], "prior_games": [5.0, 10.0, 15.0, 20.0],
            "carry": [0.3, 0.5, 0.7], "pace_half_life": [8.0, 15.0, 30.0]}
    for pas in (1, 2):
        changed = False
        for k, vals in grid.items():
            for v in vals:
                c = dict(spec["cfg"])
                if c.get(k) == v:
                    continue
                c[k] = v
                if k == "prior_games":
                    c["pace_prior_games"] = v
                if trial(f"S{pas} {k}={v:g}", {**spec, "cfg": c}, "both"):
                    changed = True
        if not changed:
            break
    # 2. rookie LOKI (preseason boards 2022-2027), scored on 2022-2025
    trial("R1 preseason LOKI for unrated players", {**spec, "loki_pre": True}, "both", seasons=[2022, 2023, 2024, 2025],
          note="scored on 2022-2025")
    spec["adopted_phase5"] = adopted
    with open(os.path.join(OUT, "p5_spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    md += ["", "Adopted spec:", "", "```", json.dumps(spec, indent=1), "```", ""]
    with open(os.path.join(OUT, "p5_select.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))


def final():
    with open(os.path.join(OUT, "p5_spec.json")) as f:
        spec = json.load(f)
    with open(os.path.join(OUT, "p4_spec.json")) as f:
        old = json.load(f)
    old["loki_pre"] = False
    out = ["# Phase 5 final: check season 2026 and betting scorecards 2024-2026", ""]
    ws = {}
    for name, sp in (("phase 4 spec", old), ("phase 5 spec", spec)):
        w = s1.with_lines(run(sp, sorted(set(SEL + CHECK))))
        ws[name] = w
        m_sel, m_chk = mae(w, SEL), mae(w, CHECK)
        out.append(f"- {name}: accuracy 2015-2025 margin {m_sel['margin']:.3f} / total {m_sel['total']:.3f}; "
                   f"2026 check margin {m_chk['margin']:.3f} / total {m_chk['total']:.3f}")
    out.append("")
    md, _ = s1.report_parts(ws["phase 5 spec"][ws["phase 5 spec"]["season"].isin(BET)], "Phase 5 spec at the opener",
                            {"2024-2025": [2024, 2025], "check 2026": CHECK, "all three 2024-2026": BET})
    rows = [p3.HEAD[0], p3.HEAD[1]]
    for name, w in ws.items():
        for s in BET:
            rows.append(p3.fmt(f"{name} {s}", p3.score(w, [s]), ""))
    text = "\n".join(out) + "\n" + md + "\n## Per season, phase 4 vs phase 5\n\n" + "\n".join(rows) + "\n"
    with open(os.path.join(OUT, "p5_final.md"), "w") as f:
        f.write(text)
    ws["phase 5 spec"].to_csv(os.path.join(OUT, "p5_games.csv"), index=False)
    print(text)


if __name__ == "__main__":
    {"select": select, "final": final}[sys.argv[1]]()
