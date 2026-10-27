"""Player strength from LUMA ARC (lumahoops.org open data, CC BY 4.0) and hoopR player box scores.

For each team-game: minutes-weighted ARC of
  * avail   players who played in the team's previous game this season (known when openers post)
  * usual   the team's rotation over its last 10 games (who normally plays)
  * dressed players dressed for this game (known only near tip: diagnostic, not bettable at the open)
A player's expected minutes = his average over his last 10 appearances (any team). His ARC for season s comes
from the season s-1 board (2-year window), so nothing from season s is used. Unrated players (rookies, deep
bench) get ROOKIE_ARC.
"""
from __future__ import annotations

import os
import re
import unicodedata
import urllib.request

import numpy as np
import pandas as pd

from . import data

ARC_URL = "https://lumahoops.org/luma/data/releases/arc/v3.1/arc_season_boards.csv"
ARC_FILE = os.path.join(data.CACHE, "arc_season_boards_v3.1.csv")
BOX_URL = data.RELEASES + "/espn_nba_player_boxscores/player_box_{season}.parquet"
ROOKIE_ARC = {"net": -2.0, "O": -1.0, "D": -1.0}
# LUMA subskills (O = shooting + playmaking + ball_security + off_rebounding + lineups_o; D = def_rebounding +
# defense + lineups_d) and the 3-point profile. Unrated players get 0.
SUBSKILLS = ["shooting", "playmaking", "ball_security", "off_rebounding", "def_rebounding", "defense",
             "O_sel_thr", "O_make_thr", "D_sel_thr"]
