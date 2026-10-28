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

import hashlib
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


ARC_SHA256 = "822e6c7d9d5fbb60c1e035ba1bbb6352295ff8db80bd08f24585ec2c79353ad6"   # LUMA MANIFEST.txt, v3.1


def arc() -> pd.DataFrame:
    if not os.path.exists(ARC_FILE):
        os.makedirs(data.CACHE, exist_ok=True)
        req = urllib.request.Request(ARC_URL, headers={"User-Agent": "Mozilla/5.0 (nba-card; LUMA open data)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
        if hashlib.sha256(body).hexdigest() != ARC_SHA256:
            raise RuntimeError("LUMA ARC file does not match the release hash")
        with open(ARC_FILE, "wb") as f:
            f.write(body)
    a = pd.read_csv(ARC_FILE)
    a = a[a["window_years"] == 2].copy()
    a["season"] = a["season"].str[:4].astype(int) + 1        # "2024-25" -> 2025
    a["key"] = a["name"].map(norm)
    # traded players can appear once per team; keep the row with most possessions
    return a.sort_values("poss").drop_duplicates(["season", "key"], keep="last")[["season", "key"] + COLS]


LOKI_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "luma")
LOKI_BOARD_URL = "https://lumahoops.org/luma/data/releases/loki/2026-27/R1/v3.3/board.csv"
LOKI_BOARD_SHA256 = "9659c162c2af225a3096aac0b8d8ce8a43e8d6d165a45a05108df9dab9058da8"   # LUMA MANIFEST.txt
LOKI_BOARD = os.path.join(data.CACHE, "loki_board_2027_v3.3.csv")


def _loki_names() -> pd.Series:
    """pid -> normalized name, from LUMA's free 2026-27 LOKI board (names are not in the API pull)."""
    if not os.path.exists(LOKI_BOARD):
        os.makedirs(data.CACHE, exist_ok=True)
        req = urllib.request.Request(LOKI_BOARD_URL, headers={"User-Agent": "Mozilla/5.0 (nba-card; LUMA open data)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
        if hashlib.sha256(body).hexdigest() != LOKI_BOARD_SHA256:
            raise RuntimeError("LUMA LOKI board does not match the release hash")
        with open(LOKI_BOARD, "wb") as f:
            f.write(body)
    bd = pd.read_csv(LOKI_BOARD).dropna(subset=["pid"])
    names = dict(zip(bd["pid"].astype(int), bd["name"].map(norm)))
    a = pd.read_csv(ARC_FILE, usecols=["pid", "name"]).drop_duplicates("pid") if os.path.exists(ARC_FILE) else None
    if a is not None:
        names = {**dict(zip(a["pid"].astype(int), a["name"].map(norm))), **names}
    return pd.Series(names)


def loki(season: int) -> pd.DataFrame | None:
    """Latest LUMA LOKI ratings for a season (data/luma/loki_<season>.csv from nba/luma.py), indexed by normalized
    name with net, O, D; None when there is no file."""
    path = os.path.join(LOKI_DIR, f"loki_{season}.csv")
    if not os.path.exists(path):
        return None
    lk = pd.read_csv(path)
    lk = lk[lk["asof"] == lk["asof"].max()]
    lk["key"] = lk["pid"].astype(int).map(_loki_names())
    lk = lk.dropna(subset=["key"]).drop_duplicates("key").set_index("key")
    lk = lk.rename(columns={"o": "O", "d": "D"})[["net", "O", "D"]]
    # this year's draft picks have no pid on LUMA's board: their board rating by name, split evenly O/D
    bd = pd.read_csv(LOKI_BOARD)
    bd = bd[bd["pid"].isna()].assign(key=lambda d: d["name"].map(norm)).drop_duplicates("key").set_index("key")
    rk = pd.DataFrame({"net": bd["loki"], "O": bd["loki"] / 2, "D": bd["loki"] / 2})
    return pd.concat([lk, rk[~rk.index.isin(lk.index)]])


def box(seasons, refresh=()) -> pd.DataFrame:
    parts = []
    for s in seasons:
        path = os.path.join(data.CACHE, f"player_box_{s}.parquet")
        if not os.path.exists(path) or s in refresh:
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


def strength(seasons, games: pd.DataFrame, slate: pd.DataFrame | None = None, refresh=()) -> pd.DataFrame:
    """One row per (game_id, team_id): avail_/usual_/dressed_ net, O, D, plus the share of players matched.
    slate: unplayed games (game_id, season, date, home_id, away_id) to get avail_/usual_ for (live card)."""
    b = box(sorted(set(seasons) | {min(seasons) - 1}), refresh)
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
    # Live seasons only (from Oct 28, 2026): players with no ARC rating (rookies, returners) take LUMA's LOKI
    # rating instead of the flat ROOKIE_ARC. Seasons without a LOKI file (every backtest season) are unchanged.
    for s, lk in ((s, loki(s)) for s in sorted(b["season"].unique())):
        if lk is None:
            continue
        m = (b["season"] == s) & b["net"].isna()
        for c in ("net", "O", "D"):
            b.loc[m, c] = b.loc[m, "key"].map(lk[c])
        b.loc[m & b["net"].notna(), "rated"] = True
    for c in COLS:
        b[c] = b[c].fillna(ROOKIE_ARC.get(c, 0.0))
    # expected minutes: average over each player's last 10 appearances before this game (any team)
    b = b.sort_values(["athlete_id", "date", "game_id"])
    played = b["minutes"].where(b["minutes"] > 0)
    b["exp_min"] = played.groupby(b["athlete_id"]).transform(
        lambda x: x.shift().rolling(10, min_periods=1).mean()).fillna(0)
    # team game sequence within season
    tg = b[["game_id", "team_id", "season", "date"]].drop_duplicates(["game_id", "team_id"])
    if slate is not None and len(slate):
        sl = pd.concat([slate[["game_id", "season", "date", "home_id"]].rename(columns={"home_id": "team_id"}),
                        slate[["game_id", "season", "date", "away_id"]].rename(columns={"away_id": "team_id"})])
        sl["date"] = pd.to_datetime(sl["date"])
        tg = pd.concat([tg, sl[~sl["game_id"].isin(tg["game_id"])]], ignore_index=True)
    tg = tg.sort_values(["date", "game_id"])
    tg["n"] = tg.groupby(["team_id", "season"]).cumcount()
    # n_av: the slot whose "previous game" is the team's last completed one. Equal to n for played games; for
    # unplayed ones (days ahead on the live card) every game after the last completed one maps to it.
    done = tg["game_id"].isin(b["game_id"]).astype(int)
    tg["n_av"] = done.groupby([tg["team_id"], tg["season"]]).cumsum() - done
    tg["n_av"] = np.where(done == 1, tg["n"], tg["n_av"])
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
    slot = tg[["game_id", "team_id", "season", "n_av"]].rename(columns={"n_av": "n"})
    av = prev.merge(slot, on=["team_id", "season", "n"])
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
    us = pd.concat(rows).merge(slot, on=["team_id", "season", "n"])
    usual = agg(us, us["w"], "usual")
    # played: who actually played, by actual minutes (known only after the game; used to fit past games only)
    played = agg(b[b["minutes"] > 0], b.loc[b["minutes"] > 0, "minutes"], "played")
    out = (tg.set_index(["game_id", "team_id"])[[]].join(dressed, how="left").join(avail, how="left")
           .join(usual, how="left").join(played, how="left"))
    # first game of a season (no previous game): the dressed list stands in
    for tag in ("avail", "usual"):
        for c in COLS + ["rated"]:
            out[f"{tag}_{c}"] = out[f"{tag}_{c}"].fillna(out[f"dressed_{c}"])
    return out.reset_index()