COLS = ["net", "O", "D"] + SUBSKILLS


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`-]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def arc() -> pd.DataFrame:
    if not os.path.exists(ARC_FILE):
        urllib.request.urlretrieve(ARC_URL, ARC_FILE)
    a = pd.read_csv(ARC_FILE)
    a = a[a["window_years"] == 2].copy()
    a["season"] = a["season"].str[:4].astype(int) + 1        # "2024-25" -> 2025
    a["key"] = a["name"].map(norm)
    # traded players can appear once per team; keep the row with most possessions
    return a.sort_values("poss").drop_duplicates(["season", "key"], keep="last")[["season", "key"] + COLS]


def box(seasons) -> pd.DataFrame:
    parts = []
    for s in seasons:
        path = os.path.join(data.CACHE, f"player_box_{s}.parquet")
        if not os.path.exists(path):
            urllib.request.urlretrieve(BOX_URL.format(season=s), path)
        b = pd.read_parquet(path, columns=["game_id", "season", "game_date", "athlete_id", "athlete_display_name",
                                           "team_id", "minutes", "did_not_play"])
        parts.append(b)
    b = pd.concat(parts, ignore_index=True)
    b = b[b["team_id"].isin(data.TEAMS)].copy()
    b["date"] = pd.to_datetime(b["game_date"])
    b["minutes"] = pd.to_numeric(b["minutes"], errors="coerce").fillna(0)
    b["key"] = b["athlete_display_name"].map(norm)
    return b.drop_duplicates(["game_id", "athlete_id"])


def strength(seasons, games: pd.DataFrame) -> pd.DataFrame:
    """One row per (game_id, team_id): avail_/usual_/dressed_ net, O, D, plus the share of players matched."""
    b = box(sorted(set(seasons) | {min(seasons) - 1}))
    b = b[b["game_id"].isin(games["game_id"]) | (b["season"] == min(seasons) - 1)]
    a = arc()
    b["arc_season"] = b["season"] - 1
    b = b.merge(a.rename(columns={"season": "arc_season"}), on=["arc_season", "key"], how="left")
    # missed last season entirely: the board from the season before
    b2 = b[["key"]].assign(arc_season=b["season"] - 2).merge(
        a.rename(columns={"season": "arc_season"}), on=["arc_season", "key"], how="left")
    for c in COLS:
        b[c] = b[c].fillna(pd.Series(b2[c].to_numpy(), index=b.index))
    b["rated"] = b["net"].notna()
    for c in COLS:
        b[c] = b[c].fillna(ROOKIE_ARC.get(c, 0.0))
    # expected minutes: average over each player's last 10 appearances before this game (any team)
    b = b.sort_values(["athlete_id", "date", "game_id"])
    played = b["minutes"].where(b["minutes"] > 0)
    b["exp_min"] = played.groupby(b["athlete_id"]).transform(
        lambda x: x.shift().rolling(10, min_periods=1).mean()).fillna(0)
    # team game sequence within season
    tg = b[["game_id", "team_id", "season", "date"]].drop_duplicates(["game_id", "team_id"]).sort_values("date")
    tg["n"] = tg.groupby(["team_id", "season"]).cumcount()
    b = b.merge(tg[["game_id", "team_id", "n"]], on=["game_id", "team_id"])

    def agg(sel: pd.DataFrame, w: pd.Series, tag: str) -> pd.DataFrame:
        w = w.clip(lower=0)
        g = sel.assign(w=w, **{f"w_{c}": w * sel[c] for c in COLS + ["rated"]})
        s = g.groupby(["game_id", "team_id"])[["w"] + [f"w_{c}" for c in COLS + ["rated"]]].sum()
        out = pd.DataFrame({f"{tag}_{c}": 5 * s[f"w_{c}"] / s["w"] for c in COLS})
        out[f"{tag}_rated"] = s["w_rated"] / s["w"]
        return out

    # dressed: everyone on this game's box, weighted by expected minutes
    dressed = agg(b, b["exp_min"], "dressed")
    # previous game's players (minutes > 0), carried to the next game of the same team-season
    prev = b[b["minutes"] > 0][["team_id", "season", "n", "athlete_id"]].assign(n=lambda x: x["n"] + 1)
    av = prev.merge(tg[["game_id", "team_id", "season", "n"]], on=["team_id", "season", "n"])
    # exp_min / ARC as of this game: his rows are known up to the previous game; exp_min at prev game + that game
    pm = b[b["minutes"] > 0][["team_id", "season", "n", "athlete_id", "minutes", "exp_min", "rated"] + COLS]
    pm = pm.assign(n=pm["n"] + 1)
    av = av.merge(pm, on=["team_id", "season", "n", "athlete_id"])
    # update the average with the previous game's minutes (approx: 0.9 old + 0.1 new)
    av["w"] = np.where(av["exp_min"] > 0, 0.9 * av["exp_min"] + 0.1 * av["minutes"], av["minutes"])
    avail = agg(av, av["w"], "avail")
    # usual rotation: players with minutes in the team's last 10 games, weighted by their average minutes there
    rows = []
    bm = b[b["minutes"] > 0][["team_id", "season", "n", "athlete_id", "minutes", "rated"] + COLS]
    for (t, s), g in bm.groupby(["team_id", "season"]):
        ns = sorted(g["n"].unique())
        for n in range(1, max(ns) + 2):
            win = g[(g["n"] >= n - 10) & (g["n"] < n)]
            if not len(win):
                continue
            m = win.groupby("athlete_id").agg(w=("minutes", "sum"), rated=("rated", "last"),
                                               **{c: (c, "last") for c in COLS})
            m = m.assign(team_id=t, season=s, n=n)
            rows.append(m.reset_index())
    us = pd.concat(rows).merge(tg[["game_id", "team_id", "season", "n"]], on=["team_id", "season", "n"])
    usual = agg(us, us["w"], "usual")
    out = dressed.join(avail, how="left").join(usual, how="left")
    # first game of a season (no previous game): the dressed list stands in
    for tag in ("avail", "usual"):
        for c in COLS + ["rated"]:
            out[f"{tag}_{c}"] = out[f"{tag}_{c}"].fillna(out[f"dressed_{c}"])
    return out.reset_index()
